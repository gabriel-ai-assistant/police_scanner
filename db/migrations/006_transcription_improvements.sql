-- ============================================================
-- Migration 006: Transcription Pipeline Improvements
-- ============================================================
--
-- Purpose: Prepare transcripts table for refactored transcription worker
-- that uses OpenAI Whisper API
--
-- Changes:
--   1. Add default values for duration_seconds and confidence
--   2. Add index for pending transcription query
--   3. Fix tsv index (GIN instead of BTREE for full-text search)
--   4. Add retry tracking columns to processing_state
--
-- ============================================================

BEGIN;

-- ============================================================
-- 1. Handle NOT NULL constraints with defaults
-- ============================================================
-- For existing rows without values, set reasonable defaults
-- This prevents INSERT failures from the new worker

UPDATE transcripts
SET duration_seconds = 0
WHERE duration_seconds IS NULL;

UPDATE transcripts
SET confidence = 0
WHERE confidence IS NULL;

-- Add default values for future inserts (in case worker fails to provide)
ALTER TABLE transcripts
    ALTER COLUMN duration_seconds SET DEFAULT 0;

ALTER TABLE transcripts
    ALTER COLUMN confidence SET DEFAULT 0;

-- ============================================================
-- 2. Add index for pending transcription query
-- ============================================================
-- This dramatically speeds up the dispatcher query that finds
-- calls needing transcription

CREATE INDEX IF NOT EXISTS bcfy_calls_raw_pending_transcription_idx
    ON bcfy_calls_raw(started_at DESC)
    WHERE processed = TRUE
      AND s3_key_v2 IS NOT NULL
      AND error IS NULL;

COMMENT ON INDEX bcfy_calls_raw_pending_transcription_idx IS
    'Optimizes dispatcher query for finding calls pending transcription';

-- ============================================================
-- 3. Fix tsv index - GIN is correct for tsvector, not BTREE
-- ============================================================

DROP INDEX IF EXISTS transcripts_tsv_idx;
CREATE INDEX IF NOT EXISTS transcripts_tsv_gin_idx
    ON transcripts USING GIN(tsv);

COMMENT ON INDEX transcripts_tsv_gin_idx IS
    'GIN index for full-text search on transcript text';

-- ============================================================
-- 4. Add call_uid index for transcript lookups (if not exists)
-- ============================================================

CREATE INDEX IF NOT EXISTS transcripts_call_uid_idx
    ON transcripts(call_uid)
    WHERE call_uid IS NOT NULL;

-- ============================================================
-- 5. Add retry tracking to processing_state
-- ============================================================

ALTER TABLE processing_state
    ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;

ALTER TABLE processing_state
    ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 3;

ALTER TABLE processing_state
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- ============================================================
-- 6. Add index on processing_state for stuck item queries
-- ============================================================

CREATE INDEX IF NOT EXISTS processing_state_status_updated_idx
    ON processing_state(status, updated_at)
    WHERE status NOT IN ('indexed');

COMMIT;

-- ============================================================
-- Validation queries (run manually after migration)
-- ============================================================
--
-- Check transcripts table:
-- SELECT
--     COUNT(*) as total_transcripts,
--     COUNT(*) FILTER (WHERE call_uid IS NOT NULL) as with_call_uid,
--     COUNT(*) FILTER (WHERE duration_seconds > 0) as with_duration,
--     AVG(confidence) as avg_confidence
-- FROM transcripts;
--
-- Check pending calls:
-- SELECT COUNT(*) FROM bcfy_calls_raw c
-- LEFT JOIN transcripts t ON c.call_uid = t.call_uid
-- WHERE c.processed = TRUE AND c.s3_key_v2 IS NOT NULL AND t.id IS NULL;
