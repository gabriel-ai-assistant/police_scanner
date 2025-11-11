-- ============================================================
-- Police Scanner - Database Initialization
-- ============================================================
-- Safe re-run: drop in dependency order (optional)
-- DROP TABLE IF EXISTS processing_state, keyword_hits, ratings, call_streets, streets_norm,
--   detected_terms, transcripts, recordings, bcfy_calls_raw,
--   bcfy_feed_tags, bcfy_talkgroups, bcfy_feeds,
--   bcfy_tags, bcfy_counties, bcfy_states, bcfy_countries CASCADE;

-- ============================================================
-- 0. Extensions (optional; uncomment if you want them)
-- ============================================================
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- 1) COMMON CACHE (local copy of Broadcastify "common" endpoints)
-- ============================================================

-- Countries
CREATE TABLE IF NOT EXISTS bcfy_countries (
    coid          INTEGER PRIMARY KEY,
    country_name  TEXT NOT NULL,
    country_code  TEXT NOT NULL,         -- as returned by API (may be non-ISO like UK, EU, SU)
    iso_alpha2    TEXT,                  -- normalized ISO (optional)
    is_active     BOOLEAN DEFAULT TRUE,
    notes         TEXT,
    fetched_at    TIMESTAMPTZ DEFAULT NOW(),
    raw_json      JSONB
);
CREATE INDEX IF NOT EXISTS bcfy_countries_country_code_idx ON bcfy_countries(country_code);

-- States
CREATE TABLE IF NOT EXISTS bcfy_states (
    stid         INTEGER PRIMARY KEY,
    coid         INTEGER NOT NULL REFERENCES bcfy_countries(coid) ON DELETE CASCADE,
    state_name   TEXT NOT NULL,
    state_code   TEXT NOT NULL,
    is_active    BOOLEAN DEFAULT TRUE,
    fetched_at   TIMESTAMPTZ DEFAULT NOW(),
    raw_json     JSONB
);
CREATE INDEX IF NOT EXISTS bcfy_states_coid_idx ON bcfy_states(coid);
CREATE INDEX IF NOT EXISTS bcfy_states_state_code_idx ON bcfy_states(state_code);

-- Counties (list + detail/snapshot)
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
    fips           TEXT,                 -- keep as text (leading zeros)
    timezone_str   TEXT,
    -- denormalized snapshot fields from detail response (convenience)
    state_name     TEXT,
    state_code     TEXT,
    country_name   TEXT,
    country_code   TEXT,
    is_active      BOOLEAN DEFAULT TRUE,
    fetched_at     TIMESTAMPTZ DEFAULT NOW(),
    raw_json       JSONB
);
CREATE INDEX IF NOT EXISTS bcfy_counties_stid_idx ON bcfy_counties(stid);
CREATE INDEX IF NOT EXISTS bcfy_counties_coid_idx ON bcfy_counties(coid);
CREATE INDEX IF NOT EXISTS bcfy_counties_fips_idx ON bcfy_counties(fips);
CREATE INDEX IF NOT EXISTS bcfy_counties_name_idx ON bcfy_counties(county_name);

-- Tags (global reference)
CREATE TABLE IF NOT EXISTS bcfy_tags (
    tag_id        INTEGER PRIMARY KEY,
    tag_descr     TEXT NOT NULL,
    allow_listen  BOOLEAN NOT NULL,
    is_active     BOOLEAN DEFAULT TRUE,
    fetched_at    TIMESTAMPTZ DEFAULT NOW(),
    raw_json      JSONB
);
CREATE INDEX IF NOT EXISTS bcfy_tags_descr_idx ON bcfy_tags(tag_descr);

-- ============================================================
-- 2) INGEST CACHE (feeds, talkgroups, tags map)
-- ============================================================

-- Feeds cache
CREATE TABLE IF NOT EXISTS bcfy_feeds (
    feed_id        INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,
    description    TEXT,
    stid           INTEGER REFERENCES bcfy_states(stid)    ON DELETE SET NULL,
    cntid           INTEGER REFERENCES bcfy_counties(cntid)  ON DELETE SET NULL,
    coid           INTEGER REFERENCES bcfy_countries(coid) ON DELETE SET NULL,
    is_active      BOOLEAN DEFAULT TRUE,
    source_type    TEXT,          -- e.g., 'calls', 'conventional'
    url_web        TEXT,
    fetched_at     TIMESTAMPTZ DEFAULT NOW(),
    raw_json       JSONB
);
CREATE INDEX IF NOT EXISTS bcfy_feeds_stid_idx ON bcfy_feeds(stid);
CREATE INDEX IF NOT EXISTS bcfy_feeds_cntid_idx ON bcfy_feeds(cntid);
CREATE INDEX IF NOT EXISTS bcfy_feeds_coid_idx ON bcfy_feeds(coid);
CREATE INDEX IF NOT EXISTS bcfy_feeds_name_idx ON bcfy_feeds(name);

-- Talkgroups cache (optionally tagged)
CREATE TABLE IF NOT EXISTS bcfy_talkgroups (
    tg_id          BIGINT PRIMARY KEY,                       -- talkgroup id
    system_id      BIGINT,
    alpha_tag      TEXT,
    description    TEXT,
    service_type   TEXT,                                     -- Law, Fire, EMS, etc.
    tag_id         INTEGER REFERENCES bcfy_tags(tag_id) ON DELETE SET NULL,
    stid           INTEGER REFERENCES bcfy_states(stid)    ON DELETE SET NULL,
    cntid           INTEGER REFERENCES bcfy_counties(cntid)  ON DELETE SET NULL,
    coid           INTEGER REFERENCES bcfy_countries(coid) ON DELETE SET NULL,
    is_active      BOOLEAN DEFAULT TRUE,
    fetched_at     TIMESTAMPTZ DEFAULT NOW(),
    raw_json       JSONB
);
CREATE INDEX IF NOT EXISTS bcfy_talkgroups_stid_idx    ON bcfy_talkgroups(stid);
CREATE INDEX IF NOT EXISTS bcfy_talkgroups_cntid_idx    ON bcfy_talkgroups(cntid);
CREATE INDEX IF NOT EXISTS bcfy_talkgroups_coid_idx    ON bcfy_talkgroups(coid);
CREATE INDEX IF NOT EXISTS bcfy_talkgroups_service_idx ON bcfy_talkgroups(service_type);
CREATE INDEX IF NOT EXISTS bcfy_talkgroups_tag_idx     ON bcfy_talkgroups(tag_id);

-- Feed ↔ Tag map
CREATE TABLE IF NOT EXISTS bcfy_feed_tags (
    feed_id        INTEGER NOT NULL REFERENCES bcfy_feeds(feed_id) ON DELETE CASCADE,
    tag_id         INTEGER NOT NULL REFERENCES bcfy_tags(tag_id)   ON DELETE CASCADE,
    fetched_at     TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (feed_id, tag_id)
);
CREATE INDEX IF NOT EXISTS bcfy_feed_tags_feed_idx ON bcfy_feed_tags(feed_id);
CREATE INDEX IF NOT EXISTS bcfy_feed_tags_tag_idx  ON bcfy_feed_tags(tag_id);

-- ============================================================
-- 3) CALLS RAW QUEUE (de-dupe & retries; mirrors Calls payload)
-- ============================================================

CREATE TABLE IF NOT EXISTS bcfy_calls_raw (
    call_uid       TEXT PRIMARY KEY,    -- optional synthetic; keep for convenience
    -- Native identifiers (preferred for uniqueness)
    group_id       TEXT,                -- e.g., '7017-38529' (system-group key)
    ts             BIGINT,              -- epoch seconds for call
    -- Helpful payload fields
    feed_id        INTEGER REFERENCES bcfy_feeds(feed_id)         ON DELETE SET NULL,
    tg_id          BIGINT  REFERENCES bcfy_talkgroups(tg_id)      ON DELETE SET NULL,
    tag_id         INTEGER REFERENCES bcfy_tags(tag_id)           ON DELETE SET NULL,
    node_id        BIGINT,
    sid            BIGINT,
    site_id        BIGINT,
    freq           DOUBLE PRECISION,
    src            BIGINT,
    url            TEXT,                -- source audio URL (temp/presigned)
    started_at     TIMESTAMPTZ,
    ended_at       TIMESTAMPTZ,
    duration_ms    BIGINT,
    size_bytes     BIGINT,
    fetched_at     TIMESTAMPTZ DEFAULT NOW(),
    raw_json       JSONB
);
-- Canonical uniqueness on native IDs to avoid dupes
CREATE UNIQUE INDEX IF NOT EXISTS bcfy_calls_raw_group_ts_uidx ON bcfy_calls_raw (group_id, ts);
-- Helpful search indexes
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_feed_idx  ON bcfy_calls_raw(feed_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_tg_idx    ON bcfy_calls_raw(tg_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_tag_idx   ON bcfy_calls_raw(tag_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_node_idx  ON bcfy_calls_raw(node_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_sid_idx   ON bcfy_calls_raw(sid);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_site_idx  ON bcfy_calls_raw(site_id);
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_start_idx ON bcfy_calls_raw(started_at);

-- ============================================================
-- 4) APP: RECORDINGS & TRANSCRIPTS (Option 2: object-store pointers)
-- ============================================================

-- Object-store pointers for audio files
CREATE TABLE IF NOT EXISTS recordings (
    id                 BIGSERIAL PRIMARY KEY,
    feed_id            INTEGER REFERENCES bcfy_feeds(feed_id)     ON DELETE SET NULL,
    tg_id              BIGINT  REFERENCES bcfy_talkgroups(tg_id)  ON DELETE SET NULL,
    tag_id             INTEGER REFERENCES bcfy_tags(tag_id)       ON DELETE SET NULL,
    call_uid           TEXT UNIQUE,           -- link to bcfy_calls_raw.call_uid if used
    group_id           TEXT,                  -- mirror for convenience (optional)
    ts                 BIGINT,                -- mirror for convenience (optional)
    s3_bucket          TEXT NOT NULL DEFAULT 'feeds',
    s3_key             TEXT NOT NULL,         -- e.g., 'tx/collin/2025/11/10/<epoch>-<group>.mp3'
    format             TEXT DEFAULT 'mp3',
    duration_seconds   INT,
    started_at         TIMESTAMPTZ,
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    meta_json          JSONB
);
CREATE INDEX IF NOT EXISTS recordings_feed_idx     ON recordings(feed_id);
CREATE INDEX IF NOT EXISTS recordings_tg_idx       ON recordings(tg_id);
CREATE INDEX IF NOT EXISTS recordings_tag_idx      ON recordings(tag_id);
CREATE INDEX IF NOT EXISTS recordings_started_idx  ON recordings(started_at);
CREATE INDEX IF NOT EXISTS recordings_group_ts_idx ON recordings(group_id, ts);

-- Transcripts
CREATE TABLE IF NOT EXISTS transcripts (
    id             BIGSERIAL PRIMARY KEY,
    recording_id   BIGINT NOT NULL REFERENCES recordings(id) ON DELETE CASCADE,
    text           TEXT,
    words          JSONB,                 -- optional word/segment timing detail
    language       TEXT,
    model_name     TEXT,                  -- e.g., 'whisper-large-v3'
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    -- Materialized tsvector for fast FTS
    tsv            tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(text,''))) STORED
);
CREATE INDEX IF NOT EXISTS transcripts_tsv_idx       ON transcripts USING GIN (tsv);
CREATE INDEX IF NOT EXISTS transcripts_recording_idx ON transcripts(recording_id);

-- ============================================================
-- 5) APP: NLP/ANALYTICS (terms, streets, ratings, keywords)
-- ============================================================

-- Detected terms (raw extraction from transcripts)
CREATE TABLE IF NOT EXISTS detected_terms (
    recording_id  BIGINT NOT NULL REFERENCES recordings(id) ON DELETE CASCADE,
    term          TEXT NOT NULL,
    hits          INT  NOT NULL,
    is_street     BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (recording_id, term)
);
CREATE INDEX IF NOT EXISTS detected_terms_term_idx   ON detected_terms(term);
CREATE INDEX IF NOT EXISTS detected_terms_street_idx ON detected_terms(is_street);

-- Normalized streets catalog (heat-map ready; lat/lon optional)
CREATE TABLE IF NOT EXISTS streets_norm (
    street_id    BIGSERIAL PRIMARY KEY,
    street_norm  TEXT UNIQUE NOT NULL,     -- e.g., 'Sweetwater Ln'
    city         TEXT,
    state        TEXT,
    lat          NUMERIC(9,6),
    lon          NUMERIC(9,6)
    -- PostGIS geom column can be added later without breaking shape
);
-- CREATE INDEX streets_norm_trgm ON streets_norm USING GIN (street_norm gin_trgm_ops); -- if pg_trgm enabled

-- Link recordings to normalized streets (counts)
CREATE TABLE IF NOT EXISTS call_streets (
    recording_id BIGINT NOT NULL REFERENCES recordings(id) ON DELETE CASCADE,
    street_id    BIGINT NOT NULL REFERENCES streets_norm(street_id) ON DELETE RESTRICT,
    hits         INT NOT NULL DEFAULT 1,
    PRIMARY KEY (recording_id, street_id)
);
CREATE INDEX IF NOT EXISTS call_streets_street_idx ON call_streets(street_id);

-- Ratings (write-back: translation good/bad, extensible categories)
CREATE TABLE IF NOT EXISTS ratings (
    recording_id BIGINT NOT NULL REFERENCES recordings(id) ON DELETE CASCADE,
    category     TEXT   NOT NULL,   -- 'translation','incident','audio', etc.
    label        TEXT   NOT NULL CHECK (label IN ('good','bad')),
    score        NUMERIC(3,2),      -- optional 0.00–1.00
    notes        TEXT,
    rated_by     TEXT,
    rated_at     TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (recording_id, category)
);
CREATE INDEX IF NOT EXISTS ratings_category_idx ON ratings(category, label);

-- Optional: keyword hits (simple alerting/log of matched phrases)
CREATE TABLE IF NOT EXISTS keyword_hits (
    id             BIGSERIAL PRIMARY KEY,
    recording_id   BIGINT NOT NULL REFERENCES recordings(id) ON DELETE CASCADE,
    keyword        TEXT NOT NULL,
    matched_text   TEXT,
    matched_at     TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS keyword_hits_recording_idx ON keyword_hits(recording_id);
CREATE INDEX IF NOT EXISTS keyword_hits_keyword_idx   ON keyword_hits(keyword);

-- ============================================================
-- 6) APP: PIPELINE STATE (idempotency & retries)
-- ============================================================

CREATE TABLE IF NOT EXISTS processing_state (
    id             BIGSERIAL PRIMARY KEY,
    call_uid       TEXT UNIQUE,  -- tracks per-call processing when used
    recording_id   BIGINT REFERENCES recordings(id) ON DELETE SET NULL,
    status         TEXT NOT NULL,
    last_error     TEXT,
    updated_at     TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT processing_state_status_chk
        CHECK (status IN ('queued','downloaded','transcribed','indexed','error'))
);
CREATE INDEX IF NOT EXISTS processing_state_status_idx ON processing_state(status);

-- Optional: keep updated_at fresh
-- CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
-- BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql;
-- CREATE TRIGGER trg_processing_state_updated BEFORE UPDATE ON processing_state
-- FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- COMMENTS
-- ============================================================
COMMENT ON TABLE bcfy_calls_raw  IS 'Raw call metadata cache/queue from Broadcastify Calls endpoint (unique on group_id+ts).';
COMMENT ON TABLE recordings      IS 'Object-storage pointers (Option 2) for audio, with feed/tg/tag context and group_id+ts mirrors.';
COMMENT ON TABLE transcripts     IS 'Transcribed text and optional word-level timing; includes FTS tsvector.';
COMMENT ON TABLE detected_terms  IS 'Per-recording extracted tokens; mark streets via is_street for heat maps.';
COMMENT ON TABLE call_streets    IS 'Recording-to-normalized-street linkage with hit counts.';
COMMENT ON TABLE ratings         IS 'Write-back adjudications, e.g., translation good/bad.';
COMMENT ON TABLE keyword_hits    IS 'Simple keyword match log for alerting/analytics.';
COMMENT ON TABLE processing_state IS 'Pipeline status for idempotent processing and retries.';

-- ============================================================
-- END
-- ============================================================
