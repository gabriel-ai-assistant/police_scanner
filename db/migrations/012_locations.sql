-- ============================================================
-- Migration 012: Location Intelligence & Heat Map
-- ============================================================
--
-- Purpose: Extract, geocode, and store location data from transcripts
--          for heat map visualization
--
-- Changes:
--   1. Create locations table for geocoded location mentions
--   2. Create geocode_cache table to avoid re-geocoding
--   3. Add indexes for spatial queries
--
-- Risk: LOW - new tables only, no modifications to existing schema
--
-- Dependencies:
--   - bcfy_playlists table (init.sql)
--   - bcfy_counties table (init.sql)
--   - transcripts table (init.sql)
--
-- ============================================================

BEGIN;

-- ============================================================
-- 1. LOCATIONS TABLE
-- ============================================================
-- Stores extracted and geocoded location mentions from transcripts

CREATE TABLE IF NOT EXISTS locations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source reference (polymorphic - can come from transcript text, keyword match, etc.)
    source_type             VARCHAR(50) NOT NULL,  -- 'transcript', 'keyword_match'
    source_id               TEXT NOT NULL,         -- call_uid for transcript, UUID for keyword_match

    -- Raw extracted text
    raw_location_text       TEXT NOT NULL,
    location_type           VARCHAR(50),  -- 'address', 'street', 'intersection', 'business', 'area', 'landmark'

    -- Geocoded result
    latitude                DECIMAL(10, 8),
    longitude               DECIMAL(11, 8),
    geocode_confidence      DECIMAL(3, 2),  -- 0.00 to 1.00
    geocode_source          VARCHAR(50) DEFAULT 'nominatim',  -- 'nominatim', 'manual', 'county_center'

    -- Normalized address components
    street_name             VARCHAR(255),
    street_number           VARCHAR(50),
    city                    VARCHAR(100),
    state                   VARCHAR(50),
    postal_code             VARCHAR(20),
    country                 VARCHAR(100),
    formatted_address       TEXT,  -- Full formatted address from geocoder

    -- Feed context (for filtering and biasing)
    playlist_uuid           UUID REFERENCES bcfy_playlists(uuid) ON DELETE SET NULL,
    county_id               INTEGER REFERENCES bcfy_counties(cntid) ON DELETE SET NULL,

    -- Processing metadata
    geocoded_at             TIMESTAMPTZ,
    geocode_attempts        INTEGER DEFAULT 0,
    geocode_error           TEXT,

    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate entries for same source and location text
    CONSTRAINT locations_source_text_unique
        UNIQUE(source_type, source_id, raw_location_text)
);

COMMENT ON TABLE locations IS 'Extracted and geocoded location mentions from police scanner transcripts';
COMMENT ON COLUMN locations.source_type IS 'Type of source: transcript, keyword_match';
COMMENT ON COLUMN locations.source_id IS 'ID of source record (call_uid for transcript)';
COMMENT ON COLUMN locations.raw_location_text IS 'Original location text extracted from transcript';
COMMENT ON COLUMN locations.location_type IS 'Type: address, street, intersection, business, area, landmark';
COMMENT ON COLUMN locations.geocode_confidence IS 'Geocoding confidence score 0.00-1.00';
COMMENT ON COLUMN locations.geocode_source IS 'Source of geocode: nominatim, manual, county_center';
COMMENT ON COLUMN locations.playlist_uuid IS 'Associated feed for filtering and context';

-- ============================================================
-- 2. INDEXES FOR LOCATIONS TABLE
-- ============================================================

-- Spatial index for bounding box queries (map viewport)
CREATE INDEX IF NOT EXISTS idx_locations_coords
    ON locations(latitude, longitude)
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Feed filtering (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_locations_playlist
    ON locations(playlist_uuid, created_at DESC)
    WHERE latitude IS NOT NULL;

-- Time-based queries for heatmap
CREATE INDEX IF NOT EXISTS idx_locations_created
    ON locations(created_at DESC)
    WHERE latitude IS NOT NULL;

-- County-based filtering
CREATE INDEX IF NOT EXISTS idx_locations_county
    ON locations(county_id)
    WHERE county_id IS NOT NULL;

-- Source lookup
CREATE INDEX IF NOT EXISTS idx_locations_source
    ON locations(source_type, source_id);

-- Geocoding status (for retry processing)
CREATE INDEX IF NOT EXISTS idx_locations_pending_geocode
    ON locations(created_at ASC)
    WHERE latitude IS NULL AND geocode_attempts < 3;

-- ============================================================
-- 3. GEOCODE CACHE TABLE
-- ============================================================
-- Cache geocoding results to avoid hitting Nominatim for duplicate addresses

CREATE TABLE IF NOT EXISTS geocode_cache (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Cache key (normalized query string)
    query_hash              VARCHAR(64) NOT NULL UNIQUE,  -- SHA256 of normalized query
    query_text              TEXT NOT NULL,                -- Original query for debugging

    -- Context that was used (affects results)
    bias_city               VARCHAR(100),
    bias_state              VARCHAR(50),
    bias_country            VARCHAR(100),

    -- Geocode result
    latitude                DECIMAL(10, 8),
    longitude               DECIMAL(11, 8),
    confidence              DECIMAL(3, 2),
    formatted_address       TEXT,

    -- Address components
    street_name             VARCHAR(255),
    street_number           VARCHAR(50),
    city                    VARCHAR(100),
    state                   VARCHAR(50),
    postal_code             VARCHAR(20),
    country                 VARCHAR(100),

    -- Metadata
    source                  VARCHAR(50) DEFAULT 'nominatim',
    raw_response            JSONB,  -- Full API response for debugging

    -- Cache management
    hit_count               INTEGER DEFAULT 0,
    last_hit_at             TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    expires_at              TIMESTAMPTZ DEFAULT NOW() + INTERVAL '90 days'
);

COMMENT ON TABLE geocode_cache IS 'Cache for Nominatim geocoding results to reduce API calls';
COMMENT ON COLUMN geocode_cache.query_hash IS 'SHA256 hash of normalized query+bias for lookup';
COMMENT ON COLUMN geocode_cache.hit_count IS 'Number of times this cache entry was used';
COMMENT ON COLUMN geocode_cache.expires_at IS 'Cache expiry time (90 days default)';

-- Indexes for geocode cache
CREATE INDEX IF NOT EXISTS idx_geocode_cache_hash
    ON geocode_cache(query_hash);

CREATE INDEX IF NOT EXISTS idx_geocode_cache_expires
    ON geocode_cache(expires_at)
    WHERE expires_at < NOW();

-- ============================================================
-- 4. HELPER FUNCTIONS
-- ============================================================

-- Function to calculate distance between two points (Haversine formula)
CREATE OR REPLACE FUNCTION haversine_distance(
    lat1 DECIMAL, lon1 DECIMAL,
    lat2 DECIMAL, lon2 DECIMAL
) RETURNS DECIMAL AS $$
DECLARE
    R DECIMAL := 6371;  -- Earth's radius in kilometers
    dlat DECIMAL;
    dlon DECIMAL;
    a DECIMAL;
    c DECIMAL;
BEGIN
    dlat := RADIANS(lat2 - lat1);
    dlon := RADIANS(lon2 - lon1);
    a := SIN(dlat/2) * SIN(dlat/2) +
         COS(RADIANS(lat1)) * COS(RADIANS(lat2)) *
         SIN(dlon/2) * SIN(dlon/2);
    c := 2 * ASIN(SQRT(a));
    RETURN R * c;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION haversine_distance IS 'Calculate distance in km between two lat/lon points';

-- ============================================================
-- 5. VIEWS FOR COMMON QUERIES
-- ============================================================

-- View: Locations with playlist/feed context
CREATE OR REPLACE VIEW v_locations_with_context AS
SELECT
    l.id,
    l.source_type,
    l.source_id,
    l.raw_location_text,
    l.location_type,
    l.latitude,
    l.longitude,
    l.geocode_confidence,
    l.formatted_address,
    l.city,
    l.state,
    l.created_at,
    l.playlist_uuid,
    p.name as playlist_name,
    c.county_name,
    c.state_code as county_state,
    t.text as transcript_text,
    t.created_at as transcript_created_at
FROM locations l
LEFT JOIN bcfy_playlists p ON p.uuid = l.playlist_uuid
LEFT JOIN bcfy_counties c ON c.cntid = l.county_id
LEFT JOIN transcripts t ON t.call_uid = l.source_id AND l.source_type = 'transcript'
WHERE l.latitude IS NOT NULL AND l.longitude IS NOT NULL;

COMMENT ON VIEW v_locations_with_context IS 'Locations with feed and transcript context for display';

-- View: Location density for heatmap (aggregated by grid cell)
CREATE OR REPLACE VIEW v_location_heatmap AS
SELECT
    -- Round to ~100m grid cells for aggregation
    ROUND(latitude::NUMERIC, 3) as lat_grid,
    ROUND(longitude::NUMERIC, 3) as lon_grid,
    AVG(latitude) as center_lat,
    AVG(longitude) as center_lon,
    COUNT(*) as location_count,
    MAX(created_at) as most_recent,
    array_agg(DISTINCT playlist_uuid) FILTER (WHERE playlist_uuid IS NOT NULL) as playlist_uuids
FROM locations
WHERE latitude IS NOT NULL AND longitude IS NOT NULL
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY ROUND(latitude::NUMERIC, 3), ROUND(longitude::NUMERIC, 3)
HAVING COUNT(*) > 0
ORDER BY location_count DESC;

COMMENT ON VIEW v_location_heatmap IS 'Aggregated location density for heatmap visualization';

-- ============================================================
-- 6. TRIGGERS
-- ============================================================

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_locations_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_locations_ts ON locations;
CREATE TRIGGER update_locations_ts
    BEFORE UPDATE ON locations
    FOR EACH ROW
    EXECUTE FUNCTION update_locations_timestamp();

-- Trigger to update geocode_cache hit_count
CREATE OR REPLACE FUNCTION update_geocode_cache_hit()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        NEW.last_hit_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMIT;

-- ============================================================
-- Validation queries (run manually after migration)
-- ============================================================
--
-- Check tables were created:
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
-- AND table_name IN ('locations', 'geocode_cache');
--
-- Check indexes:
-- SELECT indexname, tablename FROM pg_indexes
-- WHERE tablename IN ('locations', 'geocode_cache');
--
-- Check views:
-- SELECT table_name FROM information_schema.views
-- WHERE table_schema = 'public'
-- AND table_name LIKE 'v_location%';
--
-- Check function:
-- SELECT haversine_distance(33.0, -97.0, 33.1, -97.1);
--
