-- migration_aggregator_fixes.sql
-- Run this in your Supabase SQL Editor to add the missing columns for the Aggregator tracking worker

ALTER TABLE aggregator_accounts
    ADD COLUMN IF NOT EXISTS followers_count     INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS following_count     INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS alert_enabled       BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS alert_threshold_er  DECIMAL(5,2) DEFAULT 3.00,
    ADD COLUMN IF NOT EXISTS sync_error          TEXT;

ALTER TABLE aggregated_posts
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS engagement_rate DECIMAL(5,2) DEFAULT 0.00,
    ADD COLUMN IF NOT EXISTS reach INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS saved INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS shares INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS views INTEGER DEFAULT 0;

-- Optional: If they were accidentally added as text previously, you may need to drop and re-add them, 
-- but IF NOT EXISTS safely ignores them if they're correct.
