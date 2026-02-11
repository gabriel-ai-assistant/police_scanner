#!/usr/bin/env python3
"""
Monitor data integrity in bcfy_calls_raw.

This script provides ongoing monitoring and diagnostics for the ingestion pipeline.

Checks:
- Calls stuck in processed=FALSE for >1 hour (potential failures)
- Calls with NULL s3_key_v2 but processed=TRUE (inconsistent state)
- Calls with error messages (review for patterns)
- Recent INSERT/UPDATE activity
- Pipeline throughput metrics

Usage:
    python monitor_data_integrity.py              # Run all checks
    python monitor_data_integrity.py --watch      # Continuous monitoring (every 60s)
    python monitor_data_integrity.py --json       # Output as JSON
"""

import asyncio
import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

# Add shared modules to path
sys.path.insert(0, '/app/shared_bcfy')

from db_pool import get_connection, release_connection


async def check_stuck_calls(conn, hours=1):
    """Find calls that haven't been processed in >N hours."""
    result = await conn.fetch("""
        SELECT call_uid, fetched_at, url, playlist_uuid
        FROM bcfy_calls_raw
        WHERE processed = FALSE
          AND error IS NULL
          AND fetched_at < NOW() - INTERVAL '%s hours'
        ORDER BY fetched_at ASC
        LIMIT 20
    """ % hours)

    return {
        'check': 'stuck_calls',
        'threshold_hours': hours,
        'count': len(result),
        'severity': 'critical' if len(result) > 10 else 'warning' if len(result) > 0 else 'ok',
        'samples': [
            {
                'call_uid': r['call_uid'],
                'fetched_at': r['fetched_at'].isoformat() if r['fetched_at'] else None,
                'hours_stuck': round((datetime.now(timezone.utc) - r['fetched_at'].replace(tzinfo=timezone.utc)).total_seconds() / 3600, 1) if r['fetched_at'] else None
            }
            for r in result[:5]
        ]
    }


async def check_inconsistent_state(conn):
    """Find calls where processed=TRUE but s3_key_v2 is NULL."""
    result = await conn.fetch("""
        SELECT call_uid, fetched_at, url, last_attempt
        FROM bcfy_calls_raw
        WHERE processed = TRUE AND s3_key_v2 IS NULL
        ORDER BY fetched_at DESC
        LIMIT 20
    """)

    return {
        'check': 'inconsistent_state',
        'description': 'processed=TRUE but s3_key_v2 is NULL',
        'count': len(result),
        'severity': 'critical' if len(result) > 0 else 'ok',
        'samples': [
            {
                'call_uid': r['call_uid'],
                'fetched_at': r['fetched_at'].isoformat() if r['fetched_at'] else None,
                'last_attempt': r['last_attempt'].isoformat() if r['last_attempt'] else None
            }
            for r in result[:5]
        ]
    }


async def check_error_patterns(conn, hours=24):
    """Aggregate error messages to identify patterns."""
    result = await conn.fetch("""
        SELECT
            SUBSTRING(error FROM 1 FOR 100) as error_prefix,
            COUNT(*) as count,
            MAX(last_attempt) as latest
        FROM bcfy_calls_raw
        WHERE error IS NOT NULL
          AND last_attempt > NOW() - INTERVAL '%s hours'
        GROUP BY SUBSTRING(error FROM 1 FOR 100)
        ORDER BY count DESC
        LIMIT 10
    """ % hours)

    total_errors = sum(r['count'] for r in result)

    return {
        'check': 'error_patterns',
        'time_window_hours': hours,
        'total_errors': total_errors,
        'severity': 'critical' if total_errors > 100 else 'warning' if total_errors > 10 else 'ok',
        'patterns': [
            {
                'error': r['error_prefix'],
                'count': r['count'],
                'latest': r['latest'].isoformat() if r['latest'] else None
            }
            for r in result
        ]
    }


async def check_null_playlist_uuid(conn, hours=24):
    """Find calls with NULL playlist_uuid (should be populated)."""
    count = await conn.fetchval("""
        SELECT COUNT(*) FROM bcfy_calls_raw
        WHERE playlist_uuid IS NULL
          AND fetched_at > NOW() - INTERVAL '%s hours'
    """ % hours)

    return {
        'check': 'null_playlist_uuid',
        'time_window_hours': hours,
        'count': count,
        'severity': 'warning' if count > 0 else 'ok'
    }


async def get_pipeline_throughput(conn):
    """Get pipeline throughput metrics."""
    # Calls per hour for last 24 hours
    hourly = await conn.fetch("""
        SELECT
            DATE_TRUNC('hour', fetched_at) as hour,
            COUNT(*) as total,
            SUM(CASE WHEN processed = TRUE THEN 1 ELSE 0 END) as processed,
            SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as errors
        FROM bcfy_calls_raw
        WHERE fetched_at > NOW() - INTERVAL '24 hours'
        GROUP BY DATE_TRUNC('hour', fetched_at)
        ORDER BY hour DESC
        LIMIT 24
    """)

    # Current queue depth
    queue_depth = await conn.fetchval("""
        SELECT COUNT(*) FROM bcfy_calls_raw
        WHERE processed = FALSE AND error IS NULL
    """)

    # Processing rate (last hour)
    processed_last_hour = await conn.fetchval("""
        SELECT COUNT(*) FROM bcfy_calls_raw
        WHERE processed = TRUE
          AND last_attempt > NOW() - INTERVAL '1 hour'
    """)

    return {
        'check': 'pipeline_throughput',
        'queue_depth': queue_depth,
        'processed_last_hour': processed_last_hour,
        'severity': 'warning' if queue_depth > 100 else 'ok',
        'hourly_stats': [
            {
                'hour': r['hour'].isoformat() if r['hour'] else None,
                'total': r['total'],
                'processed': r['processed'],
                'errors': r['errors']
            }
            for r in hourly[:6]  # Last 6 hours
        ]
    }


async def get_recent_system_logs(conn, minutes=30):
    """Get recent ingestion-related system logs."""
    logs = await conn.fetch("""
        SELECT event_type, message, metadata, created_at
        FROM system_logs
        WHERE component = 'ingestion'
          AND created_at > NOW() - INTERVAL '%s minutes'
        ORDER BY created_at DESC
        LIMIT 20
    """ % minutes)

    return {
        'check': 'recent_logs',
        'time_window_minutes': minutes,
        'count': len(logs),
        'logs': [
            {
                'event_type': r['event_type'],
                'message': r['message'],
                'created_at': r['created_at'].isoformat() if r['created_at'] else None
            }
            for r in logs[:10]
        ]
    }


async def run_all_checks(output_json=False):
    """Run all data integrity checks."""
    conn = await get_connection()
    try:
        results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'checks': []
        }

        # Run all checks
        checks = [
            ('Stuck Calls', check_stuck_calls(conn)),
            ('Inconsistent State', check_inconsistent_state(conn)),
            ('Error Patterns', check_error_patterns(conn)),
            ('NULL playlist_uuid', check_null_playlist_uuid(conn)),
            ('Pipeline Throughput', get_pipeline_throughput(conn)),
            ('Recent Logs', get_recent_system_logs(conn)),
        ]

        for name, coro in checks:
            result = await coro
            results['checks'].append(result)

        # Calculate overall severity
        severities = [c.get('severity', 'ok') for c in results['checks']]
        if 'critical' in severities:
            results['overall_severity'] = 'critical'
        elif 'warning' in severities:
            results['overall_severity'] = 'warning'
        else:
            results['overall_severity'] = 'ok'

        if output_json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print_results(results)

        return results

    finally:
        await release_connection(conn)


def print_results(results):
    """Print results in human-readable format."""
    print("=" * 70)
    print(f"Data Integrity Monitor - {results['timestamp']}")
    print(f"Overall Status: {results['overall_severity'].upper()}")
    print("=" * 70)

    for check in results['checks']:
        severity = check.get('severity', 'ok')
        icon = '✓' if severity == 'ok' else '⚠' if severity == 'warning' else '✗'

        print(f"\n{icon} {check['check'].upper()}")

        if check['check'] == 'stuck_calls':
            print(f"  Calls stuck >1hr: {check['count']}")
            if check['samples']:
                for s in check['samples']:
                    print(f"    - {s['call_uid']} ({s['hours_stuck']}h stuck)")

        elif check['check'] == 'inconsistent_state':
            print(f"  Inconsistent records: {check['count']}")
            if check['samples']:
                for s in check['samples']:
                    print(f"    - {s['call_uid']}")

        elif check['check'] == 'error_patterns':
            print(f"  Total errors (24h): {check['total_errors']}")
            if check['patterns']:
                for p in check['patterns'][:3]:
                    print(f"    - {p['count']}x: {p['error'][:60]}...")

        elif check['check'] == 'null_playlist_uuid':
            print(f"  Missing playlist_uuid: {check['count']}")

        elif check['check'] == 'pipeline_throughput':
            print(f"  Queue depth: {check['queue_depth']}")
            print(f"  Processed (1h): {check['processed_last_hour']}")

        elif check['check'] == 'recent_logs':
            print(f"  Recent logs (30min): {check['count']}")
            if check.get('logs'):
                for log in check['logs'][:3]:
                    print(f"    - [{log['event_type']}] {log['message'][:50]}")


async def watch_mode(interval_sec=60, output_json=False):
    """Continuous monitoring mode."""
    print(f"Starting watch mode (interval: {interval_sec}s)")
    print("Press Ctrl+C to stop\n")

    while True:
        try:
            await run_all_checks(output_json=output_json)
            print(f"\n--- Next check in {interval_sec}s ---\n")
            await asyncio.sleep(interval_sec)
        except KeyboardInterrupt:
            print("\nStopping watch mode")
            break


def main():
    parser = argparse.ArgumentParser(description='Monitor data integrity in bcfy_calls_raw')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--interval', type=int, default=60, help='Watch interval in seconds')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    if args.watch:
        asyncio.run(watch_mode(interval_sec=args.interval, output_json=args.json))
    else:
        asyncio.run(run_all_checks(output_json=args.json))


if __name__ == "__main__":
    main()
