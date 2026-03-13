-- migration_aggregator_analytics.sql
-- Add metrics and settings columns to aggregator_accounts
ALTER TABLE aggregator_accounts 
ADD COLUMN IF NOT EXISTS followers_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS following_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS alert_enabled BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS alert_threshold_er FLOAT DEFAULT 3.0; -- Default 3% ER threshold

-- B5.1: Backfill for existing rows
UPDATE aggregator_accounts SET alert_enabled = TRUE WHERE alert_enabled IS FALSE;

-- Add engagement_rate to aggregated_posts
ALTER TABLE aggregated_posts 
ADD COLUMN IF NOT EXISTS engagement_rate FLOAT DEFAULT 0.0;

-- Optimized index for top posts sorting
CREATE INDEX IF NOT EXISTS idx_aggregated_posts_er_posted ON aggregated_posts(user_id, engagement_rate DESC, posted_at DESC);

-- Index for frequency analysis
CREATE INDEX IF NOT EXISTS idx_aggregated_posts_posted_at ON aggregated_posts(posted_at);
