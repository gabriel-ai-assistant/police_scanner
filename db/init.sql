-- ============================================================
-- Broadcastify Common Data Cache Schema
-- ============================================================

-- ============================================================
-- 1. Countries
-- ============================================================
CREATE TABLE bcfy_countries (
    coid          INTEGER PRIMARY KEY,
    country_name  TEXT NOT NULL,
    country_code  TEXT NOT NULL,
    iso_alpha2    TEXT,
    is_active     BOOLEAN DEFAULT TRUE,
    notes         TEXT,
    fetched_at    TIMESTAMPTZ DEFAULT NOW(),
    raw_json      JSONB
);
CREATE INDEX IF NOT EXISTS bcfy_countries_country_code_idx ON bcfy_countries(country_code);

-- ============================================================
-- 2. States
-- ============================================================
CREATE TABLE bcfy_states (
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

-- ============================================================
-- 3. Counties
-- ============================================================
CREATE TABLE bcfy_counties (
    ctid           INTEGER PRIMARY KEY,
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
    fetched_at     TIMESTAMPTZ DEFAULT NOW(),
    raw_json       JSONB
);
CREATE INDEX IF NOT EXISTS bcfy_counties_stid_idx ON bcfy_counties(stid);
CREATE INDEX IF NOT EXISTS bcfy_counties_coid_idx ON bcfy_counties(coid);
CREATE INDEX IF NOT EXISTS bcfy_counties_fips_idx ON bcfy_counties(fips);
CREATE INDEX IF NOT EXISTS bcfy_counties_name_idx ON bcfy_counties(county_name);

-- ============================================================
-- 4. Tags
-- ============================================================
CREATE TABLE bcfy_tags (
    tag_id        INTEGER PRIMARY KEY,
    tag_descr     TEXT NOT NULL,
    allow_listen  BOOLEAN NOT NULL,
    is_active     BOOLEAN DEFAULT TRUE,
    fetched_at    TIMESTAMPTZ DEFAULT NOW(),
    raw_json      JSONB
);
CREATE INDEX IF NOT EXISTS bcfy_tags_descr_idx ON bcfy_tags(tag_descr);

-- App runtime tables
CREATE TABLE IF NOT EXISTS recordings (
  id BIGSERIAL PRIMARY KEY,
  feed_id INT NOT NULL,
  s3_key TEXT NOT NULL,
  duration_seconds INT,
  started_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now(),
  tag_id INT
);

CREATE TABLE IF NOT EXISTS transcripts (
  id BIGSERIAL PRIMARY KEY,
  recording_id BIGINT REFERENCES recordings(id) ON DELETE CASCADE,
  text TEXT,
  words JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_transcripts_fts
  ON transcripts USING gin (to_tsvector('english', text));




-- ============================================================
-- Completed successfully
-- ============================================================
COMMENT ON SCHEMA public IS 'Broadcastify Common Data Cache';
