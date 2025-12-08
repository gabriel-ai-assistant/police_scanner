-- ============================================================
-- Police Scanner - Full Schema (Active Tables Only, Cleaned)
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
    cntid          INTEGER PRIMARY KEY,
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
    CONSTRAINT bcfy_calls_raw_group_ts_uidx UNIQUE (group_id, ts)
);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_feed_idx   ON bcfy_calls_raw(feed_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_tg_idx     ON bcfy_calls_raw(tg_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_tag_idx    ON bcfy_calls_raw(tag_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_start_idx  ON bcfy_calls_raw(started_at);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_node_idx   ON bcfy_calls_raw(node_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_sid_idx    ON bcfy_calls_raw(sid);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_site_idx   ON bcfy_calls_raw(site_id);

COMMENT ON TABLE bcfy_calls_raw IS 'Raw call metadata queue from Broadcastify Calls endpoint.';

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
    tsv              tsvector DEFAULT to_tsvector('english', coalesce(text,'')),
    duration_seconds NUMERIC NOT NULL,
    confidence       NUMERIC NOT NULL,
    call_uid         TEXT,
    s3_bucket        TEXT,
    s3_key           TEXT,
    CONSTRAINT transcripts_call_uid_key UNIQUE (call_uid)
);
CREATE INDEX IF NOT EXISTS transcripts_lang_model_idx ON transcripts(language, model_name);
CREATE INDEX IF NOT EXISTS transcripts_recording_idx  ON transcripts(recording_id);
CREATE INDEX IF NOT EXISTS transcripts_tsv_idx        ON transcripts USING btree(tsv);

ALTER TABLE IF EXISTS transcripts
    ADD CONSTRAINT transcripts_call_fk
    FOREIGN KEY (call_uid) REFERENCES bcfy_calls_raw(call_uid)
    ON DELETE SET NULL;

COMMENT ON TABLE transcripts IS 'Text transcriptions of recordings with FTS tsvector.';

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
    CONSTRAINT processing_state_status_chk
        CHECK (status IN ('queued','downloaded','transcribed','indexed','error'))
);
CREATE INDEX IF NOT EXISTS processing_state_status_idx ON processing_state(status);

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
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    component       TEXT NOT NULL,  -- 'ingestion', 'audio_worker', etc.
    event_type      TEXT NOT NULL,  -- 'api_call', 'cycle_complete', 'error'
    severity        TEXT NOT NULL DEFAULT 'INFO',
    message         TEXT,
    metadata        JSONB,
    duration_ms     INTEGER
);

CREATE INDEX IF NOT EXISTS system_logs_timestamp_idx ON system_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS system_logs_component_idx ON system_logs(component);
CREATE INDEX IF NOT EXISTS system_logs_event_type_idx ON system_logs(event_type);

-- API call tracking
CREATE TABLE IF NOT EXISTS api_call_metrics (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    endpoint        TEXT NOT NULL,
    method          TEXT DEFAULT 'GET',
    status_code     INTEGER,
    duration_ms     INTEGER,
    response_size   INTEGER,
    cache_hit       BOOLEAN DEFAULT FALSE,
    error           TEXT
);

CREATE INDEX IF NOT EXISTS api_call_metrics_timestamp_idx ON api_call_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS api_call_metrics_endpoint_idx ON api_call_metrics(endpoint);

COMMENT ON TABLE system_logs IS 'System event logs for monitoring and debugging';
COMMENT ON TABLE api_call_metrics IS 'Tracks all Broadcastify API calls for optimization';

-- ============================================================
-- END
-- ============================================================
