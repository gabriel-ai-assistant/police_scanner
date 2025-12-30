-- ============================================================
-- Migration 009: Keyword Groups & Subscription Linking
-- ============================================================
--
-- Purpose: Enable users to create reusable keyword groups for
--          notification filtering and link them to subscriptions
--
-- Changes:
--   1. Create keyword_groups table (user-owned collections)
--   2. Create keywords table (individual terms in groups)
--   3. Create subscription_keyword_groups join table
--   4. Seed template keyword groups (system-owned)
--   5. Add indexes and triggers
--
-- Risk: LOW - new tables only, no modifications to existing schema
--
-- Dependencies:
--   - users table (migration 007)
--   - user_subscriptions table (migration 008)
--
-- ============================================================

BEGIN;

-- ============================================================
-- 1. KEYWORD GROUPS TABLE
-- ============================================================
-- Named, reusable collections of keywords owned by users
-- user_id = NULL indicates system template (clonable)

CREATE TABLE IF NOT EXISTS keyword_groups (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,  -- NULL for system templates
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    is_template BOOLEAN DEFAULT FALSE,  -- TRUE for system templates
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Unique name per user (NULL user_id for templates needs separate handling)
CREATE UNIQUE INDEX IF NOT EXISTS idx_kg_user_name
    ON keyword_groups(user_id, name)
    WHERE user_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_kg_template_name
    ON keyword_groups(name)
    WHERE user_id IS NULL AND is_template = TRUE;

CREATE INDEX IF NOT EXISTS idx_kg_user
    ON keyword_groups(user_id)
    WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_kg_templates
    ON keyword_groups(is_template)
    WHERE is_template = TRUE;

CREATE INDEX IF NOT EXISTS idx_kg_active
    ON keyword_groups(user_id)
    WHERE is_active = TRUE;

COMMENT ON TABLE keyword_groups IS 'User-defined keyword groups for notification filtering';
COMMENT ON COLUMN keyword_groups.user_id IS 'FK to users table, NULL for system templates';
COMMENT ON COLUMN keyword_groups.is_template IS 'TRUE for system templates that users can clone';
COMMENT ON COLUMN keyword_groups.is_active IS 'Soft delete / disable toggle';

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_keyword_groups_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_keyword_groups_ts ON keyword_groups;
CREATE TRIGGER update_keyword_groups_ts
    BEFORE UPDATE ON keyword_groups
    FOR EACH ROW
    EXECUTE FUNCTION update_keyword_groups_timestamp();

-- ============================================================
-- 2. KEYWORDS TABLE
-- ============================================================
-- Individual keywords/phrases within a group

CREATE TABLE IF NOT EXISTS keywords (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword_group_id UUID NOT NULL REFERENCES keyword_groups(id) ON DELETE CASCADE,
    keyword          TEXT NOT NULL,
    match_type       VARCHAR(20) NOT NULL DEFAULT 'substring',
    is_active        BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT keywords_match_type_chk
        CHECK (match_type IN ('exact', 'substring', 'fuzzy', 'regex', 'phrase'))
);

-- Unique keyword + match_type per group
CREATE UNIQUE INDEX IF NOT EXISTS idx_kw_group_keyword_type
    ON keywords(keyword_group_id, keyword, match_type);

CREATE INDEX IF NOT EXISTS idx_kw_group
    ON keywords(keyword_group_id);

-- Partial index for active keywords (Phase 5 optimization)
CREATE INDEX IF NOT EXISTS idx_kw_active
    ON keywords(keyword_group_id)
    WHERE is_active = TRUE;

COMMENT ON TABLE keywords IS 'Individual keywords within keyword groups';
COMMENT ON COLUMN keywords.keyword IS 'The search term/phrase';
COMMENT ON COLUMN keywords.match_type IS 'Matching strategy: exact, substring, fuzzy, regex, phrase';
COMMENT ON COLUMN keywords.is_active IS 'Toggle to temporarily disable without deleting';

-- ============================================================
-- 3. SUBSCRIPTION KEYWORD GROUPS (JOIN TABLE)
-- ============================================================
-- Links keyword groups to specific user subscriptions
-- Many-to-many: one subscription can use many groups,
--               one group can be used by many subscriptions

CREATE TABLE IF NOT EXISTS subscription_keyword_groups (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id  UUID NOT NULL REFERENCES user_subscriptions(id) ON DELETE CASCADE,
    keyword_group_id UUID NOT NULL REFERENCES keyword_groups(id) ON DELETE CASCADE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT skg_unique UNIQUE(subscription_id, keyword_group_id)
);

CREATE INDEX IF NOT EXISTS idx_skg_sub
    ON subscription_keyword_groups(subscription_id);

CREATE INDEX IF NOT EXISTS idx_skg_group
    ON subscription_keyword_groups(keyword_group_id);

COMMENT ON TABLE subscription_keyword_groups IS 'Links keyword groups to specific user subscriptions';

-- ============================================================
-- 4. SEED TEMPLATE KEYWORD GROUPS
-- ============================================================
-- Pre-populated templates that users can clone

-- Template 1: Emergency Codes
INSERT INTO keyword_groups (id, user_id, name, description, is_template, is_active)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    NULL,
    'Emergency Codes',
    'Common police radio codes indicating emergencies',
    TRUE,
    TRUE
) ON CONFLICT DO NOTHING;

INSERT INTO keywords (keyword_group_id, keyword, match_type) VALUES
    ('a0000000-0000-0000-0000-000000000001', '10-33', 'exact'),
    ('a0000000-0000-0000-0000-000000000001', '10-0', 'exact'),
    ('a0000000-0000-0000-0000-000000000001', '10-99', 'exact'),
    ('a0000000-0000-0000-0000-000000000001', 'Signal 100', 'phrase'),
    ('a0000000-0000-0000-0000-000000000001', 'Code 3', 'phrase'),
    ('a0000000-0000-0000-0000-000000000001', 'Priority 1', 'phrase'),
    ('a0000000-0000-0000-0000-000000000001', 'shots fired', 'substring'),
    ('a0000000-0000-0000-0000-000000000001', 'officer needs assistance', 'substring'),
    ('a0000000-0000-0000-0000-000000000001', 'officer down', 'substring')
ON CONFLICT DO NOTHING;

-- Template 2: Common Alert Keywords
INSERT INTO keyword_groups (id, user_id, name, description, is_template, is_active)
VALUES (
    'a0000000-0000-0000-0000-000000000002',
    NULL,
    'Common Alerts',
    'Frequently used alert keywords for critical incidents',
    TRUE,
    TRUE
) ON CONFLICT DO NOTHING;

INSERT INTO keywords (keyword_group_id, keyword, match_type) VALUES
    ('a0000000-0000-0000-0000-000000000002', 'structure fire', 'substring'),
    ('a0000000-0000-0000-0000-000000000002', 'vehicle pursuit', 'substring'),
    ('a0000000-0000-0000-0000-000000000002', 'armed robbery', 'substring'),
    ('a0000000-0000-0000-0000-000000000002', 'domestic violence', 'substring'),
    ('a0000000-0000-0000-0000-000000000002', 'medical emergency', 'substring'),
    ('a0000000-0000-0000-0000-000000000002', 'traffic collision', 'substring'),
    ('a0000000-0000-0000-0000-000000000002', 'hit and run', 'substring'),
    ('a0000000-0000-0000-0000-000000000002', 'active shooter', 'substring')
ON CONFLICT DO NOTHING;

-- Template 3: Suspicious Activity
INSERT INTO keyword_groups (id, user_id, name, description, is_template, is_active)
VALUES (
    'a0000000-0000-0000-0000-000000000003',
    NULL,
    'Suspicious Activity',
    'Keywords related to suspicious persons or activity',
    TRUE,
    TRUE
) ON CONFLICT DO NOTHING;

INSERT INTO keywords (keyword_group_id, keyword, match_type) VALUES
    ('a0000000-0000-0000-0000-000000000003', 'suspicious person', 'substring'),
    ('a0000000-0000-0000-0000-000000000003', 'suspicious vehicle', 'substring'),
    ('a0000000-0000-0000-0000-000000000003', 'trespassing', 'substring'),
    ('a0000000-0000-0000-0000-000000000003', 'prowler', 'substring'),
    ('a0000000-0000-0000-0000-000000000003', 'breaking and entering', 'substring'),
    ('a0000000-0000-0000-0000-000000000003', 'burglary in progress', 'substring'),
    ('a0000000-0000-0000-0000-000000000003', 'break in', 'substring')
ON CONFLICT DO NOTHING;

COMMIT;

-- ============================================================
-- Validation queries (run manually after migration)
-- ============================================================
--
-- Check tables were created:
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
-- AND table_name IN ('keyword_groups', 'keywords', 'subscription_keyword_groups');
--
-- Check keyword_groups columns:
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'keyword_groups'
-- ORDER BY ordinal_position;
--
-- Check template groups were seeded:
-- SELECT id, name, is_template FROM keyword_groups WHERE is_template = TRUE;
--
-- Check keywords in templates:
-- SELECT kg.name, k.keyword, k.match_type
-- FROM keyword_groups kg
-- JOIN keywords k ON k.keyword_group_id = kg.id
-- WHERE kg.is_template = TRUE
-- ORDER BY kg.name, k.keyword;
--
-- Check indexes:
-- SELECT indexname FROM pg_indexes
-- WHERE tablename IN ('keyword_groups', 'keywords', 'subscription_keyword_groups');
--
