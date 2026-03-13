-- migration_aggregator.sql
-- ─────────────────────────────────────────────────────────────────────────────
-- InstaAgent — Aggregator Feature Migration
-- 1. Add is_admin to users
-- 2. Create aggregator_accounts table
-- 3. Create aggregated_posts table
-- 4. Enable RLS and add policies
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Update Users Table
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT false;

-- Create is_admin() helper for RLS
CREATE OR REPLACE FUNCTION is_admin()
RETURNS boolean AS $$
    SELECT COALESCE(is_admin, false) FROM users WHERE id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- 2. Create Aggregator Accounts Table
CREATE TABLE IF NOT EXISTS aggregator_accounts (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        REFERENCES users(id) ON DELETE CASCADE,
    instagram_username  TEXT        NOT NULL,
    account_type        TEXT        NOT NULL DEFAULT 'owned', -- 'owned' | 'competitor'
    access_token        TEXT,                                 -- for owned accounts
    last_synced_at      TIMESTAMPTZ,
    sync_error          TEXT,                                 -- Error message if sync failed
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, instagram_username)
);

-- 3. Create Aggregated Posts Table
CREATE TABLE IF NOT EXISTS aggregated_posts (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregator_account_id UUID      REFERENCES aggregator_accounts(id) ON DELETE CASCADE,
    user_id             UUID        REFERENCES users(id) ON DELETE CASCADE, -- New: For RLS perf
    ig_post_id          TEXT        NOT NULL,
    caption             TEXT,
    media_url           TEXT,
    media_type          TEXT,       -- 'image' | 'video' | 'carousel'
    likes               INTEGER     DEFAULT 0,
    comments            INTEGER     DEFAULT 0,
    hashtags            TEXT[],
    posted_at           TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(aggregator_account_id, ig_post_id)
);

-- 4. Row Level Security
ALTER TABLE aggregator_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE aggregated_posts    ENABLE ROW LEVEL SECURITY;

-- Policies for aggregator_accounts
CREATE POLICY aggregator_accounts_user_policy ON aggregator_accounts
    FOR ALL USING (
        user_id = auth.uid() OR is_admin()
    );

-- Policies for aggregated_posts
CREATE POLICY aggregated_posts_user_policy ON aggregated_posts
    FOR ALL USING (
        user_id = auth.uid() OR is_admin()
    );

-- Trigger for updated_at
CREATE TRIGGER aggregator_accounts_updated_at
    BEFORE UPDATE ON aggregator_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 5. Helper Functions (RPCs)
CREATE OR REPLACE FUNCTION get_aggregator_user_stats()
RETURNS TABLE (
    id UUID,
    full_name TEXT,
    email TEXT,
    account_count BIGINT,
    post_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id, 
        u.full_name, 
        u.email, 
        COUNT(DISTINCT aa.id) as account_count,
        COUNT(DISTINCT ap.id) as post_count
    FROM users u
    LEFT JOIN aggregator_accounts aa ON aa.user_id = u.id
    LEFT JOIN aggregated_posts ap ON ap.aggregator_account_id = aa.id
    GROUP BY u.id, u.full_name, u.email
    HAVING COUNT(DISTINCT aa.id) > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_trending_hashtags(hashtag_limit INTEGER DEFAULT 10)
RETURNS TABLE (
    tag TEXT,
    count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        unnest(hashtags) as tag,
        COUNT(*) as count
    FROM aggregated_posts
    GROUP BY tag
    ORDER BY count DESC
    LIMIT hashtag_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
