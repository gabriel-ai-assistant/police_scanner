-- ============================================================
-- Phase 2: Table Partitioning for Time-Series Data
-- Expert DBA Analysis - Zero-Downtime Implementation
-- ============================================================
-- This migration implements native PostgreSQL partitioning for:
-- - bcfy_calls_raw (monthly)
-- - transcripts (monthly)
-- - api_call_metrics (weekly)
-- - system_logs (daily)
--
-- Estimated execution time: 5-30 minutes (depends on data volume)
-- Downtime: None (zero-downtime approach)
--
-- IMPORTANT NOTES:
-- 1. This creates NEW partitioned tables alongside existing ones
-- 2. You must migrate data and switch over (see migration steps)
-- 3. Test on staging first!
--
-- To apply: psql "connection_string" -f 002_phase2_partitioning.sql
-- ============================================================

BEGIN;

-- ============================================================
-- PART 1: PREPARE PARTITION MANAGEMENT FUNCTIONS
-- ============================================================
DO $$BEGIN RAISE NOTICE ''; END$$;
DO $$BEGIN RAISE NOTICE '============================================================'; END$$;
DO $$BEGIN RAISE NOTICE 'PHASE 2: Table Partitioning for Time-Series Data'; END$$;
DO $$BEGIN RAISE NOTICE '============================================================'; END$$;
DO $$BEGIN RAISE NOTICE ''; END$$;

DO $$BEGIN RAISE NOTICE 'Step 1: Creating partition management functions...'; END$$;

-- Function to automatically create future partitions
CREATE OR REPLACE FUNCTION create_partition_if_not_exists(
    parent_table TEXT,
    partition_date DATE,
    interval_type TEXT -- 'month', 'week', or 'day'
) RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    start_date TIMESTAMP;
    end_date TIMESTAMP;
    table_exists BOOLEAN;
BEGIN
    -- Calculate partition bounds based on interval
    start_date := date_trunc(interval_type, partition_date::TIMESTAMP);
    end_date := start_date + ('1 ' || interval_type)::INTERVAL;

    -- Generate partition name (e.g., bcfy_calls_raw_2025_01)
    IF interval_type = 'month' THEN
        partition_name := parent_table || '_' || to_char(start_date, 'YYYY_MM');
    ELSIF interval_type = 'week' THEN
        partition_name := parent_table || '_' || to_char(start_date, 'YYYY_WW');
    ELSIF interval_type = 'day' THEN
        partition_name := parent_table || '_' || to_char(start_date, 'YYYY_MM_DD');
    ELSE
        RAISE EXCEPTION 'Invalid interval_type: %', interval_type;
    END IF;

    -- Check if partition already exists
    SELECT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) INTO table_exists;

    -- Create partition if it doesn't exist
    IF NOT table_exists THEN
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
            partition_name, parent_table, start_date, end_date
        );
        RAISE NOTICE '✓ Created partition: %', partition_name;
    ELSE
        RAISE NOTICE '• Partition already exists: %', partition_name;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to create partitions for a date range
CREATE OR REPLACE FUNCTION create_partitions_for_range(
    parent_table TEXT,
    start_date DATE,
    end_date DATE,
    interval_type TEXT
) RETURNS TABLE(partition_name TEXT, created BOOLEAN) AS $$
DECLARE
    current_date DATE;
    partition_name TEXT;
    table_exists BOOLEAN;
    partition_start TIMESTAMP;
    partition_end TIMESTAMP;
BEGIN
    current_date := start_date;

    WHILE current_date <= end_date LOOP
        -- Calculate partition bounds
        partition_start := date_trunc(interval_type, current_date::TIMESTAMP);
        partition_end := partition_start + ('1 ' || interval_type)::INTERVAL;

        -- Generate partition name
        IF interval_type = 'month' THEN
            partition_name := parent_table || '_' || to_char(partition_start, 'YYYY_MM');
        ELSIF interval_type = 'week' THEN
            partition_name := parent_table || '_' || to_char(partition_start, 'YYYY_WW');
        ELSIF interval_type = 'day' THEN
            partition_name := parent_table || '_' || to_char(partition_start, 'YYYY_MM_DD');
        END IF;

        -- Check if partition already exists
        SELECT EXISTS (
            SELECT 1 FROM pg_class WHERE relname = partition_name
        ) INTO table_exists;

        -- Create partition if needed
        IF NOT table_exists THEN
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                partition_name, parent_table, partition_start, partition_end
            );
            created := TRUE;
        ELSE
            created := FALSE;
        END IF;

        RETURN NEXT;

        -- Move to next interval
        IF interval_type = 'month' THEN
            current_date := current_date + INTERVAL '1 month';
        ELSIF interval_type = 'week' THEN
            current_date := current_date + INTERVAL '1 week';
        ELSIF interval_type = 'day' THEN
            current_date := current_date + INTERVAL '1 day';
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

DO $$BEGIN RAISE NOTICE '✓ Partition management functions created'; END$$;

-- ============================================================
-- PART 2: PARTITION bcfy_calls_raw (BY MONTH)
-- ============================================================
DO $$BEGIN RAISE NOTICE ''; END$$;
DO $$BEGIN RAISE NOTICE 'Step 2: Creating partitioned bcfy_calls_raw table...'; END$$;

-- Check if table is already partitioned
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_partitioned_table pt ON c.oid = pt.partrelid
        WHERE c.relname = 'bcfy_calls_raw'
    ) THEN
        RAISE NOTICE 'Table is not yet partitioned. Creating partitioned version...';

        -- Rename old table
        ALTER TABLE IF EXISTS bcfy_calls_raw RENAME TO bcfy_calls_raw_nonpartitioned;
        RAISE NOTICE '✓ Renamed old table to bcfy_calls_raw_nonpartitioned';

        -- Create partitioned table with same structure
        CREATE TABLE bcfy_calls_raw (
            call_uid TEXT,
            group_id TEXT,
            ts BIGINT,
            feed_id INTEGER,
            tg_id BIGINT,
            tag_id INTEGER,
            node_id BIGINT,
            sid BIGINT,
            site_id BIGINT,
            freq DOUBLE PRECISION,
            src BIGINT,
            url TEXT,
            started_at TIMESTAMPTZ NOT NULL,
            ended_at TIMESTAMPTZ,
            duration_ms BIGINT,
            size_bytes BIGINT,
            fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            raw_json JSONB,
            processed BOOLEAN DEFAULT FALSE,
            last_attempt TIMESTAMPTZ,
            error TEXT,
            PRIMARY KEY (call_uid, started_at),
            CONSTRAINT bcfy_calls_raw_group_ts_uidx UNIQUE (group_id, ts, started_at)
        ) PARTITION BY RANGE (started_at);

        RAISE NOTICE '✓ Created partitioned bcfy_calls_raw table';
    ELSE
        RAISE NOTICE '• Table is already partitioned';
    END IF;
END $$;

-- Create partitions for past 2 months + current month + next 2 months
DO $$BEGIN RAISE NOTICE 'Creating monthly partitions for bcfy_calls_raw...'; END$$;

SELECT create_partitions_for_range(
    'bcfy_calls_raw',
    CURRENT_DATE - INTERVAL '2 months',
    CURRENT_DATE + INTERVAL '2 months',
    'month'
);

-- Recreate indexes on partitioned table
DO $$BEGIN RAISE NOTICE 'Recreating indexes on bcfy_calls_raw...'; END$$;

CREATE INDEX IF NOT EXISTS bcfy_calls_raw_feed_idx ON bcfy_calls_raw(feed_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_tg_idx ON bcfy_calls_raw(tg_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_tag_idx ON bcfy_calls_raw(tag_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_start_idx ON bcfy_calls_raw(started_at);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_node_idx ON bcfy_calls_raw(node_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_sid_idx ON bcfy_calls_raw(sid);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_site_idx ON bcfy_calls_raw(site_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_fetched_at_idx ON bcfy_calls_raw(fetched_at DESC);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_pending_idx ON bcfy_calls_raw(fetched_at)
    WHERE processed = FALSE AND error IS NULL;
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_feed_tg_time_idx ON bcfy_calls_raw(feed_id, tg_id, started_at DESC)
    WHERE tg_id IS NOT NULL;

DO $$BEGIN RAISE NOTICE '✓ All indexes created on partitioned bcfy_calls_raw'; END$$;

-- ============================================================
-- PART 3: PARTITION transcripts (BY MONTH)
-- ============================================================
DO $$BEGIN RAISE NOTICE ''; END$$;
DO $$BEGIN RAISE NOTICE 'Step 3: Creating partitioned transcripts table...'; END$$;

-- Check if table is already partitioned
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_partitioned_table pt ON c.oid = pt.partrelid
        WHERE c.relname = 'transcripts'
    ) THEN
        RAISE NOTICE 'Creating partitioned transcripts table...';

        -- Rename old table
        ALTER TABLE IF EXISTS transcripts RENAME TO transcripts_nonpartitioned;
        RAISE NOTICE '✓ Renamed old table to transcripts_nonpartitioned';

        -- Create partitioned table
        CREATE TABLE transcripts (
            id BIGSERIAL,
            recording_id BIGINT,
            text TEXT,
            words JSONB,
            language TEXT,
            model_name TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            tsv tsvector,
            duration_seconds NUMERIC NOT NULL,
            confidence NUMERIC NOT NULL,
            call_uid TEXT,
            s3_bucket TEXT,
            s3_key TEXT,
            PRIMARY KEY (id, created_at),
            CONSTRAINT transcripts_call_uid_key UNIQUE (call_uid, created_at)
        ) PARTITION BY RANGE (created_at);

        RAISE NOTICE '✓ Created partitioned transcripts table';
    ELSE
        RAISE NOTICE '• Table is already partitioned';
    END IF;
END $$;

-- Create monthly partitions for transcripts
DO $$BEGIN RAISE NOTICE 'Creating monthly partitions for transcripts...'; END$$;

SELECT create_partitions_for_range(
    'transcripts',
    CURRENT_DATE - INTERVAL '2 months',
    CURRENT_DATE + INTERVAL '2 months',
    'month'
);

-- Recreate indexes on partitioned transcripts
DO $$BEGIN RAISE NOTICE 'Recreating indexes on transcripts...'; END$$;

CREATE INDEX IF NOT EXISTS transcripts_lang_model_idx ON transcripts(language, model_name);
CREATE INDEX IF NOT EXISTS transcripts_recording_idx ON transcripts(recording_id);
CREATE INDEX IF NOT EXISTS transcripts_tsv_gin_idx ON transcripts USING GIN(tsv);
CREATE INDEX IF NOT EXISTS transcripts_quality_idx ON transcripts(language, confidence)
    WHERE confidence > 0.5;
CREATE INDEX IF NOT EXISTS transcripts_created_at_idx ON transcripts(created_at DESC);
CREATE INDEX IF NOT EXISTS transcripts_lang_created_idx ON transcripts(language, created_at DESC);

-- Recreate foreign key
ALTER TABLE transcripts
  ADD CONSTRAINT IF NOT EXISTS transcripts_call_fk
  FOREIGN KEY (call_uid) REFERENCES bcfy_calls_raw(call_uid)
  ON DELETE SET NULL;

DO $$BEGIN RAISE NOTICE '✓ All indexes created on partitioned transcripts'; END$$;

-- ============================================================
-- PART 4: PARTITION api_call_metrics (BY WEEK)
-- ============================================================
DO $$BEGIN RAISE NOTICE ''; END$$;
DO $$BEGIN RAISE NOTICE 'Step 4: Creating partitioned api_call_metrics table...'; END$$;

-- Check if table is already partitioned
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_partitioned_table pt ON c.oid = pt.partrelid
        WHERE c.relname = 'api_call_metrics'
    ) THEN
        RAISE NOTICE 'Creating partitioned api_call_metrics table...';

        -- Rename old table
        ALTER TABLE IF EXISTS api_call_metrics RENAME TO api_call_metrics_nonpartitioned;
        RAISE NOTICE '✓ Renamed old table to api_call_metrics_nonpartitioned';

        -- Create partitioned table
        CREATE TABLE api_call_metrics (
            id BIGSERIAL,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            endpoint TEXT NOT NULL,
            method TEXT DEFAULT 'GET',
            status_code INTEGER,
            duration_ms INTEGER,
            response_size INTEGER,
            cache_hit BOOLEAN DEFAULT FALSE,
            error TEXT,
            PRIMARY KEY (id, timestamp)
        ) PARTITION BY RANGE (timestamp);

        RAISE NOTICE '✓ Created partitioned api_call_metrics table';
    ELSE
        RAISE NOTICE '• Table is already partitioned';
    END IF;
END $$;

-- Create weekly partitions for api_call_metrics
DO $$BEGIN RAISE NOTICE 'Creating weekly partitions for api_call_metrics...'; END$$;

SELECT create_partitions_for_range(
    'api_call_metrics',
    CURRENT_DATE - INTERVAL '2 weeks',
    CURRENT_DATE + INTERVAL '2 weeks',
    'week'
);

-- Recreate indexes
DO $$BEGIN RAISE NOTICE 'Recreating indexes on api_call_metrics...'; END$$;

CREATE INDEX IF NOT EXISTS api_call_metrics_timestamp_idx ON api_call_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS api_call_metrics_endpoint_idx ON api_call_metrics(endpoint);
CREATE INDEX IF NOT EXISTS api_call_metrics_endpoint_time_idx ON api_call_metrics(endpoint, timestamp DESC);

DO $$BEGIN RAISE NOTICE '✓ All indexes created on partitioned api_call_metrics'; END$$;

-- ============================================================
-- PART 5: PARTITION system_logs (BY DAY)
-- ============================================================
DO $$BEGIN RAISE NOTICE ''; END$$;
DO $$BEGIN RAISE NOTICE 'Step 5: Creating partitioned system_logs table...'; END$$;

-- Check if table is already partitioned
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_partitioned_table pt ON c.oid = pt.partrelid
        WHERE c.relname = 'system_logs'
    ) THEN
        RAISE NOTICE 'Creating partitioned system_logs table...';

        -- Rename old table
        ALTER TABLE IF EXISTS system_logs RENAME TO system_logs_nonpartitioned;
        RAISE NOTICE '✓ Renamed old table to system_logs_nonpartitioned';

        -- Create partitioned table
        CREATE TABLE system_logs (
            id BIGSERIAL,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            component TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'INFO',
            message TEXT,
            metadata JSONB,
            duration_ms INTEGER,
            PRIMARY KEY (id, timestamp)
        ) PARTITION BY RANGE (timestamp);

        RAISE NOTICE '✓ Created partitioned system_logs table';
    ELSE
        RAISE NOTICE '• Table is already partitioned';
    END IF;
END $$;

-- Create daily partitions for system_logs
DO $$BEGIN RAISE NOTICE 'Creating daily partitions for system_logs...'; END$$;

SELECT create_partitions_for_range(
    'system_logs',
    CURRENT_DATE - INTERVAL '7 days',
    CURRENT_DATE + INTERVAL '7 days',
    'day'
);

-- Recreate indexes
DO $$BEGIN RAISE NOTICE 'Recreating indexes on system_logs...'; END$$;

CREATE INDEX IF NOT EXISTS system_logs_timestamp_idx ON system_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS system_logs_component_idx ON system_logs(component);
CREATE INDEX IF NOT EXISTS system_logs_event_type_idx ON system_logs(event_type);
CREATE INDEX IF NOT EXISTS system_logs_component_severity_time_idx ON system_logs(component, severity, timestamp DESC);

DO $$BEGIN RAISE NOTICE '✓ All indexes created on partitioned system_logs'; END$$;

-- ============================================================
-- PART 6: CREATE DATA RETENTION POLICIES
-- ============================================================
DO $$BEGIN RAISE NOTICE ''; END$$;
DO $$BEGIN RAISE NOTICE 'Step 6: Creating data retention policy framework...'; END$$;

-- Create retention policy configuration table
CREATE TABLE IF NOT EXISTS app_retention_policies (
    table_name TEXT PRIMARY KEY,
    retention_days INTEGER NOT NULL,
    partition_column TEXT NOT NULL,
    archive_table TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    last_cleanup_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT app_retention_policies_days_check CHECK (retention_days > 0)
);

-- Define retention policies
INSERT INTO app_retention_policies (table_name, retention_days, partition_column, archive_table, enabled)
VALUES
    ('bcfy_calls_raw', 90, 'started_at', NULL, TRUE),          -- Keep 90 days of calls
    ('transcripts', 180, 'created_at', NULL, TRUE),            -- Keep 180 days of transcripts
    ('api_call_metrics', 30, 'timestamp', NULL, TRUE),         -- Keep 30 days of API metrics
    ('system_logs', 30, 'timestamp', NULL, TRUE),              -- Keep 30 days of system logs
    ('bcfy_playlist_poll_log', 30, 'poll_started_at', NULL, TRUE) -- Keep 30 days of poll logs
ON CONFLICT (table_name) DO NOTHING;

DO $$BEGIN RAISE NOTICE '✓ Retention policies table created'; END$$;

-- Create cleanup function
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS TABLE(table_name TEXT, rows_deleted BIGINT, cleanup_duration_ms INTEGER) AS $$
DECLARE
    policy RECORD;
    deleted_count BIGINT;
    cleanup_start TIMESTAMP;
    cleanup_end TIMESTAMP;
    duration_ms INTEGER;
BEGIN
    FOR policy IN
        SELECT * FROM app_retention_policies WHERE enabled = TRUE
    LOOP
        cleanup_start := NOW();

        -- Delete old records
        EXECUTE format(
            'DELETE FROM %I WHERE %I < NOW() - INTERVAL ''%s days''',
            policy.table_name, policy.partition_column, policy.retention_days
        ) INTO deleted_count;

        cleanup_end := NOW();
        duration_ms := EXTRACT(EPOCH FROM (cleanup_end - cleanup_start))::INTEGER * 1000;

        -- Update last cleanup time
        UPDATE app_retention_policies
        SET last_cleanup_at = NOW()
        WHERE table_name = policy.table_name;

        IF deleted_count > 0 THEN
            RAISE NOTICE 'Cleaned % rows from % in %ms', deleted_count, policy.table_name, duration_ms;
        ELSE
            RAISE NOTICE 'No rows to clean from %', policy.table_name;
        END IF;

        table_name := policy.table_name;
        rows_deleted := deleted_count;
        cleanup_duration_ms := duration_ms;
        RETURN NEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

DO $$BEGIN RAISE NOTICE '✓ Data cleanup function created'; END$$;

-- ============================================================
-- PART 7: CREATE PARTITION MAINTENANCE FUNCTION
-- ============================================================
DO $$BEGIN RAISE NOTICE ''; END$$;
DO $$BEGIN RAISE NOTICE 'Step 7: Creating partition maintenance function...'; END$$;

CREATE OR REPLACE FUNCTION maintain_partitions()
RETURNS TABLE(action TEXT, partition_name TEXT) AS $$
DECLARE
    target_date DATE;
BEGIN
    -- Create partitions for future dates (stay 1 month ahead)
    target_date := CURRENT_DATE + INTERVAL '1 month';

    -- For bcfy_calls_raw and transcripts (monthly)
    RETURN QUERY
    SELECT 'CREATE_PARTITION'::TEXT, parent_table || '_' || to_char(date_trunc('month', target_date), 'YYYY_MM')::TEXT
    FROM (
        SELECT 'bcfy_calls_raw' AS parent_table
        UNION ALL
        SELECT 'transcripts' AS parent_table
    ) t
    WHERE NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = parent_table || '_' || to_char(date_trunc('month', target_date), 'YYYY_MM')
    );

    -- Create partitions for api_call_metrics (weekly)
    RETURN QUERY
    SELECT 'CREATE_PARTITION'::TEXT, 'api_call_metrics_' || to_char(date_trunc('week', target_date), 'YYYY_WW')::TEXT
    WHERE NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = 'api_call_metrics_' || to_char(date_trunc('week', target_date), 'YYYY_WW')
    );

    -- Create partitions for system_logs (daily for next 3 days)
    FOR i IN 0..3 LOOP
        RETURN QUERY
        SELECT 'CREATE_PARTITION'::TEXT, 'system_logs_' || to_char(CURRENT_DATE + (i || ' days')::INTERVAL, 'YYYY_MM_DD')::TEXT
        WHERE NOT EXISTS (
            SELECT 1 FROM pg_class WHERE relname = 'system_logs_' || to_char(CURRENT_DATE + (i || ' days')::INTERVAL, 'YYYY_MM_DD')
        );
    END LOOP;

    -- Execute partition creation
    PERFORM create_partition_if_not_exists('bcfy_calls_raw', target_date, 'month');
    PERFORM create_partition_if_not_exists('transcripts', target_date, 'month');
    PERFORM create_partition_if_not_exists('api_call_metrics', target_date, 'week');
    PERFORM create_partition_if_not_exists('system_logs', CURRENT_DATE, 'day');
    PERFORM create_partition_if_not_exists('system_logs', CURRENT_DATE + INTERVAL '1 day', 'day');
    PERFORM create_partition_if_not_exists('system_logs', CURRENT_DATE + INTERVAL '2 days', 'day');
    PERFORM create_partition_if_not_exists('system_logs', CURRENT_DATE + INTERVAL '3 days', 'day');
END;
$$ LANGUAGE plpgsql;

DO $$BEGIN RAISE NOTICE '✓ Partition maintenance function created'; END$$;

-- ============================================================
-- PART 8: CREATE PARTITION HEALTH VIEW
-- ============================================================
CREATE OR REPLACE VIEW monitoring.partition_health AS
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    n_live_tup AS row_count,
    CASE
        WHEN n_live_tup > 1000000 THEN 'LARGE'
        WHEN n_live_tup > 100000 THEN 'MEDIUM'
        ELSE 'SMALL'
    END AS size_category
FROM pg_stat_user_tables
WHERE tablename IN ('bcfy_calls_raw', 'transcripts', 'api_call_metrics', 'system_logs')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

DO $$BEGIN RAISE NOTICE '✓ Partition health view created'; END$$;

-- ============================================================
-- PART 9: MIGRATE DATA (IF NEEDED)
-- ============================================================
DO $$BEGIN RAISE NOTICE ''; END$$;
DO $$BEGIN RAISE NOTICE 'Step 8: Migrating data to partitioned tables...'; END$$;

-- Migrate bcfy_calls_raw if needed
DO $$
DECLARE
    record_count BIGINT;
BEGIN
    SELECT COUNT(*) INTO record_count FROM bcfy_calls_raw_nonpartitioned;

    IF record_count > 0 THEN
        RAISE NOTICE 'Migrating % records from bcfy_calls_raw_nonpartitioned...', record_count;
        INSERT INTO bcfy_calls_raw
        SELECT * FROM bcfy_calls_raw_nonpartitioned
        ON CONFLICT DO NOTHING;
        RAISE NOTICE '✓ Migration complete';
    ELSE
        RAISE NOTICE '• No data to migrate for bcfy_calls_raw';
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        RAISE NOTICE '• Source table does not exist (already migrated?)';
END $$;

-- Migrate transcripts if needed
DO $$
DECLARE
    record_count BIGINT;
BEGIN
    SELECT COUNT(*) INTO record_count FROM transcripts_nonpartitioned;

    IF record_count > 0 THEN
        RAISE NOTICE 'Migrating % records from transcripts_nonpartitioned...', record_count;
        INSERT INTO transcripts
        SELECT * FROM transcripts_nonpartitioned
        ON CONFLICT DO NOTHING;
        RAISE NOTICE '✓ Migration complete';
    ELSE
        RAISE NOTICE '• No data to migrate for transcripts';
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        RAISE NOTICE '• Source table does not exist (already migrated?)';
END $$;

-- Migrate api_call_metrics if needed
DO $$
DECLARE
    record_count BIGINT;
BEGIN
    SELECT COUNT(*) INTO record_count FROM api_call_metrics_nonpartitioned;

    IF record_count > 0 THEN
        RAISE NOTICE 'Migrating % records from api_call_metrics_nonpartitioned...', record_count;
        INSERT INTO api_call_metrics
        SELECT * FROM api_call_metrics_nonpartitioned
        ON CONFLICT DO NOTHING;
        RAISE NOTICE '✓ Migration complete';
    ELSE
        RAISE NOTICE '• No data to migrate for api_call_metrics';
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        RAISE NOTICE '• Source table does not exist (already migrated?)';
END $$;

-- Migrate system_logs if needed
DO $$
DECLARE
    record_count BIGINT;
BEGIN
    SELECT COUNT(*) INTO record_count FROM system_logs_nonpartitioned;

    IF record_count > 0 THEN
        RAISE NOTICE 'Migrating % records from system_logs_nonpartitioned...', record_count;
        INSERT INTO system_logs
        SELECT * FROM system_logs_nonpartitioned
        ON CONFLICT DO NOTHING;
        RAISE NOTICE '✓ Migration complete';
    ELSE
        RAISE NOTICE '• No data to migrate for system_logs';
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        RAISE NOTICE '• Source table does not exist (already migrated?)';
END $$;

-- ============================================================
-- COMMIT
-- ============================================================
COMMIT;

-- ============================================================
-- SUMMARY AND NEXT STEPS
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Phase 2 Migration Complete! ✓';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables partitioned:';
    RAISE NOTICE '  ✓ bcfy_calls_raw (monthly partitions)';
    RAISE NOTICE '  ✓ transcripts (monthly partitions)';
    RAISE NOTICE '  ✓ api_call_metrics (weekly partitions)';
    RAISE NOTICE '  ✓ system_logs (daily partitions)';
    RAISE NOTICE '';
    RAISE NOTICE 'Features added:';
    RAISE NOTICE '  ✓ Automated partition creation functions';
    RAISE NOTICE '  ✓ Data retention policy framework';
    RAISE NOTICE '  ✓ Partition maintenance function';
    RAISE NOTICE '  ✓ Partition health monitoring view';
    RAISE NOTICE '';
    RAISE NOTICE 'IMPORTANT NEXT STEPS:';
    RAISE NOTICE '1. Verify data migration was successful:';
    RAISE NOTICE '   SELECT COUNT(*) FROM bcfy_calls_raw;';
    RAISE NOTICE '   SELECT COUNT(*) FROM transcripts;';
    RAISE NOTICE '';
    RAISE NOTICE '2. Compare row counts with old non-partitioned tables';
    RAISE NOTICE '3. Drop old non-partitioned tables once verified:';
    RAISE NOTICE '   DROP TABLE bcfy_calls_raw_nonpartitioned;';
    RAISE NOTICE '   DROP TABLE transcripts_nonpartitioned;';
    RAISE NOTICE '   DROP TABLE api_call_metrics_nonpartitioned;';
    RAISE NOTICE '   DROP TABLE system_logs_nonpartitioned;';
    RAISE NOTICE '';
    RAISE NOTICE '4. Check partition health:';
    RAISE NOTICE '   SELECT * FROM monitoring.partition_health;';
    RAISE NOTICE '';
    RAISE NOTICE '5. Test maintenance functions:';
    RAISE NOTICE '   SELECT * FROM maintain_partitions();';
    RAISE NOTICE '   SELECT * FROM cleanup_old_data();';
    RAISE NOTICE '';
    RAISE NOTICE '6. Update application code to handle partitioned tables';
    RAISE NOTICE '   (Queries should work transparently, but verify)';
    RAISE NOTICE '';
    RAISE NOTICE '7. Consider setting up automated maintenance with pg_cron:';
    RAISE NOTICE '   CREATE EXTENSION pg_cron;';
    RAISE NOTICE '   SELECT cron.schedule(''maintain-partitions'', ''0 0 * * *'',';
    RAISE NOTICE '     ''SELECT maintain_partitions();'');';
    RAISE NOTICE '   SELECT cron.schedule(''cleanup-old-data'', ''0 2 * * *'',';
    RAISE NOTICE '     ''SELECT cleanup_old_data();'');';
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
END $$;
