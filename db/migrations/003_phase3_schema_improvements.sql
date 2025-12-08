-- ============================================================
-- Phase 3: Schema Improvements & Optimization
-- Expert DBA Analysis - Schema Enhancements
-- ============================================================
-- This migration enhances schemas to track additional metadata
-- and improve query efficiency
--
-- Estimated execution time: 2-5 minutes
-- Downtime: None (additive changes)
--
-- To apply: psql "connection_string" -f 003_phase3_schema_improvements.sql
-- ============================================================

BEGIN;

-- ============================================================
-- PART 1: ENHANCE bcfy_playlists SCHEMA
-- ============================================================
RAISE NOTICE '';
RAISE NOTICE '============================================================';
RAISE NOTICE 'PHASE 3: Schema Improvements';
RAISE NOTICE '============================================================';
RAISE NOTICE '';

RAISE NOTICE 'Step 1: Enhancing bcfy_playlists table...';

-- Add metadata columns if they don't exist
ALTER TABLE bcfy_playlists
    ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE bcfy_playlists
    ADD COLUMN IF NOT EXISTS sync_error_count INTEGER DEFAULT 0;

ALTER TABLE bcfy_playlists
    ADD COLUMN IF NOT EXISTS last_error_message TEXT;

-- Ensure last_pos is properly configured
UPDATE bcfy_playlists SET last_pos = 0 WHERE last_pos IS NULL;
ALTER TABLE bcfy_playlists
    ALTER COLUMN last_pos SET NOT NULL,
    ALTER COLUMN last_pos SET DEFAULT 0;

-- Add constraint to ensure last_pos >= 0
ALTER TABLE bcfy_playlists
    ADD CONSTRAINT IF NOT EXISTS bcfy_playlists_last_pos_check
    CHECK (last_pos >= 0);

-- Add sync_error_count constraint
ALTER TABLE bcfy_playlists
    ADD CONSTRAINT IF NOT EXISTS bcfy_playlists_error_count_check
    CHECK (sync_error_count >= 0);

RAISE NOTICE '✓ bcfy_playlists schema enhanced';

-- ============================================================
-- PART 2: ENHANCE bcfy_calls_raw SCHEMA
-- ============================================================
RAISE NOTICE 'Step 2: Enhancing bcfy_calls_raw table...';

-- Add processing_stage column for better state tracking
ALTER TABLE bcfy_calls_raw
    ADD COLUMN IF NOT EXISTS processing_stage TEXT DEFAULT 'pending'
    CHECK (processing_stage IN ('pending', 'downloading', 'downloaded', 'converting', 'completed', 'failed'));

-- Add retry tracking
ALTER TABLE bcfy_calls_raw
    ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;

-- Ensure retry_count >= 0
ALTER TABLE bcfy_calls_raw
    ADD CONSTRAINT IF NOT EXISTS bcfy_calls_raw_retry_count_check
    CHECK (retry_count >= 0);

-- Update indices to include processing_stage
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_processing_stage_idx
    ON bcfy_calls_raw(processing_stage)
    WHERE processing_stage IN ('pending', 'downloading');

RAISE NOTICE '✓ bcfy_calls_raw schema enhanced';

-- ============================================================
-- PART 3: ENHANCE processing_state SCHEMA
-- ============================================================
RAISE NOTICE 'Step 3: Enhancing processing_state table...';

-- Add tracking columns
ALTER TABLE processing_state
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

ALTER TABLE processing_state
    ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;

ALTER TABLE processing_state
    ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 3;

-- Add constraints
ALTER TABLE processing_state
    ADD CONSTRAINT IF NOT EXISTS processing_state_retry_limit
    CHECK (retry_count <= max_retries);

ALTER TABLE processing_state
    ADD CONSTRAINT IF NOT EXISTS processing_state_max_retries_check
    CHECK (max_retries > 0);

-- Index for retry logic
CREATE INDEX IF NOT EXISTS processing_state_retry_idx
    ON processing_state(status, retry_count)
    WHERE status IN ('error') AND retry_count < max_retries;

RAISE NOTICE '✓ processing_state schema enhanced';

-- ============================================================
-- PART 4: ADD HELPER FUNCTIONS FOR STATE MANAGEMENT
-- ============================================================
RAISE NOTICE 'Step 4: Creating state management helper functions...';

-- Function to safely advance processing state
CREATE OR REPLACE FUNCTION advance_processing_state(
    p_call_uid TEXT,
    p_new_status TEXT,
    p_error_msg TEXT DEFAULT NULL
) RETURNS TABLE(call_uid TEXT, old_status TEXT, new_status TEXT) AS $$
DECLARE
    v_old_status TEXT;
    v_valid_transitions TEXT[] := ARRAY[
        'queued->downloaded',
        'downloaded->transcribed',
        'transcribed->indexed',
        'queued->error',
        'downloaded->error',
        'transcribed->error',
        'indexed->error',
        'error->queued'  -- Allow retry
    ];
    v_current_transition TEXT;
BEGIN
    -- Get current status
    SELECT status INTO v_old_status
    FROM processing_state
    WHERE call_uid = p_call_uid;

    IF v_old_status IS NULL THEN
        RAISE EXCEPTION 'No processing record found for call_uid: %', p_call_uid;
    END IF;

    -- Validate transition
    v_current_transition := v_old_status || '->' || p_new_status;

    IF NOT v_current_transition = ANY(v_valid_transitions) THEN
        RAISE EXCEPTION 'Invalid state transition: % to %', v_old_status, p_new_status;
    END IF;

    -- Update status
    UPDATE processing_state
    SET
        status = p_new_status,
        last_error = p_error_msg,
        updated_at = NOW(),
        retry_count = CASE
            WHEN p_new_status = 'error' THEN retry_count + 1
            WHEN p_new_status = 'queued' THEN retry_count  -- Keep count on retry
            ELSE 0
        END
    WHERE call_uid = p_call_uid;

    call_uid := p_call_uid;
    old_status := v_old_status;
    new_status := p_new_status;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Function to get stuck processing items
CREATE OR REPLACE FUNCTION get_stuck_processing_items(p_max_age_hours INTEGER DEFAULT 24)
RETURNS TABLE(call_uid TEXT, status TEXT, updated_at TIMESTAMPTZ, retry_count INTEGER, age_hours INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ps.call_uid,
        ps.status,
        ps.updated_at,
        ps.retry_count,
        EXTRACT(EPOCH FROM (NOW() - ps.updated_at))::INTEGER / 3600 AS age_hours
    FROM processing_state ps
    WHERE (ps.status IN ('queued', 'downloading', 'transcribed')
        AND NOW() - ps.updated_at > (p_max_age_hours || ' hours')::INTERVAL)
        OR (ps.status = 'error' AND ps.retry_count >= ps.max_retries)
    ORDER BY ps.updated_at ASC;
END;
$$ LANGUAGE plpgsql;

RAISE NOTICE '✓ State management functions created';

-- ============================================================
-- PART 5: CREATE STATISTICS AND HEALTH FUNCTION
-- ============================================================
RAISE NOTICE 'Step 5: Creating statistics and health check function...';

CREATE OR REPLACE FUNCTION get_pipeline_stats()
RETURNS TABLE(
    metric TEXT,
    value TEXT,
    status TEXT
) AS $$
BEGIN
    -- Total calls
    RETURN QUERY
    SELECT 'Total Calls'::TEXT, COUNT(*)::TEXT,
        CASE WHEN COUNT(*) > 1000000 THEN 'LARGE'
             WHEN COUNT(*) > 100000 THEN 'MEDIUM'
             ELSE 'SMALL' END
    FROM bcfy_calls_raw;

    -- Processed vs Pending
    RETURN QUERY
    SELECT 'Processed Calls'::TEXT, COUNT(*)::TEXT,
        CASE WHEN COUNT(*) > 900000 THEN '✓ GOOD'
             WHEN COUNT(*) > 500000 THEN '⚠ OK'
             ELSE '✗ LOW' END
    FROM bcfy_calls_raw
    WHERE processed = TRUE;

    RETURN QUERY
    SELECT 'Pending Calls'::TEXT, COUNT(*)::TEXT,
        CASE WHEN COUNT(*) < 1000 THEN '✓ LOW'
             WHEN COUNT(*) < 10000 THEN '⚠ MEDIUM'
             ELSE '✗ HIGH' END
    FROM bcfy_calls_raw
    WHERE processed = FALSE AND error IS NULL;

    -- Failed calls
    RETURN QUERY
    SELECT 'Failed Calls'::TEXT, COUNT(*)::TEXT,
        CASE WHEN COUNT(*) = 0 THEN '✓ NONE'
             WHEN COUNT(*) < 100 THEN '⚠ FEW'
             ELSE '✗ MANY' END
    FROM bcfy_calls_raw
    WHERE error IS NOT NULL;

    -- Transcripts
    RETURN QUERY
    SELECT 'Total Transcripts'::TEXT, COUNT(*)::TEXT,
        CASE WHEN COUNT(*) > 500000 THEN 'LARGE'
             WHEN COUNT(*) > 50000 THEN 'MEDIUM'
             ELSE 'SMALL' END
    FROM transcripts;

    -- Processing queue
    RETURN QUERY
    SELECT 'Queued Items'::TEXT, COUNT(*)::TEXT,
        CASE WHEN COUNT(*) = 0 THEN '✓ HEALTHY'
             WHEN COUNT(*) < 100 THEN '⚠ SMALL'
             WHEN COUNT(*) < 1000 THEN '⚠ MEDIUM'
             ELSE '✗ LARGE' END
    FROM processing_state
    WHERE status = 'queued';

    -- Error items needing retry
    RETURN QUERY
    SELECT 'Retryable Errors'::TEXT, COUNT(*)::TEXT,
        CASE WHEN COUNT(*) = 0 THEN '✓ NONE'
             WHEN COUNT(*) < 100 THEN '⚠ FEW'
             ELSE '✗ MANY' END
    FROM processing_state
    WHERE status = 'error' AND retry_count < max_retries;

    -- Active playlists
    RETURN QUERY
    SELECT 'Active Playlists'::TEXT, COUNT(*)::TEXT,
        CASE WHEN COUNT(*) > 0 THEN '✓ ACTIVE'
             ELSE '✗ NONE' END
    FROM bcfy_playlists
    WHERE sync = TRUE;

END;
$$ LANGUAGE plpgsql;

-- Add view for pipeline statistics
CREATE OR REPLACE VIEW monitoring.pipeline_stats AS
SELECT * FROM get_pipeline_stats();

RAISE NOTICE '✓ Statistics functions and views created';

-- ============================================================
-- PART 6: CREATE ADMIN FUNCTIONS
-- ============================================================
RAISE NOTICE 'Step 6: Creating administrative functions...';

-- Function to reset retry counts for old errors
CREATE OR REPLACE FUNCTION reset_old_error_retries(p_days_ago INTEGER DEFAULT 7)
RETURNS TABLE(call_uid TEXT, reset BOOLEAN) AS $$
BEGIN
    RETURN QUERY
    UPDATE processing_state
    SET
        retry_count = 0,
        status = 'queued',
        last_error = NULL,
        updated_at = NOW()
    WHERE
        status = 'error'
        AND updated_at < NOW() - (p_days_ago || ' days')::INTERVAL
        AND retry_count >= max_retries
    RETURNING call_uid, TRUE;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old polling logs
CREATE OR REPLACE FUNCTION cleanup_playlist_poll_logs(p_days_ago INTEGER DEFAULT 30)
RETURNS TABLE(deleted_count BIGINT, oldest_kept TIMESTAMPTZ) AS $$
DECLARE
    v_deleted BIGINT;
    v_oldest TIMESTAMPTZ;
BEGIN
    DELETE FROM bcfy_playlist_poll_log
    WHERE poll_started_at < NOW() - (p_days_ago || ' days')::INTERVAL;

    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    SELECT MIN(poll_started_at) INTO v_oldest
    FROM bcfy_playlist_poll_log;

    deleted_count := v_deleted;
    oldest_kept := v_oldest;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

RAISE NOTICE '✓ Administrative functions created';

-- ============================================================
-- PART 7: CREATE MONITORING VIEWS FOR NEW COLUMNS
-- ============================================================
RAISE NOTICE 'Step 7: Creating advanced monitoring views...';

-- View for playlist sync health
CREATE OR REPLACE VIEW monitoring.playlist_sync_health AS
SELECT
    uuid,
    name,
    sync,
    last_synced_at,
    NOW() - last_synced_at AS staleness,
    sync_error_count,
    CASE
        WHEN NOT sync THEN 'DISABLED'
        WHEN NOW() - last_synced_at < INTERVAL '15 minutes' THEN '✓ FRESH'
        WHEN NOW() - last_synced_at < INTERVAL '1 hour' THEN '⚠ STALE'
        ELSE '✗ VERY_STALE'
    END AS sync_status,
    CASE
        WHEN sync_error_count = 0 THEN '✓ HEALTHY'
        WHEN sync_error_count < 5 THEN '⚠ ERRORS'
        ELSE '✗ FAILING'
    END AS health_status
FROM bcfy_playlists
ORDER BY sync DESC, last_synced_at DESC;

-- View for processing pipeline status
CREATE OR REPLACE VIEW monitoring.processing_pipeline_status AS
SELECT
    status,
    COUNT(*) AS count,
    AVG(retry_count) AS avg_retries,
    MAX(retry_count) AS max_retries_used,
    MIN(updated_at) AS oldest_item_age,
    NOW() - MIN(updated_at) AS age_of_oldest,
    CASE
        WHEN status = 'indexed' THEN '✓ COMPLETE'
        WHEN status = 'transcribed' THEN '→ INDEXING'
        WHEN status = 'downloaded' THEN '→ TRANSCRIBING'
        WHEN status = 'queued' THEN '→ DOWNLOADING'
        WHEN status = 'error' THEN '✗ FAILED'
    END AS stage_description
FROM processing_state
GROUP BY status
ORDER BY
    CASE status
        WHEN 'queued' THEN 1
        WHEN 'downloading' THEN 2
        WHEN 'downloaded' THEN 3
        WHEN 'transcribed' THEN 4
        WHEN 'indexed' THEN 5
        WHEN 'error' THEN 6
    END;

-- View for call processing health
CREATE OR REPLACE VIEW monitoring.call_processing_health AS
SELECT
    COUNT(*) FILTER (WHERE processed = TRUE) AS successfully_processed,
    COUNT(*) FILTER (WHERE processed = FALSE AND error IS NULL) AS pending_audio_processing,
    COUNT(*) FILTER (WHERE error IS NOT NULL) AS failed_audio_processing,
    COUNT(*) FILTER (WHERE retry_count > 0) AS items_with_retries,
    COUNT(*) AS total_calls,
    ROUND(100.0 * COUNT(*) FILTER (WHERE processed = TRUE) / NULLIF(COUNT(*), 0), 2) AS processing_completion_pct,
    MAX(updated_at) AS last_update
FROM bcfy_calls_raw;

RAISE NOTICE '✓ Monitoring views created';

-- ============================================================
-- PART 8: GRANT PERMISSIONS ON NEW FUNCTIONS/VIEWS
-- ============================================================
RAISE NOTICE 'Step 8: Granting permissions...';

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION advance_processing_state(TEXT, TEXT, TEXT) TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_stuck_processing_items(INTEGER) TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_pipeline_stats() TO PUBLIC;
GRANT EXECUTE ON FUNCTION reset_old_error_retries(INTEGER) TO PUBLIC;
GRANT EXECUTE ON FUNCTION cleanup_playlist_poll_logs(INTEGER) TO PUBLIC;

-- Grant select on views
GRANT SELECT ON monitoring.pipeline_stats TO PUBLIC;
GRANT SELECT ON monitoring.playlist_sync_health TO PUBLIC;
GRANT SELECT ON monitoring.processing_pipeline_status TO PUBLIC;
GRANT SELECT ON monitoring.call_processing_health TO PUBLIC;

RAISE NOTICE '✓ Permissions granted';

-- ============================================================
-- COMMIT
-- ============================================================
COMMIT;

-- ============================================================
-- SUMMARY
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Phase 3 Schema Improvements Complete! ✓';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Schema enhancements:';
    RAISE NOTICE '  ✓ bcfy_playlists: Added sync tracking and error counting';
    RAISE NOTICE '  ✓ bcfy_calls_raw: Added processing stage and retry tracking';
    RAISE NOTICE '  ✓ processing_state: Added retry limits and timestamps';
    RAISE NOTICE '';
    RAISE NOTICE 'New helper functions:';
    RAISE NOTICE '  • advance_processing_state() - Safe state transitions';
    RAISE NOTICE '  • get_stuck_processing_items() - Find bottlenecks';
    RAISE NOTICE '  • get_pipeline_stats() - Quick health check';
    RAISE NOTICE '  • reset_old_error_retries() - Retry failed items';
    RAISE NOTICE '  • cleanup_playlist_poll_logs() - Maintenance';
    RAISE NOTICE '';
    RAISE NOTICE 'New monitoring views:';
    RAISE NOTICE '  • monitoring.pipeline_stats - Overall statistics';
    RAISE NOTICE '  • monitoring.playlist_sync_health - Playlist sync status';
    RAISE NOTICE '  • monitoring.processing_pipeline_status - Pipeline stages';
    RAISE NOTICE '  • monitoring.call_processing_health - Processing metrics';
    RAISE NOTICE '';
    RAISE NOTICE 'Recommended queries:';
    RAISE NOTICE '  SELECT * FROM monitoring.pipeline_stats;';
    RAISE NOTICE '  SELECT * FROM monitoring.processing_pipeline_status;';
    RAISE NOTICE '  SELECT * FROM monitoring.playlist_sync_health WHERE sync_error_count > 0;';
    RAISE NOTICE '  SELECT * FROM get_stuck_processing_items();';
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
END $$;
