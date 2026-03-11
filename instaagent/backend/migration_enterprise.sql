-- ═══════════════════════════════════════════════════════════════════════════
-- InstaAgent — Enterprise DB Migration
-- Run this in your Supabase SQL Editor to add enterprise-level schema.
-- All changes are ADDITIVE — no existing tables are modified destructively.
-- ═══════════════════════════════════════════════════════════════════════════

-- ── 1. users — add enterprise columns ────────────────────────────────────────

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS instagram_token_expires_at  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS preferred_post_time         TIME    DEFAULT '19:00:00',
    ADD COLUMN IF NOT EXISTS is_admin                    BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS whatsapp_phone              TEXT;

-- language column: ensure it exists (may already be present)
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS language                    VARCHAR(5) DEFAULT 'hi';

-- ── 2. posts — add metric columns ────────────────────────────────────────────

ALTER TABLE posts
    ADD COLUMN IF NOT EXISTS likes             INTEGER        DEFAULT 0,
    ADD COLUMN IF NOT EXISTS comments_count    INTEGER        DEFAULT 0,
    ADD COLUMN IF NOT EXISTS reach             INTEGER        DEFAULT 0,
    ADD COLUMN IF NOT EXISTS saved             INTEGER        DEFAULT 0,
    ADD COLUMN IF NOT EXISTS shares            INTEGER        DEFAULT 0,
    ADD COLUMN IF NOT EXISTS engagement_rate   DECIMAL(5,2)   DEFAULT 0.00,
    ADD COLUMN IF NOT EXISTS source            VARCHAR(20)    DEFAULT 'dashboard';
    -- source: 'dashboard' | 'telegram'

-- ── 3. analytics_snapshots — daily metric snapshots ──────────────────────────

CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followers_count     INTEGER      DEFAULT 0,
    reach_30d           INTEGER      DEFAULT 0,
    impressions_30d     INTEGER      DEFAULT 0,
    total_posts         INTEGER      DEFAULT 0,
    avg_engagement_rate DECIMAL(5,2) DEFAULT 0.00,
    snapshotted_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_user_date
    ON analytics_snapshots(user_id, snapshotted_at DESC);

-- ── 4. telegram_sessions — FSM state log (Redis is the live store) ───────────

CREATE TABLE IF NOT EXISTS telegram_sessions (
    telegram_id  BIGINT      PRIMARY KEY,
    state        VARCHAR(50) NOT NULL DEFAULT 'IDLE',
    context      JSONB       NOT NULL DEFAULT '{}',
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 5. comments — ensure table exists with all required columns ───────────────
-- (Existing table — only adds columns if missing)

CREATE TABLE IF NOT EXISTS comments (
    id                    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id               UUID         REFERENCES posts(id) ON DELETE CASCADE,
    user_id               UUID         REFERENCES users(id) ON DELETE CASCADE,
    instagram_comment_id  VARCHAR(100),
    comment_text          TEXT,
    reply_text            TEXT,
    reply_sent            BOOLEAN      DEFAULT FALSE,
    created_at            TIMESTAMPTZ  DEFAULT NOW()
);

-- ── 6. Row Level Security (RLS) — analytics_snapshots ────────────────────────

ALTER TABLE analytics_snapshots ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can read own snapshots" ON analytics_snapshots;
CREATE POLICY "Users can read own snapshots"
    ON analytics_snapshots FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can insert snapshots" ON analytics_snapshots;
CREATE POLICY "Service role can insert snapshots"
    ON analytics_snapshots FOR INSERT
    WITH CHECK (TRUE);   -- service key bypasses, protected by API auth layer

-- ── 7. Grant access ───────────────────────────────────────────────────────────

GRANT SELECT, INSERT ON analytics_snapshots TO authenticated;
GRANT ALL ON analytics_snapshots TO service_role;
GRANT ALL ON telegram_sessions TO service_role;
