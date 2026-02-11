-- ============================================================
-- Migration 007: User Authentication
-- ============================================================
--
-- Purpose: Add user authentication tables for Firebase Auth integration
--
-- Changes:
--   1. Create users table linked to Firebase UID
--   2. Create auth_audit_log table for security events
--   3. Add trigger for users updated_at
--
-- Risk: LOW - new tables only, no modifications to existing schema
--
-- ============================================================

BEGIN;

-- ============================================================
-- 1. USERS TABLE
-- ============================================================
-- Links to Firebase Auth UID, stores local user data and roles

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid    TEXT NOT NULL UNIQUE,           -- Firebase Auth UID
    email           TEXT NOT NULL UNIQUE,
    email_verified  BOOLEAN DEFAULT FALSE,
    display_name    TEXT,
    avatar_url      TEXT,
    role            TEXT NOT NULL DEFAULT 'user',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ,
    CONSTRAINT users_role_chk CHECK (role IN ('user', 'admin'))
);

CREATE INDEX IF NOT EXISTS users_firebase_uid_idx ON users(firebase_uid);
CREATE INDEX IF NOT EXISTS users_email_idx ON users(email);
CREATE INDEX IF NOT EXISTS users_role_idx ON users(role);
CREATE INDEX IF NOT EXISTS users_active_idx ON users(is_active) WHERE is_active = TRUE;

COMMENT ON TABLE users IS 'User accounts linked to Firebase Auth';
COMMENT ON COLUMN users.firebase_uid IS 'Firebase Authentication UID (unique identifier from Firebase)';
COMMENT ON COLUMN users.role IS 'User role: user (default) or admin';

-- ============================================================
-- 2. USERS UPDATED_AT TRIGGER
-- ============================================================
-- Reuse existing update_timestamp function if available

CREATE OR REPLACE FUNCTION update_users_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_users_ts ON users;
CREATE TRIGGER update_users_ts
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_users_timestamp();

-- ============================================================
-- 3. AUTH AUDIT LOG
-- ============================================================
-- Track authentication events for security monitoring

CREATE TABLE IF NOT EXISTS auth_audit_log (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    event_type      TEXT NOT NULL,      -- 'login', 'logout', 'role_change', 'registration'
    ip_address      INET,
    user_agent      TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS auth_audit_log_user_id_idx ON auth_audit_log(user_id);
CREATE INDEX IF NOT EXISTS auth_audit_log_created_at_idx ON auth_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS auth_audit_log_event_type_idx ON auth_audit_log(event_type);

COMMENT ON TABLE auth_audit_log IS 'Authentication audit trail for security monitoring';
COMMENT ON COLUMN auth_audit_log.event_type IS 'Event types: login, logout, role_change, registration';

COMMIT;

-- ============================================================
-- Validation queries (run manually after migration)
-- ============================================================
--
-- Check tables were created:
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public' AND table_name IN ('users', 'auth_audit_log');
--
-- Check indexes:
-- SELECT indexname FROM pg_indexes WHERE tablename = 'users';
--
-- Check trigger:
-- SELECT tgname FROM pg_trigger WHERE tgrelid = 'users'::regclass;
--
