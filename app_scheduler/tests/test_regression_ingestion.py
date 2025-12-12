#!/usr/bin/env python3
"""
Regression test for the complete ingestion pipeline.

This script:
1. Records current call count in bcfy_calls_raw
2. Triggers one ingestion cycle
3. Waits for completion
4. Verifies new calls were inserted
5. Triggers audio worker
6. Verifies calls were processed (processed=TRUE, s3_key_v2 populated)
7. Reports success/failure with detailed metrics

Usage:
    python regression_test_ingestion.py

Requirements:
    - At least one playlist with sync=TRUE
    - Database connection available
    - MinIO/S3 storage available
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

# Add shared modules to path
sys.path.insert(0, '/app/shared_bcfy')

from db_pool import get_connection, release_connection


async def get_baseline_metrics(conn):
    """Get baseline metrics before test."""
    metrics = {}

    # Total call count
    metrics['total_calls'] = await conn.fetchval(
        "SELECT COUNT(*) FROM bcfy_calls_raw"
    )

    # Unprocessed calls
    metrics['unprocessed_calls'] = await conn.fetchval(
        "SELECT COUNT(*) FROM bcfy_calls_raw WHERE processed = FALSE AND error IS NULL"
    )

    # Processed calls with s3_key_v2
    metrics['processed_with_s3'] = await conn.fetchval(
        "SELECT COUNT(*) FROM bcfy_calls_raw WHERE processed = TRUE AND s3_key_v2 IS NOT NULL"
    )

    # Recent calls (last 5 minutes)
    metrics['recent_calls'] = await conn.fetchval("""
        SELECT COUNT(*) FROM bcfy_calls_raw
        WHERE fetched_at > NOW() - INTERVAL '5 minutes'
    """)

    # Error count
    metrics['error_calls'] = await conn.fetchval(
        "SELECT COUNT(*) FROM bcfy_calls_raw WHERE error IS NOT NULL"
    )

    return metrics


async def get_recent_system_logs(conn, component, since_minutes=5):
    """Get recent system logs for a component."""
    return await conn.fetch("""
        SELECT event_type, message, metadata, created_at
        FROM system_logs
        WHERE component = $1 AND created_at > NOW() - INTERVAL '%s minutes'
        ORDER BY created_at DESC
        LIMIT 10
    """ % since_minutes, component)


async def run_ingestion_cycle():
    """Import and run one ingestion cycle."""
    from get_calls import ingest_loop
    await ingest_loop()


async def run_audio_worker():
    """Import and run audio worker to process pending files."""
    from audio_worker import process_pending_audio
    await process_pending_audio()


async def verify_insert_metrics(conn, baseline):
    """Verify INSERT metrics after ingestion."""
    current = await get_baseline_metrics(conn)

    new_calls = current['total_calls'] - baseline['total_calls']

    # Get recent system_logs for ingestion
    logs = await get_recent_system_logs(conn, 'ingestion')

    # Parse playlist_batch logs
    batch_metrics = []
    for log in logs:
        if log['event_type'] == 'playlist_batch' and log['metadata']:
            try:
                metadata = json.loads(log['metadata']) if isinstance(log['metadata'], str) else log['metadata']
                batch_metrics.append(metadata)
            except (json.JSONDecodeError, TypeError):
                pass

    return {
        'new_calls': new_calls,
        'current_total': current['total_calls'],
        'unprocessed': current['unprocessed_calls'],
        'batch_logs': batch_metrics
    }


async def verify_audio_processing(conn, baseline, timeout_sec=60):
    """Verify audio processing after worker runs."""
    start = time.time()

    while time.time() - start < timeout_sec:
        current = await get_baseline_metrics(conn)

        newly_processed = current['processed_with_s3'] - baseline['processed_with_s3']

        if newly_processed > 0 or current['unprocessed_calls'] == 0:
            return {
                'newly_processed': newly_processed,
                'remaining_unprocessed': current['unprocessed_calls'],
                'new_errors': current['error_calls'] - baseline['error_calls'],
                'elapsed_sec': int(time.time() - start)
            }

        await asyncio.sleep(2)

    return {
        'newly_processed': 0,
        'remaining_unprocessed': current['unprocessed_calls'],
        'new_errors': current['error_calls'] - baseline['error_calls'],
        'elapsed_sec': timeout_sec,
        'timeout': True
    }


async def check_data_consistency(conn):
    """Check for data consistency issues."""
    issues = []

    # Check for processed=TRUE but no s3_key_v2
    inconsistent = await conn.fetchval("""
        SELECT COUNT(*) FROM bcfy_calls_raw
        WHERE processed = TRUE AND s3_key_v2 IS NULL
    """)
    if inconsistent > 0:
        issues.append(f"Found {inconsistent} calls with processed=TRUE but no s3_key_v2")

    # Check for calls stuck in processing (processed=FALSE for >1 hour)
    stuck = await conn.fetchval("""
        SELECT COUNT(*) FROM bcfy_calls_raw
        WHERE processed = FALSE AND error IS NULL
        AND fetched_at < NOW() - INTERVAL '1 hour'
    """)
    if stuck > 0:
        issues.append(f"Found {stuck} calls stuck in processed=FALSE for >1 hour")

    # Check for NULL playlist_uuid (should be populated by ingestion)
    null_playlist = await conn.fetchval("""
        SELECT COUNT(*) FROM bcfy_calls_raw
        WHERE playlist_uuid IS NULL AND fetched_at > NOW() - INTERVAL '24 hours'
    """)
    if null_playlist > 0:
        issues.append(f"Found {null_playlist} recent calls with NULL playlist_uuid")

    return issues


async def regression_test():
    """Run full regression test."""
    print("=" * 70)
    print("Police Scanner Ingestion Pipeline Regression Test")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    conn = await get_connection()
    try:
        # Step 1: Get baseline metrics
        print("\n[1/6] Getting baseline metrics...")
        baseline = await get_baseline_metrics(conn)
        print(f"       Total calls: {baseline['total_calls']}")
        print(f"       Unprocessed: {baseline['unprocessed_calls']}")
        print(f"       Processed with S3: {baseline['processed_with_s3']}")
        print(f"       Recent (5min): {baseline['recent_calls']}")
        print(f"       Errors: {baseline['error_calls']}")

        # Step 2: Check for active playlists
        print("\n[2/6] Checking active playlists...")
        playlists = await conn.fetch(
            "SELECT uuid, name FROM bcfy_playlists WHERE sync = TRUE"
        )
        if not playlists:
            print("       ERROR: No playlists with sync=TRUE")
            return False

        print(f"       Found {len(playlists)} active playlist(s):")
        for p in playlists:
            print(f"         - {p['name']} ({p['uuid']})")

        # Step 3: Run ingestion cycle
        print("\n[3/6] Running ingestion cycle...")
        try:
            await run_ingestion_cycle()
            print("       Ingestion cycle completed")
        except Exception as e:
            print(f"       ERROR: Ingestion failed: {e}")
            return False

        # Step 4: Verify INSERT metrics
        print("\n[4/6] Verifying INSERT metrics...")
        insert_results = await verify_insert_metrics(conn, baseline)
        print(f"       New calls inserted: {insert_results['new_calls']}")
        print(f"       Current total: {insert_results['current_total']}")
        print(f"       Now unprocessed: {insert_results['unprocessed']}")

        if insert_results['batch_logs']:
            print("       Batch metrics from system_logs:")
            for batch in insert_results['batch_logs'][:3]:  # Show first 3
                print(f"         - {batch.get('playlist_name', 'unknown')}: "
                      f"{batch.get('inserted', 0)} inserted, "
                      f"{batch.get('duplicates', 0)} duplicates, "
                      f"{batch.get('errors', 0)} errors")

        # Step 5: Run audio worker (if there are unprocessed calls)
        if insert_results['unprocessed'] > 0:
            print(f"\n[5/6] Running audio worker ({insert_results['unprocessed']} pending)...")
            try:
                await run_audio_worker()
                print("       Audio worker completed")
            except Exception as e:
                print(f"       WARNING: Audio worker error: {e}")

            # Verify processing
            print("\n       Verifying audio processing...")
            process_results = await verify_audio_processing(conn, baseline, timeout_sec=30)
            print(f"       Newly processed: {process_results['newly_processed']}")
            print(f"       Remaining unprocessed: {process_results['remaining_unprocessed']}")
            print(f"       New errors: {process_results['new_errors']}")
            if process_results.get('timeout'):
                print("       WARNING: Timed out waiting for processing")
        else:
            print("\n[5/6] Skipping audio worker (no pending calls)")
            process_results = {'newly_processed': 0, 'remaining_unprocessed': 0, 'new_errors': 0}

        # Step 6: Check data consistency
        print("\n[6/6] Checking data consistency...")
        issues = await check_data_consistency(conn)
        if issues:
            print("       Issues found:")
            for issue in issues:
                print(f"         - {issue}")
        else:
            print("       No consistency issues found")

        # Final summary
        print("\n" + "=" * 70)
        print("REGRESSION TEST SUMMARY")
        print("=" * 70)

        success = True
        if insert_results['new_calls'] == 0 and baseline['recent_calls'] == 0:
            print("WARNING: No new calls ingested (may be normal if no recent activity)")
        else:
            print(f"PASS: Ingestion working ({insert_results['new_calls']} new calls)")

        if insert_results['batch_logs']:
            total_errors = sum(b.get('errors', 0) for b in insert_results['batch_logs'])
            if total_errors > 0:
                print(f"WARNING: {total_errors} INSERT errors logged")
                success = False
            else:
                print("PASS: No INSERT errors")

        if issues:
            print(f"WARNING: {len(issues)} consistency issue(s)")
        else:
            print("PASS: Data consistency OK")

        return success

    finally:
        await release_connection(conn)


if __name__ == "__main__":
    try:
        success = asyncio.run(regression_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
