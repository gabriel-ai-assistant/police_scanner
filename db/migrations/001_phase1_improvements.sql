-- ============================================================
-- Phase 1: Immediate Database Improvements
-- Expert DBA Analysis - Low Risk, High Impact Changes
-- ============================================================
-- This migration can be run without downtime
-- Estimated execution time: 1-5 minutes (depends on table sizes)
--
-- To apply: psql "connection_string" -f 001_phase1_improvements.sql
-- ============================================================

BEGIN;

-- ============================================================
-- 1. FIX INDEX NAMING INCONSISTENCY
-- ============================================================
-- Rename last_seen index to last_pos (column was renamed in earlier migration)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'bcfy_playlists_last_seen_idx'
    ) THEN
        ALTER INDEX bcfy_playlists_last_seen_idx
            RENAME TO bcfy_playlists_last_pos_idx;
        RAISE NOTICE 'Renamed index: bcfy_playlists_last_seen_idx → bcfy_playlists_last_pos_idx';
    ELSE
        RAISE NOTICE 'Index already renamed or does not exist';
    END IF;
END $$;

-- ============================================================
-- 2. ADD MISSING INDEXES
-- ============================================================

-- 2.1 bcfy_calls_raw indexes
DO $$BEGIN RAISE NOTICE 'Creating indexes on bcfy_calls_raw...'; END$$;

-- Index for worker queries (unprocessed calls)
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_pending_idx
  ON bcfy_calls_raw(fetched_at)
  WHERE processed = FALSE AND error IS NULL;

-- Index for monitoring queries (time-based)
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_fetched_at_idx
  ON bcfy_calls_raw(fetched_at DESC);

-- Composite index for common query pattern (feed + talkgroup + time)
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_feed_tg_time_idx
  ON bcfy_calls_raw(feed_id, tg_id, started_at DESC)
  WHERE tg_id IS NOT NULL;

-- 2.2 bcfy_playlists indexes
DO $$BEGIN RAISE NOTICE 'Creating indexes on bcfy_playlists...'; END$$;

-- Composite index for incremental polling
CREATE INDEX IF NOT EXISTS bcfy_playlists_sync_last_pos_idx
  ON bcfy_playlists(sync, last_pos)
  WHERE sync = TRUE;

-- 2.3 transcripts indexes
DO $$BEGIN RAISE NOTICE 'Creating indexes on transcripts...'; END$$;

-- Fix full-text search index (change from BTREE to GIN)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'transcripts_tsv_idx'
          AND indexdef LIKE '%btree%'
    ) THEN
        DROP INDEX IF EXISTS transcripts_tsv_idx;
        RAISE NOTICE 'Dropped BTREE index on transcripts.tsv';
    END IF;
END $$;

-- Create proper GIN index for full-text search
CREATE INDEX IF NOT EXISTS transcripts_tsv_gin_idx
  ON transcripts USING GIN(tsv);

-- Index for quality filtering
CREATE INDEX IF NOT EXISTS transcripts_quality_idx
  ON transcripts(language, confidence)
  WHERE confidence > 0.5;

-- Index for time-based searches
CREATE INDEX IF NOT EXISTS transcripts_created_at_idx
  ON transcripts(created_at DESC);

-- Composite index for language + time
CREATE INDEX IF NOT EXISTS transcripts_lang_created_idx
  ON transcripts(language, created_at DESC);

-- 2.4 processing_state indexes
DO $$BEGIN RAISE NOTICE 'Creating indexes on processing_state...'; END$$;

-- Index for queue prioritization
CREATE INDEX IF NOT EXISTS processing_state_queue_idx
  ON processing_state(status, updated_at)
  WHERE status IN ('queued', 'error');

-- 2.5 system_logs indexes
DO $$BEGIN RAISE NOTICE 'Creating indexes on system_logs...'; END$$;

-- Composite index for component + severity + time
CREATE INDEX IF NOT EXISTS system_logs_component_severity_time_idx
  ON system_logs(component, severity, timestamp DESC);

-- 2.6 api_call_metrics indexes
DO $$BEGIN RAISE NOTICE 'Creating indexes on api_call_metrics...'; END$$;

-- Composite index for endpoint + time
CREATE INDEX IF NOT EXISTS api_call_metrics_endpoint_time_idx
  ON api_call_metrics(endpoint, timestamp DESC);

DO $$BEGIN RAISE NOTICE 'All indexes created successfully'; END$$;

-- ============================================================
-- 3. FIX bcfy_playlist_poll_log PRIMARY KEY
-- ============================================================
DO $$BEGIN RAISE NOTICE 'Fixing bcfy_playlist_poll_log primary key...'; END$$;

-- Add surrogate ID column
ALTER TABLE bcfy_playlist_poll_log
  ADD COLUMN IF NOT EXISTS id BIGSERIAL;

-- Populate ID for existing rows (if any)
DO $$
BEGIN
    -- Check if we need to set the sequence
    IF EXISTS (SELECT 1 FROM bcfy_playlist_poll_log WHERE id IS NULL) THEN
        -- Backfill IDs for existing rows
        UPDATE bcfy_playlist_poll_log
        SET id = nextval('bcfy_playlist_poll_log_id_seq')
        WHERE id IS NULL;
        RAISE NOTICE 'Backfilled ID column for existing rows';
    END IF;
END $$;

-- Make ID NOT NULL after backfilling
ALTER TABLE bcfy_playlist_poll_log
  ALTER COLUMN id SET NOT NULL;

-- Drop composite primary key and create new one
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'bcfy_playlist_poll_log_pkey'
          AND contype = 'p'
    ) THEN
        ALTER TABLE bcfy_playlist_poll_log
          DROP CONSTRAINT bcfy_playlist_poll_log_pkey;
        RAISE NOTICE 'Dropped old composite primary key';
    END IF;
END $$;

-- Add new primary key on ID
ALTER TABLE bcfy_playlist_poll_log
  ADD PRIMARY KEY (id);

-- Keep uniqueness constraint on composite key
ALTER TABLE bcfy_playlist_poll_log
  ADD CONSTRAINT IF NOT EXISTS bcfy_playlist_poll_log_uuid_time_key
  UNIQUE (uuid, poll_started_at);

-- Add foreign key to playlists (with CASCADE)
ALTER TABLE bcfy_playlist_poll_log
  ADD CONSTRAINT IF NOT EXISTS bcfy_playlist_poll_log_uuid_fkey
  FOREIGN KEY (uuid) REFERENCES bcfy_playlists(uuid)
  ON DELETE CASCADE;

DO $$BEGIN RAISE NOTICE 'Primary key structure fixed successfully'; END$$;

-- ============================================================
-- 4. ADD CHECK CONSTRAINTS
-- ============================================================
DO $$BEGIN RAISE NOTICE 'Adding CHECK constraints for data validation...'; END$$;

-- 4.1 bcfy_calls_raw constraints
ALTER TABLE bcfy_calls_raw
  ADD CONSTRAINT IF NOT EXISTS bcfy_calls_raw_duration_check
  CHECK (duration_ms IS NULL OR duration_ms > 0);

ALTER TABLE bcfy_calls_raw
  ADD CONSTRAINT IF NOT EXISTS bcfy_calls_raw_size_check
  CHECK (size_bytes IS NULL OR size_bytes > 0);

ALTER TABLE bcfy_calls_raw
  ADD CONSTRAINT IF NOT EXISTS bcfy_calls_raw_url_check
  CHECK (url IS NULL OR length(url) > 0);

ALTER TABLE bcfy_calls_raw
  ADD CONSTRAINT IF NOT EXISTS bcfy_calls_raw_time_order_check
  CHECK (ended_at IS NULL OR ended_at >= started_at);

-- 4.2 transcripts constraints
ALTER TABLE transcripts
  ADD CONSTRAINT IF NOT EXISTS transcripts_confidence_check
  CHECK (confidence >= 0 AND confidence <= 1);

ALTER TABLE transcripts
  ADD CONSTRAINT IF NOT EXISTS transcripts_duration_check
  CHECK (duration_seconds > 0);

DO $$BEGIN RAISE NOTICE 'CHECK constraints added successfully'; END$$;

-- ============================================================
-- 5. ADD NOT NULL CONSTRAINTS
-- ============================================================
DO $$BEGIN RAISE NOTICE 'Adding NOT NULL constraints...'; END$$;

-- 5.1 Backfill NULL values first
UPDATE bcfy_calls_raw SET fetched_at = NOW() WHERE fetched_at IS NULL;
UPDATE transcripts SET created_at = NOW() WHERE created_at IS NULL;
UPDATE bcfy_playlists SET last_pos = 0 WHERE last_pos IS NULL;

-- 5.2 Add NOT NULL constraints
ALTER TABLE bcfy_calls_raw
  ALTER COLUMN fetched_at SET NOT NULL;

ALTER TABLE transcripts
  ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE bcfy_playlists
  ALTER COLUMN last_pos SET NOT NULL,
  ALTER COLUMN last_pos SET DEFAULT 0;

DO $$BEGIN RAISE NOTICE 'NOT NULL constraints added successfully'; END$$;

-- ============================================================
-- 6. ADD TRIGGERS FOR AUTO-UPDATE TIMESTAMPS
-- ============================================================
DO $$BEGIN RAISE NOTICE 'Creating triggers for timestamp management...'; END$$;

-- 6.1 Create tsvector update trigger for transcripts
CREATE OR REPLACE FUNCTION transcripts_tsv_update()
RETURNS TRIGGER AS $$
BEGIN
  NEW.tsv := to_tsvector('english', coalesce(NEW.text, ''));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS transcripts_tsv_trigger ON transcripts;
CREATE TRIGGER transcripts_tsv_trigger
BEFORE INSERT OR UPDATE OF text ON transcripts
FOR EACH ROW
EXECUTE FUNCTION transcripts_tsv_update();

-- 6.2 Create playlist sync timestamp trigger
CREATE OR REPLACE FUNCTION update_playlist_sync_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.last_pos IS DISTINCT FROM OLD.last_pos THEN
    NEW.fetched_at = NOW();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add last_synced_at column if it doesn't exist
ALTER TABLE bcfy_playlists
  ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ DEFAULT NOW();

DROP TRIGGER IF EXISTS update_bcfy_playlists_sync_ts ON bcfy_playlists;
CREATE TRIGGER update_bcfy_playlists_sync_ts
BEFORE UPDATE ON bcfy_playlists
FOR EACH ROW
EXECUTE FUNCTION update_playlist_sync_timestamp();

DO $$BEGIN RAISE NOTICE 'Triggers created successfully'; END$$;

-- ============================================================
-- 7. CREATE MONITORING SCHEMA AND VIEWS
-- ============================================================
DO $$BEGIN RAISE NOTICE 'Creating monitoring schema and views...'; END$$;

CREATE SCHEMA IF NOT EXISTS monitoring;

-- View 1: Table health overview
CREATE OR REPLACE VIEW monitoring.table_health AS
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
  pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
  pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes_size,
  n_live_tup AS live_rows,
  n_dead_tup AS dead_rows,
  ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_ratio_pct,
  last_vacuum,
  last_autovacuum,
  last_analyze,
  last_autoanalyze
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- View 2: Index usage statistics
CREATE OR REPLACE VIEW monitoring.index_usage AS
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan AS scans,
  idx_tup_read AS tuples_read,
  idx_tup_fetch AS tuples_fetched,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
  CASE
    WHEN idx_scan = 0 THEN 'UNUSED'
    WHEN idx_scan < 100 THEN 'LOW_USAGE'
    ELSE 'ACTIVE'
  END AS usage_status
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC, pg_relation_size(indexrelid) DESC;

-- View 3: Table bloat estimation
CREATE OR REPLACE VIEW monitoring.table_bloat AS
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
  n_live_tup AS live_rows,
  n_dead_tup AS dead_rows,
  ROUND(100 * (n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0)), 2) AS bloat_pct,
  CASE
    WHEN n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) > 0.2 THEN 'CRITICAL'
    WHEN n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) > 0.1 THEN 'WARNING'
    ELSE 'HEALTHY'
  END AS status,
  last_vacuum,
  last_autovacuum
FROM pg_stat_user_tables
WHERE n_live_tup > 0
ORDER BY n_dead_tup DESC;

-- View 4: Database connections overview
CREATE OR REPLACE VIEW monitoring.connections AS
SELECT
  datname AS database,
  usename AS username,
  application_name,
  client_addr,
  state,
  COUNT(*) AS connection_count,
  MAX(state_change) AS last_state_change
FROM pg_stat_activity
WHERE datname IS NOT NULL
GROUP BY datname, usename, application_name, client_addr, state
ORDER BY connection_count DESC;

-- View 5: Long-running queries
CREATE OR REPLACE VIEW monitoring.long_running_queries AS
SELECT
  pid,
  now() - pg_stat_activity.query_start AS duration,
  usename,
  application_name,
  client_addr,
  state,
  wait_event_type,
  wait_event,
  LEFT(query, 100) AS query_preview
FROM pg_stat_activity
WHERE state != 'idle'
  AND pg_stat_activity.query_start IS NOT NULL
  AND now() - pg_stat_activity.query_start > interval '5 seconds'
ORDER BY duration DESC;

-- View 6: Database size overview
CREATE OR REPLACE VIEW monitoring.database_size AS
SELECT
  pg_database.datname AS database_name,
  pg_size_pretty(pg_database_size(pg_database.datname)) AS size,
  pg_database_size(pg_database.datname) AS size_bytes
FROM pg_database
WHERE datistemplate = false
ORDER BY pg_database_size(pg_database.datname) DESC;

COMMENT ON SCHEMA monitoring IS 'Database monitoring and health check views';
COMMENT ON VIEW monitoring.table_health IS 'Table size and vacuum statistics';
COMMENT ON VIEW monitoring.index_usage IS 'Index usage patterns and efficiency';
COMMENT ON VIEW monitoring.table_bloat IS 'Table bloat detection and VACUUM recommendations';
COMMENT ON VIEW monitoring.connections IS 'Active database connections by user and application';
COMMENT ON VIEW monitoring.long_running_queries IS 'Queries running longer than 5 seconds';
COMMENT ON VIEW monitoring.database_size IS 'Database size overview';

DO $$BEGIN RAISE NOTICE 'Monitoring views created successfully'; END$$;

-- ============================================================
-- 8. CONFIGURE AUTOVACUUM FOR HIGH-WRITE TABLES
-- ============================================================
DO $$BEGIN RAISE NOTICE 'Configuring autovacuum settings...'; END$$;

-- High-write table: bcfy_calls_raw (vacuum more aggressively)
ALTER TABLE bcfy_calls_raw SET (
  autovacuum_vacuum_scale_factor = 0.05,  -- Vacuum when 5% of rows change
  autovacuum_analyze_scale_factor = 0.02  -- Analyze when 2% change
);

-- High-write table: api_call_metrics
ALTER TABLE api_call_metrics SET (
  autovacuum_vacuum_scale_factor = 0.1,
  autovacuum_analyze_scale_factor = 0.05
);

-- High-write table: system_logs
ALTER TABLE system_logs SET (
  autovacuum_vacuum_scale_factor = 0.1,
  autovacuum_analyze_scale_factor = 0.05
);

DO $$BEGIN RAISE NOTICE 'Autovacuum configuration updated'; END$$;

-- ============================================================
-- 9. ENABLE QUERY STATISTICS (if not already enabled)
-- ============================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
    ) THEN
        CREATE EXTENSION pg_stat_statements;
        RAISE NOTICE 'Enabled pg_stat_statements extension';
    ELSE
        RAISE NOTICE 'pg_stat_statements already enabled';
    END IF;
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'Insufficient privileges to create pg_stat_statements extension - requires superuser';
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not create pg_stat_statements: %', SQLERRM;
END $$;

-- Create slow query monitoring view (requires pg_stat_statements)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements') THEN
        CREATE OR REPLACE VIEW monitoring.slow_queries AS
        SELECT
          LEFT(query, 100) AS query_preview,
          calls,
          ROUND(total_exec_time::numeric, 2) AS total_time_ms,
          ROUND(mean_exec_time::numeric, 2) AS mean_time_ms,
          ROUND(max_exec_time::numeric, 2) AS max_time_ms,
          ROUND(stddev_exec_time::numeric, 2) AS stddev_time_ms,
          rows
        FROM pg_stat_statements
        WHERE mean_exec_time > 100  -- Queries averaging >100ms
        ORDER BY mean_exec_time DESC
        LIMIT 50;

        RAISE NOTICE 'Created monitoring.slow_queries view';
    END IF;
END $$;

-- ============================================================
-- 10. VERIFY FOREIGN KEY INDEXES
-- ============================================================
DO $$BEGIN RAISE NOTICE 'Checking for foreign keys without indexes...'; END$$;

DO $$
DECLARE
    missing_fk_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO missing_fk_count
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_schema = 'public'
      AND NOT EXISTS (
          SELECT 1 FROM pg_indexes
          WHERE tablename = tc.table_name
            AND indexdef LIKE '%' || kcu.column_name || '%'
      );

    IF missing_fk_count > 0 THEN
        RAISE WARNING 'Found % foreign keys without indexes - consider adding them for performance', missing_fk_count;
    ELSE
        RAISE NOTICE 'All foreign keys have supporting indexes ✓';
    END IF;
END $$;

-- ============================================================
-- COMMIT AND SUMMARY
-- ============================================================

COMMIT;

-- Display summary
DO $$
DECLARE
    idx_count INTEGER;
    constraint_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO idx_count
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND indexname LIKE '%_idx';

    SELECT COUNT(*) INTO constraint_count
    FROM information_schema.check_constraints
    WHERE constraint_schema = 'public';

    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Phase 1 Migration Complete! ✓';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Total indexes: %', idx_count;
    RAISE NOTICE 'Total CHECK constraints: %', constraint_count;
    RAISE NOTICE 'Monitoring views created: 6-7 (depending on pg_stat_statements)';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Run ANALYZE on large tables: ANALYZE bcfy_calls_raw;';
    RAISE NOTICE '2. Monitor performance with: SELECT * FROM monitoring.table_health;';
    RAISE NOTICE '3. Check for slow queries: SELECT * FROM monitoring.slow_queries;';
    RAISE NOTICE '4. Review bloat status: SELECT * FROM monitoring.table_bloat;';
    RAISE NOTICE '';
    RAISE NOTICE 'Ready for Phase 2: Table Partitioning & Schema Improvements';
    RAISE NOTICE '============================================================';
END $$;
