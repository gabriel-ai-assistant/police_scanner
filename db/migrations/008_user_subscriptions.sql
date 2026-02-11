-- ============================================================
-- Migration 008: User Playlist Subscriptions
-- ============================================================
--
-- Purpose: Enable users to subscribe to Broadcastify playlists/feeds
--          for personalized notification filtering
--
-- Changes:
--   1. Create user_subscriptions table (users → playlists M:N)
--   2. Add indexes for common query patterns
--   3. Add trigger for updated_at timestamp
--
-- Risk: LOW - new table only, no modifications to existing schema
--
-- Dependencies:
--   - users table (migration 007)
--   - bcfy_playlists table (init.sql)
--
-- ============================================================

BEGIN;

-- ============================================================
-- 1. USER SUBSCRIPTIONS TABLE
-- ============================================================
-- Links users to playlists they want to follow
-- One user can subscribe to many playlists
-- One playlist can have many subscribers

CREATE TABLE IF NOT EXISTS user_subscriptions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    playlist_uuid         UUID NOT NULL REFERENCES bcfy_playlists(uuid) ON DELETE CASCADE,
    notifications_enabled BOOLEAN DEFAULT TRUE,
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT user_subscriptions_unique UNIQUE(user_id, playlist_uuid)
);

COMMENT ON TABLE user_subscriptions IS 'User subscriptions to Broadcastify playlists/feeds';
COMMENT ON COLUMN user_subscriptions.user_id IS 'FK to users table';
COMMENT ON COLUMN user_subscriptions.playlist_uuid IS 'FK to bcfy_playlists table';
COMMENT ON COLUMN user_subscriptions.notifications_enabled IS 'Global mute toggle - false disables all notifications for this subscription';

-- ============================================================
-- 2. INDEXES
-- ============================================================
-- Optimized for common query patterns:
-- - List all subscriptions for a user
-- - Find all subscribers for a playlist (Phase 5)
-- - Find active subscribers for notification delivery

CREATE INDEX IF NOT EXISTS idx_user_subs_user
    ON user_subscriptions(user_id);

CREATE INDEX IF NOT EXISTS idx_user_subs_playlist
    ON user_subscriptions(playlist_uuid);

-- Partial index for active notifications (Phase 5 optimization)
CREATE INDEX IF NOT EXISTS idx_user_subs_active
    ON user_subscriptions(playlist_uuid)
    WHERE notifications_enabled = TRUE;

-- ============================================================
-- 3. UPDATED_AT TRIGGER
-- ============================================================
-- Automatically update updated_at timestamp on row modification

CREATE OR REPLACE FUNCTION update_user_subscriptions_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_user_subscriptions_ts ON user_subscriptions;
CREATE TRIGGER update_user_subscriptions_ts
    BEFORE UPDATE ON user_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_user_subscriptions_timestamp();

COMMIT;

-- ============================================================
-- Validation queries (run manually after migration)
-- ============================================================
--
-- Check table was created:
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public' AND table_name = 'user_subscriptions';
--
-- Check columns:
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'user_subscriptions'
-- ORDER BY ordinal_position;
--
-- Check indexes:
-- SELECT indexname FROM pg_indexes WHERE tablename = 'user_subscriptions';
--
-- Check foreign keys:
-- SELECT conname, conrelid::regclass, confrelid::regclass
-- FROM pg_constraint
-- WHERE conrelid = 'user_subscriptions'::regclass AND contype = 'f';
--
-- Check trigger:
-- SELECT tgname FROM pg_trigger WHERE tgrelid = 'user_subscriptions'::regclass;
--
