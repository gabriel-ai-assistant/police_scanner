-- ============================================================
-- Police Scanner - Monitoring & Observability Queries
-- ============================================================
-- Use these queries to monitor system health, performance,
-- and identify optimization opportunities.
-- ============================================================

-- ===== API CALL MONITORING =====

-- API call rate by hour (should be <10/hour after optimization)
-- Use this to verify that optimizations are working
SELECT
    date_trunc('hour', timestamp) AS hour,
    COUNT(*) as call_count,
    AVG(duration_ms) as avg_duration_ms,
    MAX(duration_ms) as max_duration_ms,
    COUNT(CASE WHEN error IS NOT NULL THEN 1 END) as error_count,
    ROUND(AVG(response_size) / 1024.0, 2) as avg_kb
FROM api_call_metrics
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;

-- API calls by endpoint pattern (identify which endpoints are called most)
-- Helps find remaining optimization opportunities
SELECT
    regexp_replace(endpoint, '/[0-9a-f-]+', '/{id}', 'g') as endpoint_pattern,
    regexp_replace(
        regexp_replace(endpoint, '/[0-9a-f-]+', '/{id}', 'g'),
        '/[0-9]+', '/{num}', 'g'
    ) as normalized_endpoint,
    COUNT(*) as call_count,
    AVG(duration_ms) as avg_ms,
    MAX(duration_ms) as max_ms,
    MIN(duration_ms) as min_ms,
    COUNT(CASE WHEN error IS NOT NULL THEN 1 END) as errors
FROM api_call_metrics
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY endpoint_pattern, normalized_endpoint
ORDER BY call_count DESC;

-- Recent API errors (troubleshooting failed calls)
SELECT
    timestamp,
    endpoint,
    status_code,
    duration_ms,
    error
FROM api_call_metrics
WHERE error IS NOT NULL
  AND timestamp > NOW() - INTERVAL '6 hours'
ORDER BY timestamp DESC
LIMIT 50;

-- Slow API calls (identify performance bottlenecks)
SELECT
    timestamp,
    regexp_replace(endpoint, '/[0-9a-f-]+', '/{id}', 'g') as endpoint_pattern,
    duration_ms,
    response_size,
    status_code
FROM api_call_metrics
WHERE duration_ms > 5000  -- Slower than 5 seconds
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY duration_ms DESC
LIMIT 20;

-- ===== DUPLICATE DETECTION =====

-- Find duplicate calls (should be 0 after optimization)
-- If this returns rows, last_seen logic may not be working
SELECT
    call_uid,
    COUNT(*) as fetch_count,
    array_agg(fetched_at ORDER BY fetched_at) as fetch_times,
    NOW() - MIN(fetched_at) as first_fetch_age
FROM bcfy_calls_raw
WHERE fetched_at > NOW() - INTERVAL '2 hours'
GROUP BY call_uid
HAVING COUNT(*) > 1
ORDER BY fetch_count DESC
LIMIT 20;

-- Duplicate rate summary
SELECT
    COUNT(DISTINCT call_uid) as unique_calls,
    COUNT(*) as total_fetches,
    COUNT(*) - COUNT(DISTINCT call_uid) as duplicate_fetches,
    ROUND(100.0 * (COUNT(*) - COUNT(DISTINCT call_uid)) / COUNT(*), 2) as duplicate_pct
FROM bcfy_calls_raw
WHERE fetched_at > NOW() - INTERVAL '24 hours';

-- ===== AUDIO PROCESSING BACKLOG =====

-- Processing status overview (monitor backlog size)
SELECT
    processed,
    error IS NOT NULL as has_error,
    COUNT(*) as count,
    MIN(fetched_at) as oldest_fetch,
    MAX(fetched_at) as newest_fetch,
    NOW() - MIN(fetched_at) as max_backlog_age
FROM bcfy_calls_raw
GROUP BY processed, (error IS NOT NULL)
ORDER BY processed, has_error;

-- Unprocessed calls by age (should stay near real-time)
SELECT
    CASE
        WHEN NOW() - fetched_at < INTERVAL '1 minute' THEN '< 1 min'
        WHEN NOW() - fetched_at < INTERVAL '5 minutes' THEN '1-5 min'
        WHEN NOW() - fetched_at < INTERVAL '15 minutes' THEN '5-15 min'
        WHEN NOW() - fetched_at < INTERVAL '1 hour' THEN '15-60 min'
        ELSE '> 1 hour'
    END as age_bucket,
    COUNT(*) as count
FROM bcfy_calls_raw
WHERE processed = FALSE AND error IS NULL
GROUP BY age_bucket
ORDER BY age_bucket;

-- Failed audio processing (identify problematic calls)
SELECT
    call_uid,
    error,
    last_attempt,
    NOW() - last_attempt as time_since_failure,
    fetched_at
FROM bcfy_calls_raw
WHERE error IS NOT NULL
ORDER BY last_attempt DESC
LIMIT 50;

-- Audio processing throughput (calls/hour)
SELECT
    date_trunc('hour', last_attempt) AS hour,
    COUNT(*) as processed_count,
    COUNT(CASE WHEN error IS NOT NULL THEN 1 END) as failed_count,
    ROUND(100.0 * COUNT(CASE WHEN error IS NOT NULL THEN 1 END) / COUNT(*), 2) as failure_pct
FROM bcfy_calls_raw
WHERE last_attempt IS NOT NULL
  AND last_attempt > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;

-- ===== INGESTION PERFORMANCE =====

-- Recent cycle times (should be <5 seconds after optimization)
SELECT
    timestamp,
    duration_ms,
    (metadata->>'calls_processed')::int as calls_processed,
    (metadata->>'playlists_count')::int as playlists_count,
    CASE
        WHEN duration_ms < 1000 THEN '✓ Fast'
        WHEN duration_ms < 5000 THEN '⚠ OK'
        ELSE '✗ Slow'
    END as performance
FROM system_logs
WHERE component = 'ingestion'
  AND event_type = 'cycle_complete'
  AND timestamp > NOW() - INTERVAL '2 hours'
ORDER BY timestamp DESC
LIMIT 50;

-- Cycle performance summary
SELECT
    date_trunc('hour', timestamp) AS hour,
    COUNT(*) as cycle_count,
    AVG(duration_ms) as avg_cycle_ms,
    MIN(duration_ms) as min_cycle_ms,
    MAX(duration_ms) as max_cycle_ms,
    SUM((metadata->>'calls_processed')::int) as total_calls_ingested
FROM system_logs
WHERE component = 'ingestion'
  AND event_type = 'cycle_complete'
  AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;

-- Calls ingested per hour (identify peak/quiet periods)
SELECT
    date_trunc('hour', fetched_at) AS hour,
    COUNT(*) as calls_fetched,
    COUNT(DISTINCT group_id) as unique_groups,
    COUNT(DISTINCT feed_id) as unique_feeds,
    ROUND(AVG(duration_ms) / 1000.0, 1) as avg_duration_sec
FROM bcfy_calls_raw
WHERE fetched_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;

-- ===== LAST_SEEN STALENESS MONITORING =====

-- Check if last_seen is being updated properly
-- Staleness should be < 15 minutes for active playlists
SELECT
    uuid,
    name,
    sync,
    TO_TIMESTAMP(last_seen) as last_seen_time,
    NOW() - TO_TIMESTAMP(last_seen) as staleness,
    CASE
        WHEN last_seen = 0 THEN '✗ Never updated'
        WHEN NOW() - TO_TIMESTAMP(last_seen) < INTERVAL '15 minutes' THEN '✓ Fresh'
        WHEN NOW() - TO_TIMESTAMP(last_seen) < INTERVAL '1 hour' THEN '⚠ Stale'
        ELSE '✗ Very stale'
    END as status
FROM bcfy_playlists
WHERE sync = TRUE
ORDER BY last_seen DESC;

-- Playlist poll log (verify successful polling)
SELECT
    pl.name,
    ppl.poll_started_at,
    ppl.poll_ended_at,
    EXTRACT(EPOCH FROM (ppl.poll_ended_at - ppl.poll_started_at)) as duration_sec,
    ppl.success,
    ppl.notes
FROM bcfy_playlist_poll_log ppl
JOIN bcfy_playlists pl ON pl.uuid = ppl.uuid
WHERE ppl.poll_started_at > NOW() - INTERVAL '6 hours'
ORDER BY ppl.poll_started_at DESC
LIMIT 50;

-- Failed playlist polls (identify problematic playlists)
SELECT
    pl.name,
    pl.uuid,
    ppl.poll_started_at,
    ppl.notes as error_message,
    COUNT(*) OVER (PARTITION BY pl.uuid) as failure_count
FROM bcfy_playlist_poll_log ppl
JOIN bcfy_playlists pl ON pl.uuid = ppl.uuid
WHERE ppl.success = FALSE
  AND ppl.poll_started_at > NOW() - INTERVAL '24 hours'
ORDER BY ppl.poll_started_at DESC;

-- ===== SYSTEM HEALTH OVERVIEW =====

-- System event summary (last 24 hours)
SELECT
    component,
    event_type,
    severity,
    COUNT(*) as event_count,
    AVG(duration_ms) as avg_duration_ms,
    MAX(duration_ms) as max_duration_ms
FROM system_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY component, event_type, severity
ORDER BY component, event_type;

-- Recent errors across all components
SELECT
    timestamp,
    component,
    event_type,
    message,
    metadata
FROM system_logs
WHERE severity IN ('ERROR', 'CRITICAL')
  AND timestamp > NOW() - INTERVAL '6 hours'
ORDER BY timestamp DESC
LIMIT 30;

-- ===== DATA QUALITY CHECKS =====

-- Calls with missing critical fields
SELECT
    'Missing URL' as issue,
    COUNT(*) as count
FROM bcfy_calls_raw
WHERE url IS NULL OR url = ''
UNION ALL
SELECT
    'Missing group_id',
    COUNT(*)
FROM bcfy_calls_raw
WHERE group_id IS NULL
UNION ALL
SELECT
    'Missing duration',
    COUNT(*)
FROM bcfy_calls_raw
WHERE duration_ms IS NULL OR duration_ms = 0
UNION ALL
SELECT
    'Missing timestamps',
    COUNT(*)
FROM bcfy_calls_raw
WHERE started_at IS NULL OR ended_at IS NULL;

-- Calls with unusual durations (potential data issues)
SELECT
    call_uid,
    duration_ms,
    ROUND(duration_ms / 1000.0, 1) as duration_sec,
    started_at,
    ended_at,
    CASE
        WHEN duration_ms < 1000 THEN '⚠ Too short'
        WHEN duration_ms > 600000 THEN '⚠ Too long (>10 min)'
        ELSE '✓ Normal'
    END as status
FROM bcfy_calls_raw
WHERE duration_ms < 1000 OR duration_ms > 600000
ORDER BY duration_ms DESC
LIMIT 50;

-- ===== OPTIMIZATION VALIDATION =====

-- Validate that JWT caching is working (should see few token generations)
-- Check api_call_metrics for JWT-related endpoints
SELECT
    COUNT(*) as total_api_calls,
    COUNT(DISTINCT date_trunc('hour', timestamp)) as hours_active,
    ROUND(COUNT(*)::numeric / COUNT(DISTINCT date_trunc('hour', timestamp)), 2) as calls_per_hour
FROM api_call_metrics
WHERE timestamp > NOW() - INTERVAL '24 hours';

-- Database connection efficiency (check for connection churn)
-- This query checks if connection pooling is working
SELECT
    timestamp,
    event_type,
    message,
    duration_ms
FROM system_logs
WHERE component = 'ingestion'
  AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- ===== USEFUL AGGREGATES FOR DASHBOARDS =====

-- Current system status (single-row summary)
SELECT
    (SELECT COUNT(*) FROM bcfy_calls_raw) as total_calls,
    (SELECT COUNT(*) FROM bcfy_calls_raw WHERE processed = FALSE AND error IS NULL) as pending_audio,
    (SELECT COUNT(*) FROM bcfy_calls_raw WHERE error IS NOT NULL) as failed_audio,
    (SELECT COUNT(*) FROM bcfy_playlists WHERE sync = TRUE) as active_playlists,
    (SELECT COUNT(*) FROM api_call_metrics WHERE timestamp > NOW() - INTERVAL '1 hour') as api_calls_last_hour,
    (SELECT AVG(duration_ms) FROM system_logs WHERE component = 'ingestion' AND event_type = 'cycle_complete' AND timestamp > NOW() - INTERVAL '1 hour') as avg_cycle_ms_last_hour;

-- Today's ingestion summary
SELECT
    DATE(fetched_at) as date,
    COUNT(*) as total_calls,
    COUNT(DISTINCT group_id) as unique_groups,
    COUNT(DISTINCT feed_id) as unique_feeds,
    MIN(fetched_at) as first_call,
    MAX(fetched_at) as last_call,
    ROUND(AVG(duration_ms) / 1000.0, 1) as avg_duration_sec
FROM bcfy_calls_raw
WHERE fetched_at >= CURRENT_DATE
GROUP BY DATE(fetched_at);

-- ============================================================
-- ALERTS / THRESHOLDS
-- ============================================================
-- Use these queries to set up automated alerts

-- ALERT: High API call rate (>20/hour suggests optimization failure)
SELECT
    'High API call rate' as alert,
    COUNT(*) as calls_last_hour,
    'Expected <10, investigate if >20' as threshold
FROM api_call_metrics
WHERE timestamp > NOW() - INTERVAL '1 hour'
HAVING COUNT(*) > 20;

-- ALERT: Audio backlog growing (>1000 unprocessed calls)
SELECT
    'Large audio backlog' as alert,
    COUNT(*) as unprocessed_count,
    'Expected <100, investigate if >1000' as threshold
FROM bcfy_calls_raw
WHERE processed = FALSE AND error IS NULL
HAVING COUNT(*) > 1000;

-- ALERT: Slow ingestion cycles (avg >5 seconds)
SELECT
    'Slow ingestion cycles' as alert,
    ROUND(AVG(duration_ms)) as avg_cycle_ms,
    'Expected <5000ms, investigate if >5000' as threshold
FROM system_logs
WHERE component = 'ingestion'
  AND event_type = 'cycle_complete'
  AND timestamp > NOW() - INTERVAL '1 hour'
HAVING AVG(duration_ms) > 5000;

-- ALERT: Playlist last_seen not updating
SELECT
    'Stale playlist last_seen' as alert,
    name,
    TO_TIMESTAMP(last_seen) as last_seen_time,
    NOW() - TO_TIMESTAMP(last_seen) as staleness
FROM bcfy_playlists
WHERE sync = TRUE
  AND last_seen > 0
  AND NOW() - TO_TIMESTAMP(last_seen) > INTERVAL '1 hour';

-- ============================================================
-- END
-- ============================================================
