-- ============================================================
-- InstaAgent — Complete Supabase PostgreSQL Schema
-- Run this in Supabase SQL Editor at: supabase.com/dashboard
-- ============================================================

-- ── Users Table ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id         BIGINT      UNIQUE,
    email               TEXT        UNIQUE,
    full_name           TEXT        NOT NULL,
    phone               TEXT,
    city                TEXT,
    language            TEXT        DEFAULT 'hi',       -- hi, te, ta, kn, mr, en
    password_hash       TEXT,                           -- bcrypt hash
    instagram_token     TEXT,                           -- OAuth access token (60-day)
    instagram_id        TEXT,                           -- Instagram user ID
    instagram_username  TEXT,
    plan                TEXT        DEFAULT 'free',     -- free, starter, growth, agency
    trial_start         TIMESTAMPTZ,
    trial_end           TIMESTAMPTZ,
    trial_used          BOOLEAN     DEFAULT false,
    is_active           BOOLEAN     DEFAULT true,
    is_admin            BOOLEAN     DEFAULT false,
    default_enhancement BOOLEAN     DEFAULT true,
    has_seen_guidelines BOOLEAN     DEFAULT false,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── Subscriptions Table ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subscriptions (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID        REFERENCES users(id) ON DELETE CASCADE,
    plan                    TEXT        NOT NULL,           -- starter, growth, agency
    status                  TEXT        DEFAULT 'active',   -- active, cancelled, expired, paused
    razorpay_sub_id         TEXT        UNIQUE,
    razorpay_cust_id        TEXT,
    amount_paise            INTEGER     NOT NULL,           -- 59900 = Rs 599
    billing_cycle           TEXT        DEFAULT 'monthly',
    current_period_start    TIMESTAMPTZ,
    current_period_end      TIMESTAMPTZ,
    cancelled_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ── Posts Table ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS posts (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        REFERENCES users(id) ON DELETE CASCADE,
    original_photo_url  TEXT,                           -- Supabase Storage URL
    edited_photo_url    TEXT,                           -- After Remove.bg + Photoroom
    secondary_photo_url TEXT,                           -- For Carousel Duo
    caption_hindi       TEXT,
    caption_english     TEXT,
    hashtags            TEXT[],                         -- ARRAY['#tag1','#tag2']
    product_name        TEXT        NOT NULL,
    product_type        TEXT        DEFAULT 'other',    -- jewellery, clothing, food, handmade
    additional_info     TEXT,
    platform            TEXT        DEFAULT 'instagram',
    status              TEXT        DEFAULT 'processing',
                                                        -- processing|ready|scheduled|posted|failed
    scheduled_at        TIMESTAMPTZ,
    posted_at           TIMESTAMPTZ,
    instagram_post_id   TEXT,
    instagram_permalink TEXT,
    likes_count         INTEGER     DEFAULT 0,
    comments_count      INTEGER     DEFAULT 0,
    reach               INTEGER     DEFAULT 0,
    error_message       TEXT,
    api_cost_paise      INTEGER     DEFAULT 0,
    is_enhanced         BOOLEAN     DEFAULT true,
    is_carousel_duo     BOOLEAN     DEFAULT false,
    approved_at         TIMESTAMPTZ,
    return_feedback     TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast user post lookups
CREATE INDEX IF NOT EXISTS idx_posts_user_id      ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_status       ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_scheduled_at ON posts(scheduled_at) WHERE status = 'scheduled';

-- ── Usage Logs Table ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usage_logs (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        REFERENCES users(id) ON DELETE CASCADE,
    action      TEXT        NOT NULL,   -- post_created, comment_replied, photo_edited
    api_service TEXT,                   -- claude, removebg, photoroom, instagram
    tokens_in   INTEGER     DEFAULT 0,
    tokens_out  INTEGER     DEFAULT 0,
    cost_paise  INTEGER     DEFAULT 0,
    month_year  TEXT        NOT NULL,   -- '2026-03'
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_user_month ON usage_logs(user_id, month_year);

-- ── Comments Table ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS comments (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id                 UUID        REFERENCES posts(id) ON DELETE CASCADE,
    user_id                 UUID        REFERENCES users(id),
    instagram_comment_id    TEXT        UNIQUE,
    commenter_username      TEXT,
    comment_text            TEXT,
    reply_text              TEXT,
    reply_sent              BOOLEAN     DEFAULT false,
    replied_at              TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ── Row Level Security ────────────────────────────────────────────────────────
-- CRITICAL: Every user can ONLY see their own data

ALTER TABLE users         ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts         ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs    ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments      ENABLE ROW LEVEL SECURITY;

-- Users policy
CREATE POLICY users_own_data ON users
    FOR ALL USING (id = auth.uid());

-- Posts policy
CREATE POLICY posts_own_data ON posts
    FOR ALL USING (user_id = auth.uid());

-- Subscriptions policy
CREATE POLICY subscriptions_own_data ON subscriptions
    FOR ALL USING (user_id = auth.uid());

-- Usage logs policy
CREATE POLICY usage_logs_own_data ON usage_logs
    FOR ALL USING (user_id = auth.uid());

-- Comments policy  
CREATE POLICY comments_own_data ON comments
    FOR ALL USING (user_id = auth.uid());

-- ── Supabase Storage Buckets ──────────────────────────────────────────────────
-- Run these manually in Supabase Dashboard > Storage > New Bucket

-- Bucket: post-photos (public CDN for Instagram posting)
-- Settings: Public bucket = true, File size limit = 10MB
-- Allowed MIME types: image/jpeg, image/png, image/webp

-- ── Auto-update updated_at ────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at

-- ── Aggregator Tables ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aggregator_accounts (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        REFERENCES users(id) ON DELETE CASCADE,
    instagram_username  TEXT        NOT NULL,
    account_type        TEXT        NOT NULL DEFAULT 'owned',
    access_token        TEXT,
    last_synced_at      TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, instagram_username)
);

CREATE TABLE IF NOT EXISTS aggregated_posts (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregator_account_id UUID      REFERENCES aggregator_accounts(id) ON DELETE CASCADE,
    user_id             UUID        REFERENCES users(id) ON DELETE CASCADE,
    ig_post_id          TEXT        NOT NULL,
    caption             TEXT,
    media_url           TEXT,
    media_type          TEXT,
    likes               INTEGER     DEFAULT 0,
    comments            INTEGER     DEFAULT 0,
    hashtags            TEXT[],
    posted_at           TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(aggregator_account_id, ig_post_id)
);

ALTER TABLE aggregator_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE aggregated_posts    ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION is_admin()
RETURNS boolean AS $$
    SELECT COALESCE(is_admin, false) FROM users WHERE id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER STABLE;

CREATE POLICY aggregator_accounts_user_policy ON aggregator_accounts
    FOR ALL USING (
        user_id = auth.uid() OR is_admin()
    );

CREATE POLICY aggregated_posts_user_policy ON aggregated_posts
    FOR ALL USING (
        user_id = auth.uid() OR is_admin()
    );

CREATE TRIGGER aggregator_accounts_updated_at
    BEFORE UPDATE ON aggregator_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX IF NOT EXISTS idx_aggregator_user_id ON aggregator_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_aggregated_posts_account_id ON aggregated_posts(aggregator_account_id);
CREATE INDEX IF NOT EXISTS idx_aggregated_posts_user_id ON aggregated_posts(user_id);
