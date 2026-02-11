-- ============================================================
-- Migration 010: Transcript Rating System
-- ============================================================
--
-- Purpose: Enable users to rate transcript quality (thumbs up/down)
--
-- Changes:
--   1. Create transcript_ratings table
--   2. Add indexes for efficient queries
--   3. Add updated_at trigger
--
-- Risk: LOW - new table only, no modifications to existing schema
--
-- Dependencies:
--   - users table (migration 007)
--   - transcripts table (init.sql)
--
-- ============================================================

BEGIN;

-- ============================================================
-- 1. TRANSCRIPT RATINGS TABLE
-- ============================================================
-- One rating per user per transcript (toggle behavior)
-- rating: TRUE = thumbs up, FALSE = thumbs down

CREATE TABLE IF NOT EXISTS transcript_ratings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transcript_id   BIGINT NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
    rating          BOOLEAN NOT NULL,  -- TRUE = up, FALSE = down
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT transcript_ratings_unique UNIQUE(user_id, transcript_id)
);

COMMENT ON TABLE transcript_ratings IS 'User ratings for transcript quality';
COMMENT ON COLUMN transcript_ratings.rating IS 'TRUE = thumbs up (good transcript), FALSE = thumbs down (poor transcript)';

-- ============================================================
-- 2. INDEXES
-- ============================================================
-- Optimized for:
-- - Get user's rating for a transcript (composite index)
-- - Aggregate ratings for a transcript
-- - List all ratings by a user

CREATE INDEX IF NOT EXISTS idx_transcript_ratings_user
    ON transcript_ratings(user_id);

CREATE INDEX IF NOT EXISTS idx_transcript_ratings_transcript
    ON transcript_ratings(transcript_id);

-- Composite index for quick lookup (user + transcript)
CREATE INDEX IF NOT EXISTS idx_transcript_ratings_user_transcript
    ON transcript_ratings(user_id, transcript_id);

-- ============================================================
-- 3. UPDATED_AT TRIGGER
-- ============================================================

CREATE OR REPLACE FUNCTION update_transcript_ratings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_transcript_ratings_ts ON transcript_ratings;
CREATE TRIGGER update_transcript_ratings_ts
    BEFORE UPDATE ON transcript_ratings
    FOR EACH ROW
    EXECUTE FUNCTION update_transcript_ratings_timestamp();

COMMIT;
