-- ============================================================
-- Police Scanner - Full Schema (Updated 2025-12-10)
-- ============================================================
--
-- This schema reflects the production database state as of December 2025
-- Includes changes from:
--   - Migration 004: Audio quality metrics (audio_quality_score, etc.)
--   - Migration 005: S3 hierarchical storage (playlist_uuid, s3_key_v2)
--   - Migration 006: Transcription improvements (retry logic)
--   - Migration 001: Monitoring schema and views (consolidated)
--
-- NOT APPLIED (staged for future):
--   - Migration 002: Table partitioning (monthly/weekly/daily)
--   - Migration 003: Schema improvements (state management functions)
--
-- ============================================================

-- Optional reset
-- DROP SCHEMA public CASCADE;
-- CREATE SCHEMA public;

-- ============================================================
-- 0. EXTENSIONS
-- ============================================================
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- 1) BROADCASTIFY COMMON CACHE
-- ============================================================

CREATE TABLE IF NOT EXISTS bcfy_countries (
    coid          INTEGER PRIMARY KEY,
    country_name  TEXT NOT NULL,
    country_code  TEXT NOT NULL,
    iso_alpha2    TEXT,
    is_active     BOOLEAN DEFAULT TRUE,
    sync          BOOLEAN DEFAULT FALSE,
    notes         TEXT,
    fetched_at    TIMESTAMPTZ DEFAULT now(),
    raw_json      JSONB
);
CREATE INDEX IF NOT EXISTS bcfy_countries_country_code_idx ON bcfy_countries(country_code);

CREATE TABLE IF NOT EXISTS bcfy_states (
    stid          INTEGER PRIMARY KEY,
    coid          INTEGER NOT NULL REFERENCES bcfy_countries(coid) ON DELETE CASCADE,
    state_name    TEXT NOT NULL,
    state_code    TEXT NOT NULL,
    is_active     BOOLEAN DEFAULT TRUE,
    sync          BOOLEAN DEFAULT FALSE,
    fetched_at    TIMESTAMPTZ DEFAULT now(),
    raw_json      JSONB
);
CREATE INDEX IF NOT EXISTS bcfy_states_coid_idx       ON bcfy_states(coid);
CREATE INDEX IF NOT EXISTS bcfy_states_state_code_idx ON bcfy_states(state_code);

CREATE TABLE IF NOT EXISTS bcfy_counties (
    cntid          INTEGER NOT NULL,
    stid           INTEGER NOT NULL REFERENCES bcfy_states(stid) ON DELETE CASCADE,
    coid           INTEGER NOT NULL REFERENCES bcfy_countries(coid) ON DELETE CASCADE,
    county_name    TEXT NOT NULL,
    county_header  TEXT,
    type           SMALLINT NOT NULL,
    lat            NUMERIC(9,6),
    lon            NUMERIC(9,6),
    range          INTEGER,
    fips           TEXT,
    timezone_str   TEXT,
    state_name     TEXT,
    state_code     TEXT,
    country_name   TEXT,
    country_code   TEXT,
    is_active      BOOLEAN DEFAULT TRUE,
    sync           BOOLEAN DEFAULT FALSE,
    fetched_at     TIMESTAMPTZ DEFAULT now(),
    raw_json       JSONB,
    CONSTRAINT bcfy_counties_pkey PRIMARY KEY (cntid)
);
CREATE INDEX IF NOT EXISTS bcfy_counties_stid_idx ON bcfy_counties(stid);
CREATE INDEX IF NOT EXISTS bcfy_counties_coid_idx ON bcfy_counties(coid);
CREATE INDEX IF NOT EXISTS bcfy_counties_fips_idx ON bcfy_counties(fips);
CREATE INDEX IF NOT EXISTS bcfy_counties_name_idx ON bcfy_counties(county_name);

-- ============================================================
-- 2) PLAYLISTS AND POLL LOG
-- ============================================================

CREATE TABLE IF NOT EXISTS bcfy_playlists (
    uuid           UUID PRIMARY KEY,
    name           TEXT,
    sync           BOOLEAN DEFAULT FALSE,
    descr          TEXT,
    ts             BIGINT,
    last_seen      BIGINT,
    last_pos       BIGINT DEFAULT 0 NOT NULL,
    listeners      INTEGER,
    public         BOOLEAN DEFAULT TRUE,
    max_groups     INTEGER,
    num_groups     INTEGER,
    ctids          JSONB,
    groups_json    JSONB,
    fetched_at     TIMESTAMPTZ DEFAULT now(),
    raw_json       JSONB
);
CREATE INDEX IF NOT EXISTS bcfy_playlists_last_seen_idx  ON bcfy_playlists(last_seen);
CREATE INDEX IF NOT EXISTS bcfy_playlists_listeners_idx  ON bcfy_playlists(listeners);
-- Partial index for sync=TRUE queries (faster than full table scan)
CREATE INDEX IF NOT EXISTS bcfy_playlists_sync_idx ON bcfy_playlists(sync) WHERE sync = TRUE;

COMMENT ON COLUMN bcfy_playlists.last_pos IS 'Unix timestamp from lastPos attribute in Live API response';

CREATE TABLE IF NOT EXISTS bcfy_playlist_poll_log (
    uuid            UUID NOT NULL,
    poll_started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    poll_ended_at   TIMESTAMPTZ,
    success         BOOLEAN DEFAULT FALSE,
    notes           TEXT,
    CONSTRAINT bcfy_playlist_poll_log_pkey PRIMARY KEY (uuid, poll_started_at)
);

-- ============================================================
-- 3) RAW CALL METADATA
-- ============================================================

CREATE TABLE IF NOT EXISTS bcfy_calls_raw (
    call_uid       TEXT PRIMARY KEY,
    group_id       TEXT,
    ts             BIGINT,
    feed_id        INTEGER,
    tg_id          BIGINT,
    tag_id         INTEGER,
    node_id        BIGINT,
    sid            BIGINT,
    site_id        BIGINT,
    freq           DOUBLE PRECISION,
    src            BIGINT,
    url            TEXT,
    started_at     TIMESTAMPTZ,
    ended_at       TIMESTAMPTZ,
    duration_ms    BIGINT,
    size_bytes     BIGINT,
    fetched_at     TIMESTAMPTZ DEFAULT now(),
    raw_json       JSONB,
    processed      BOOLEAN DEFAULT FALSE,
    last_attempt   TIMESTAMPTZ,
    error          TEXT,
    playlist_uuid  UUID,
    s3_key_v2      TEXT,
    CONSTRAINT bcfy_calls_raw_group_ts_uidx UNIQUE (group_id, ts)
);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_feed_idx   ON bcfy_calls_raw(feed_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_tg_idx     ON bcfy_calls_raw(tg_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_tag_idx    ON bcfy_calls_raw(tag_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_start_idx  ON bcfy_calls_raw(started_at);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_node_idx   ON bcfy_calls_raw(node_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_sid_idx    ON bcfy_calls_raw(sid);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_site_idx   ON bcfy_calls_raw(site_id);
-- Indexes for S3 hierarchical storage and playlist tracking
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_playlist_uuid_idx ON bcfy_calls_raw(playlist_uuid) WHERE playlist_uuid IS NOT NULL;
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_playlist_time_idx ON bcfy_calls_raw(playlist_uuid, started_at DESC) WHERE playlist_uuid IS NOT NULL;
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_s3_key_v2_idx ON bcfy_calls_raw(s3_key_v2) WHERE s3_key_v2 IS NOT NULL;
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_pending_transcription_idx ON bcfy_calls_raw(started_at DESC) WHERE processed = TRUE AND s3_key_v2 IS NOT NULL AND error IS NULL;

COMMENT ON TABLE bcfy_calls_raw IS 'Raw call metadata queue from Broadcastify Calls endpoint.';
COMMENT ON COLUMN bcfy_calls_raw.playlist_uuid IS 'Playlist UUID captured at insert time for hierarchical S3 path construction';
COMMENT ON COLUMN bcfy_calls_raw.s3_key_v2 IS 'Hierarchical S3 object key (v2 format with time partitioning)';

-- ============================================================
-- 4) TRANSCRIPTS
-- ============================================================

CREATE TABLE IF NOT EXISTS transcripts (
    id               BIGSERIAL PRIMARY KEY,
    recording_id     BIGINT,
    text             TEXT,
    words            JSONB,
    language         TEXT,
    model_name       TEXT,
    created_at       TIMESTAMPTZ DEFAULT now(),
    tsv              tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(text,''))) STORED,
    duration_seconds NUMERIC NOT NULL,
    confidence       NUMERIC NOT NULL,
    call_uid         TEXT,
    s3_bucket        TEXT,
    s3_key           TEXT,
    s3_key_v2        TEXT,
    CONSTRAINT transcripts_call_uid_key UNIQUE (call_uid)
);
CREATE INDEX IF NOT EXISTS transcripts_lang_model_idx ON transcripts(language, model_name);
CREATE INDEX IF NOT EXISTS transcripts_recording_idx  ON transcripts(recording_id);
CREATE INDEX IF NOT EXISTS transcripts_tsv_idx        ON transcripts USING btree(tsv);
CREATE INDEX IF NOT EXISTS transcripts_call_uid_idx   ON transcripts(call_uid) WHERE call_uid IS NOT NULL;

ALTER TABLE IF EXISTS transcripts
    ADD CONSTRAINT transcripts_call_fk
    FOREIGN KEY (call_uid) REFERENCES bcfy_calls_raw(call_uid)
    ON DELETE SET NULL;

COMMENT ON TABLE transcripts IS 'Text transcriptions of recordings with FTS tsvector.';
COMMENT ON COLUMN transcripts.s3_key_v2 IS 'Hierarchical S3 object key (v2 format) - mirrors bcfy_calls_raw';

-- ============================================================
-- 5) PIPELINE STATE MACHINE
-- ============================================================

CREATE TABLE IF NOT EXISTS processing_state (
    id             BIGSERIAL PRIMARY KEY,
    call_uid       TEXT UNIQUE,
    recording_id   BIGINT,
    status         TEXT NOT NULL,
    last_error     TEXT,
    updated_at     TIMESTAMPTZ DEFAULT now(),
    retry_count    INTEGER DEFAULT 0,
    max_retries    INTEGER DEFAULT 3,
    created_at     TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT processing_state_status_chk
        CHECK (status IN ('queued','downloaded','transcribed','indexed','error'))
);
CREATE INDEX IF NOT EXISTS processing_state_status_idx ON processing_state(status);
CREATE INDEX IF NOT EXISTS processing_state_status_updated_idx ON processing_state(status, updated_at) WHERE status NOT IN ('indexed');

ALTER TABLE IF EXISTS processing_state
    ADD CONSTRAINT processing_state_call_uid_fkey
    FOREIGN KEY (call_uid) REFERENCES bcfy_calls_raw(call_uid)
    ON DELETE SET NULL;

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_processing_state_ts ON processing_state;
CREATE TRIGGER update_processing_state_ts
BEFORE UPDATE ON processing_state
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

COMMENT ON TABLE processing_state IS 'Pipeline state machine tracking for ingestion and NLP stages.';

-- ============================================================
-- SYSTEM MONITORING
-- ============================================================

CREATE TABLE IF NOT EXISTS system_logs (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- Changed from 'timestamp' to match production
    component       TEXT NOT NULL,  -- 'ingestion', 'audio_worker', etc.
    event_type      TEXT NOT NULL,  -- 'api_call', 'cycle_complete', 'error'
    message         TEXT,
    metadata        JSONB,
    duration_ms     INTEGER
);

CREATE INDEX IF NOT EXISTS system_logs_timestamp_idx ON system_logs(created_at DESC);  -- Index on created_at
CREATE INDEX IF NOT EXISTS system_logs_component_idx ON system_logs(component);
CREATE INDEX IF NOT EXISTS system_logs_event_type_idx ON system_logs(event_type);

COMMENT ON TABLE system_logs IS 'System event logs for monitoring and debugging';

-- ============================================================
-- MONITORING SCHEMA, VIEWS, AND FUNCTIONS
-- (Consolidated from migration 001_phase1_improvements.sql)
-- ============================================================

CREATE SCHEMA IF NOT EXISTS monitoring;

-- View 1: Table health overview
CREATE OR REPLACE VIEW monitoring.table_health AS
SELECT
  schemaname,
  relname AS tablename,
  pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
  pg_size_pretty(pg_relation_size(relid)) AS table_size,
  pg_size_pretty(pg_indexes_size(relid)) AS indexes_size,
  n_live_tup AS live_rows,
  n_dead_tup AS dead_rows,
  ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_ratio_pct,
  last_vacuum,
  last_autovacuum,
  last_analyze,
  last_autoanalyze
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- View 2: Index usage statistics
CREATE OR REPLACE VIEW monitoring.index_usage AS
SELECT
  schemaname,
  relname AS tablename,
  indexrelname AS indexname,
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
  relname AS tablename,
  pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
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

-- ============================================================
-- END
-- ============================================================

