# backend/app/services/analytics_service.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Enterprise Analytics Service
# Aggregates post performance, account metrics, generates Telegram-friendly
# formatted summaries and weekly/monthly reports.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from app.db.supabase import get_supabase
from app.utils.crypto import decrypt_token

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard Stats
# ═══════════════════════════════════════════════════════════════════════════════

async def get_user_dashboard_stats(user_id: str) -> dict[str, Any]:
    """
    Aggregate stats across all of a user's posts.
    Returns: total_posts, total_likes, total_comments, total_reach,
             total_saved, total_shares, avg_engagement_rate, top_posts
    """
    supabase = get_supabase()

    posts_result = (
        supabase.table("posts")
        .select(
            "id, product_name, status, likes_count, comments_count, reach, "
            "shares, engagement_rate, instagram_permalink, posted_at"
        )
        .eq("user_id", user_id)
        .eq("status", "posted")
        .order("posted_at", desc=True)
        .execute()
    )
    posts = posts_result.data or []

    if not posts:
        return {
            "total_posts":        0,
            "total_likes":        0,
            "total_comments":     0,
            "total_reach":        0,
            "total_saved":        0,
            "total_shares":       0,
            "avg_engagement_rate": 0.0,
            "top_posts":          [],
        }

    total_likes       = sum(p.get("likes_count", 0) or 0 for p in posts)
    total_comments    = sum(p.get("comments_count", 0) or 0 for p in posts)
    total_reach       = sum(p.get("reach", 0) or 0 for p in posts)
    total_saved       = 0  # column does not exist in DB yet
    total_shares      = sum(p.get("shares", 0) or 0 for p in posts)
    
    # Authenticity Metrics
    total_returns     = sum(1 for p in posts if p.get("return_feedback"))
    enhanced_posts    = [p for p in posts if p.get("is_enhanced")]
    original_posts    = [p for p in posts if not p.get("is_enhanced")]
    
    eng_rates         = [p.get("engagement_rate", 0) or 0 for p in posts]
    avg_eng           = round(sum(eng_rates) / len(eng_rates), 2) if eng_rates else 0.0

    # Top 3 posts by engagement rate
    top_posts = sorted(
        posts,
        key=lambda p: p.get("engagement_rate", 0) or 0,
        reverse=True,
    )[:3]

    return {
        "total_posts":        len(posts),
        "total_likes":        total_likes,
        "total_comments":     total_comments,
        "total_reach":        total_reach,
        "total_saved":        total_saved,
        "total_shares":       total_shares,
        "avg_engagement_rate": avg_eng,
        "total_returns":      total_returns,
        "return_rate":        round((total_returns / len(posts)) * 100, 2) if posts else 0.0,
        "top_posts":          top_posts,
        "authenticity_score": {
            "enhanced": {
                "count": len(enhanced_posts),
                "avg_eng": round(sum(p.get("engagement_rate", 0) or 0 for p in enhanced_posts) / len(enhanced_posts), 2) if enhanced_posts else 0.0,
                "return_rate": round(sum(1 for p in enhanced_posts if p.get("return_feedback")) / len(enhanced_posts) * 100, 2) if enhanced_posts else 0.0
            },
            "original": {
                "count": len(original_posts),
                "avg_eng": round(sum(p.get("engagement_rate", 0) or 0 for p in original_posts) / len(original_posts), 2) if original_posts else 0.0,
                "return_rate": round(sum(1 for p in original_posts if p.get("return_feedback")) / len(original_posts) * 100, 2) if original_posts else 0.0
            }
        }
    }


async def get_post_stats_for_telegram(post_id: str) -> str:
    """
    Return a Telegram-formatted stats message for a specific post.
    Fetches live from Meta Graph API if insights are stale.
    """
    supabase = get_supabase()
    result = (
        supabase.table("posts")
        .select("*, users(instagram_token, language)")
        .eq("id", post_id)
        .single()
        .execute()
    )
    if not result.data:
        return "❌ Post not found."

    post = result.data
    user = post.get("users", {})

    # Attempt live fetch from Graph API if the post is live
    if post.get("instagram_post_id") and user.get("instagram_token"):
        try:
            from app.services.instagram_service import get_post_insights
            insights = await get_post_insights(
                post["instagram_post_id"],
                decrypt_token(user["instagram_token"]),
            )
            # Persist refreshed metrics
            supabase.table("posts").update({
                "likes_count":     insights.get("likes", 0),
                "comments_count":  insights.get("comments", 0),
                "reach":           insights.get("reach", 0),
                "saved":           insights.get("saved", 0),
                "shares":          insights.get("shares", 0),
                "engagement_rate": insights.get("engagement_rate", 0.0),
            }).eq("id", post_id).execute()
            post.update(insights)
        except Exception as e:
            logger.warning("Live insights fetch failed for post %s: %s", post_id, e)

    lang = user.get("language", "hi")
    name = post.get("product_name", "Post")
    link = post.get("instagram_permalink", "")

    if lang == "hi":
        return (
            f"📊 *{name} — Stats*\n\n"
            f"❤️ Likes: `{post.get('likes_count', 0)}`\n"
            f"💬 Comments: `{post.get('comments_count', 0)}`\n"
            f"👁️ Reach: `{post.get('reach', 0)}`\n"
            f"🔖 Saved: `{post.get('saved', 0)}`\n"
            f"📤 Shares: `{post.get('shares', 0)}`\n"
            f"📈 Engagement: `{post.get('engagement_rate', 0.0)}%`\n"
            + (f"\n🔗 [Instagram पर देखें]({link})" if link else "")
        )
    return (
        f"📊 *{name} — Stats*\n\n"
        f"❤️ Likes: `{post.get('likes_count', 0)}`\n"
        f"💬 Comments: `{post.get('comments_count', 0)}`\n"
        f"👁️ Reach: `{post.get('reach', 0)}`\n"
        f"🔖 Saved: `{post.get('saved', 0)}`\n"
        f"📤 Shares: `{post.get('shares', 0)}`\n"
        f"📈 Engagement: `{post.get('engagement_rate', 0.0)}%`\n"
        + (f"\n🔗 [View on Instagram]({link})" if link else "")
    )


async def get_dashboard_stats_for_telegram(user: dict) -> str:
    """Return a Telegram-formatted dashboard stats message for a user."""
    stats = await get_user_dashboard_stats(user["id"])
    lang  = user.get("language", "hi")

    if stats["total_posts"] == 0:
        return (
            "📭 अभी तक कोई post नहीं किया।\n\nPhoto भेजकर शुरू करें! 🚀"
            if lang == "hi" else
            "📭 No posts yet.\n\nSend a photo to get started! 🚀"
        )

    header = "📊 *Your Instagram Analytics*" if lang == "en" else "📊 *आपकी Instagram Analytics*"

    top_lines = []
    for i, p in enumerate(stats["top_posts"], 1):
        name = p.get("product_name", "Post")
        eng  = p.get("engagement_rate", 0)
        top_lines.append(f"  {i}. *{name}* — `{eng}%` engagement")

    top_section = "\n".join(top_lines) if top_lines else "  —"

    if lang == "hi":
        return (
            f"{header}\n\n"
            f"📸 Total posts: `{stats['total_posts']}`\n"
            f"❤️ Total likes: `{stats['total_likes']}`\n"
            f"💬 Total comments: `{stats['total_comments']}`\n"
            f"👁️ Total reach: `{stats['total_reach']}`\n"
            f"🔖 Total saved: `{stats['total_saved']}`\n"
            f"📈 Avg engagement: `{stats['avg_engagement_rate']}%`\n\n"
            f"🏆 *Top Posts:*\n{top_section}"
        )
    return (
        f"{header}\n\n"
        f"📸 Total posts: `{stats['total_posts']}`\n"
        f"❤️ Total likes: `{stats['total_likes']}`\n"
        f"💬 Comments: `{stats['total_comments']}`\n"
        f"👁️ Reach: `{stats['total_reach']}`\n"
        f"🔖 Saved: `{stats['total_saved']}`\n"
        f"📈 Avg engagement: `{stats['avg_engagement_rate']}%`\n\n"
        f"🏆 *Top Posts:*\n{top_section}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Weekly / Monthly Report
# ═══════════════════════════════════════════════════════════════════════════════

async def get_weekly_report(user: dict) -> str:
    """Generate a weekly performance summary for the user."""
    supabase = get_supabase()
    user_id  = user["id"]
    lang     = user.get("language", "hi")

    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    result = (
        supabase.table("posts")
        .select("product_name, likes_count, comments_count, reach, engagement_rate, posted_at")
        .eq("user_id", user_id)
        .eq("status", "posted")
        .gte("posted_at", week_ago)
        .order("posted_at", desc=True)
        .execute()
    )
    posts = result.data or []

    if not posts:
        return (
            "📅 *Weekly Report*\n\nपिछले 7 दिन में कोई post नहीं।\n\nइस हफ्ते post शुरू करें! 🚀"
            if lang == "hi" else
            "📅 *Weekly Report*\n\nNo posts in the last 7 days.\n\nStart posting this week! 🚀"
        )

    total_likes   = sum(p.get("likes_count", 0) or 0 for p in posts)
    total_comments = sum(p.get("comments_count", 0) or 0 for p in posts)
    total_reach   = sum(p.get("reach", 0) or 0 for p in posts)
    avg_eng       = round(
        sum(p.get("engagement_rate", 0) or 0 for p in posts) / len(posts), 2
    )
    best = max(posts, key=lambda p: p.get("engagement_rate", 0) or 0)

    if lang == "hi":
        return (
            f"📅 *Weekly Report — पिछले 7 दिन*\n\n"
            f"📸 Posts: `{len(posts)}`\n"
            f"❤️ Likes: `{total_likes}`\n"
            f"💬 Comments: `{total_comments}`\n"
            f"👁️ Reach: `{total_reach}`\n"
            f"📈 Avg Engagement: `{avg_eng}%`\n\n"
            f"🏆 *Best Post:* {best.get('product_name')} (`{best.get('engagement_rate', 0)}%`)"
        )
    return (
        f"📅 *Weekly Report — Last 7 Days*\n\n"
        f"📸 Posts: `{len(posts)}`\n"
        f"❤️ Likes: `{total_likes}`\n"
        f"💬 Comments: `{total_comments}`\n"
        f"👁️ Reach: `{total_reach}`\n"
        f"📈 Avg Engagement: `{avg_eng}%`\n\n"
        f"🏆 *Best Post:* {best.get('product_name')} (`{best.get('engagement_rate', 0)}%`)"
    )


async def get_monthly_report(user: dict) -> str:
    """Generate a monthly performance summary for the user."""
    supabase = get_supabase()
    user_id  = user["id"]
    lang     = user.get("language", "hi")

    month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    result = (
        supabase.table("posts")
        .select("product_name, likes_count, comments_count, reach, engagement_rate, posted_at")
        .eq("user_id", user_id)
        .eq("status", "posted")
        .gte("posted_at", month_ago)
        .order("posted_at", desc=True)
        .execute()
    )
    posts = result.data or []

    if not posts:
        return (
            "📅 *Monthly Report*\n\nपिछले 30 दिन में कोई post नहीं।"
            if lang == "hi" else
            "📅 *Monthly Report*\n\nNo posts in the last 30 days."
        )

    total_likes    = sum(p.get("likes_count", 0) or 0 for p in posts)
    total_comments = sum(p.get("comments_count", 0) or 0 for p in posts)
    total_reach    = sum(p.get("reach", 0) or 0 for p in posts)
    avg_eng        = round(
        sum(p.get("engagement_rate", 0) or 0 for p in posts) / len(posts), 2
    )

    if lang == "hi":
        return (
            f"📅 *Monthly Report — पिछले 30 दिन*\n\n"
            f"📸 Total Posts: `{len(posts)}`\n"
            f"❤️ Total Likes: `{total_likes}`\n"
            f"💬 Total Comments: `{total_comments}`\n"
            f"👁️ Total Reach: `{total_reach}`\n"
            f"📈 Avg Engagement: `{avg_eng}%`\n\n"
            f"📊 Dashboard पर full report देखें: {settings.FRONTEND_URL}/analytics"
        )
    return (
        f"📅 *Monthly Report — Last 30 Days*\n\n"
        f"📸 Total Posts: `{len(posts)}`\n"
        f"❤️ Total Likes: `{total_likes}`\n"
        f"💬 Total Comments: `{total_comments}`\n"
        f"👁️ Total Reach: `{total_reach}`\n"
        f"📈 Avg Engagement: `{avg_eng}%`\n\n"
        f"📊 Full report: {settings.FRONTEND_URL}/analytics"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Metric Snapshotting (for trend tracking)
# ═══════════════════════════════════════════════════════════════════════════════

async def snapshot_account_metrics(user: dict) -> None:
    """
    Take a daily snapshot of account-level metrics and persist to
    analytics_snapshots table for historical trend tracking.
    """
    supabase = get_supabase()
    user_id  = user["id"]

    if not user.get("instagram_token") or not user.get("instagram_id"):
        return

    try:
        from app.services.instagram_service import get_account_insights
        account_data = await get_account_insights(
            user["instagram_id"],
            decrypt_token(user["instagram_token"]),
            period="day",
        )
    except Exception as e:
        logger.warning("Account insights fetch failed for user %s: %s", user_id, e)
        return

    stats = await get_user_dashboard_stats(user_id)

    supabase.table("analytics_snapshots").insert({
        "user_id":            user_id,
        "followers_count":    account_data.get("follower_count", 0),
        "reach_30d":          account_data.get("reach", 0),
        "impressions_30d":    account_data.get("impressions", 0),
        "total_posts":        stats["total_posts"],
        "avg_engagement_rate": stats["avg_engagement_rate"],
    }).execute()
    logger.info("Snapshot saved for user %s", user_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Per-Post Insights Sync
# ═══════════════════════════════════════════════════════════════════════════════

async def sync_post_insights(post: dict) -> None:
    """
    Fetch and persist live insights for a single posted post.
    Called after publishing and periodically by a Celery task.
    """
    supabase   = get_supabase()
    post_id    = post["id"]
    ig_post_id = post.get("instagram_post_id")

    user_r = (
        supabase.table("users")
        .select("instagram_token")
        .eq("id", post["user_id"])
        .single()
        .execute()
    )
    access_token = (user_r.data or {}).get("instagram_token")
    if not ig_post_id or not access_token:
        return

    try:
        from app.services.instagram_service import get_post_insights
        insights = await get_post_insights(ig_post_id, decrypt_token(access_token))
        supabase.table("posts").update({
            "likes_count":     insights.get("likes", 0),
            "comments_count":  insights.get("comments", 0),
            "reach":           insights.get("reach", 0),
            "saved":           insights.get("saved", 0),
            "shares":          insights.get("shares", 0),
            "engagement_rate": insights.get("engagement_rate", 0.0),
        }).eq("id", post_id).execute()
    except Exception as e:
        logger.warning("Insights sync failed for post %s: %s", post_id, e)
