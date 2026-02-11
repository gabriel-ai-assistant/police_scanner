-- ============================================================
-- Migration 005: S3 Hierarchical Storage Architecture
-- ============================================================
--
-- Purpose: Enable hierarchical S3 key structure for audio files
--
-- Changes:
--   1. Add playlist_uuid column to bcfy_calls_raw (populated at insert time)
--   2. Add s3_key_v2 column to bcfy_calls_raw (new hierarchical path)
--   3. Add s3_key_v2 column to transcripts (for consistency)
--   4. Create indexes for efficient lookups
--
-- New S3 Key Format:
--   calls/playlist_id={UUID}/year={YYYY}/month={MM}/day={DD}/hour={HH}/call_{call_uid}.wav
--
-- Backward Compatibility:
--   - Existing rows will have NULL playlist_uuid (cannot be recovered)
--   - New rows will have playlist_uuid populated at insert time
--   - Dual-read support for 90 days, then cleanup old flat paths
--
-- ============================================================

BEGIN;

-- ============================================================
-- 1. Add playlist_uuid column to bcfy_calls_raw
-- ============================================================
-- This stores the playlist UUID at insert time, avoiding the need
-- for complex JOINs when constructing S3 paths

ALTER TABLE bcfy_calls_raw
ADD COLUMN IF NOT EXISTS playlist_uuid UUID;

COMMENT ON COLUMN bcfy_calls_raw.playlist_uuid IS
    'Playlist UUID captured at insert time for hierarchical S3 path construction';

-- ============================================================
-- 2. Add s3_key_v2 column to bcfy_calls_raw
-- ============================================================
-- Stores the new hierarchical S3 key path after audio upload
-- Format: calls/playlist_id={UUID}/year={YYYY}/month={MM}/day={DD}/hour={HH}/call_{call_uid}.wav

ALTER TABLE bcfy_calls_raw
ADD COLUMN IF NOT EXISTS s3_key_v2 TEXT;

COMMENT ON COLUMN bcfy_calls_raw.s3_key_v2 IS
    'Hierarchical S3 object key (v2 format with time partitioning)';

-- ============================================================
-- 3. Add s3_key_v2 column to transcripts
-- ============================================================
-- Mirror column for transcript records

ALTER TABLE transcripts
ADD COLUMN IF NOT EXISTS s3_key_v2 TEXT;

COMMENT ON COLUMN transcripts.s3_key_v2 IS
    'Hierarchical S3 object key (v2 format) - mirrors bcfy_calls_raw';

-- ============================================================
-- 4. Create indexes for efficient lookups
-- ============================================================

-- Index for playlist-based queries (e.g., "all calls for playlist X")
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_playlist_uuid_idx
    ON bcfy_calls_raw(playlist_uuid)
    WHERE playlist_uuid IS NOT NULL;

-- Index for S3 key lookups (used by transcription workers)
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_s3_key_v2_idx
    ON bcfy_calls_raw(s3_key_v2)
    WHERE s3_key_v2 IS NOT NULL;

-- Composite index for time-range queries within a playlist
CREATE INDEX IF NOT EXISTS bcfy_calls_raw_playlist_time_idx
    ON bcfy_calls_raw(playlist_uuid, started_at DESC)
    WHERE playlist_uuid IS NOT NULL;

-- ============================================================
-- 5. Validation query (run after migration)
-- ============================================================
-- SELECT
--     COUNT(*) as total_rows,
--     COUNT(playlist_uuid) as rows_with_playlist_uuid,
--     COUNT(s3_key_v2) as rows_with_s3_key_v2
-- FROM bcfy_calls_raw;

COMMIT;

-- ============================================================
-- Rollback (if needed):
-- ============================================================
-- BEGIN;
-- DROP INDEX IF EXISTS bcfy_calls_raw_playlist_time_idx;
-- DROP INDEX IF EXISTS bcfy_calls_raw_s3_key_v2_idx;
-- DROP INDEX IF EXISTS bcfy_calls_raw_playlist_uuid_idx;
-- ALTER TABLE transcripts DROP COLUMN IF EXISTS s3_key_v2;
-- ALTER TABLE bcfy_calls_raw DROP COLUMN IF EXISTS s3_key_v2;
-- ALTER TABLE bcfy_calls_raw DROP COLUMN IF EXISTS playlist_uuid;
-- COMMIT;
