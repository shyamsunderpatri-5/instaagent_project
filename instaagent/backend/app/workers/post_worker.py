# backend/app/workers/post_worker.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Enterprise Post Worker (Celery Beat)
# Runs every 60 seconds to publish scheduled posts.
# FIXED: Timezone bug — all times now stored and compared in UTC.
# IST = UTC + 5:30. scheduled_at is stored as UTC ISO string.
# Enterprise additions:
#   - Smart rate-limit retry (Instagram code 32 → reschedule +1h)
#   - Post-publish analytics snapshot trigger
#   - Best-time-to-post suggestion
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from app.workers.celery_app import celery_app
from app.db.supabase import get_supabase
from app.utils.crypto import decrypt_token

logger = logging.getLogger(__name__)
IST_OFFSET = timedelta(hours=5, minutes=30)  # UTC+5:30


def ist_time_to_utc(ist_time_str: str, date: datetime | None = None) -> datetime:
    """
    Convert a time string like '15:33' (IST) to a UTC-aware datetime for today.
    If 'date' is provided, use that date; otherwise use today (UTC).
    Returns a UTC-aware datetime.
    """
    if date is None:
        # Use current date in IST to avoid "yesterday" or "tomorrow" shifts during UTC conversion
        now_utc = datetime.now(timezone.utc)
        date = now_utc + IST_OFFSET
    
    hour, minute = map(int, ist_time_str.split(":"))
    # Build naive IST datetime and normalize
    ist_dt = date.replace(hour=hour, minute=minute, second=0, microsecond=0, tzinfo=None)
    utc_dt = (ist_dt - IST_OFFSET).replace(tzinfo=timezone.utc)
    return utc_dt


def parse_scheduled_at(scheduled_at_str: str) -> datetime:
    """
    Parse a scheduled_at string from the DB into a UTC-aware datetime.
    Handles:
      - ISO strings with 'Z' suffix (already UTC)
      - ISO strings with '+00:00' or '+05:30' etc.
      - Naive ISO strings (assumed to be UTC — we always store UTC now)
    """
    s = scheduled_at_str.strip()
    # Replace Z with UTC offset
    s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            # Assume UTC for legacy naive strings
            dt = dt.replace(tzinfo=timezone.utc)
        # Normalize to UTC
        return dt.astimezone(timezone.utc)
    except ValueError:
        logger.error("Cannot parse scheduled_at: %s — defaulting to now", scheduled_at_str)
        return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# Beat Task — runs every 60 seconds
# ═══════════════════════════════════════════════════════════════════════════════

@celery_app.task(name="app.workers.post_worker.publish_scheduled_posts")
def publish_scheduled_posts() -> None:
    """
    Called by Celery Beat every 60 seconds.
    Finds all posts with status='scheduled' where scheduled_at <= now
    and publishes them to Instagram.
    """
    asyncio.run(_publish_due_posts())


async def _publish_due_posts() -> None:
    from app.services.instagram_service import post_to_instagram

    supabase = get_supabase()
    now_utc  = datetime.now(timezone.utc)
    now_iso  = now_utc.isoformat()

    logger.info("🕐 [HEARTBEAT] Post worker checking for due posts — UTC now: %s (IST: %s)",
                now_utc.strftime("%Y-%m-%d %H:%M:%S"),
                (now_utc + IST_OFFSET).strftime("%Y-%m-%d %H:%M:%S"))

    result = (
        supabase.table("posts")
        .select("*, users(instagram_token, instagram_id, telegram_id, language, preferred_post_time)")
        .eq("status", "scheduled")
        .lte("scheduled_at", now_iso)
        .execute()
    )

    if not result.data:
        logger.info("🕐 [HEARTBEAT] No posts due (scheduled_at <= %s)", now_iso)
        return

    logger.info("Post worker: %d post(s) due for publishing.", len(result.data))
    for post in result.data:
        sched = post.get("scheduled_at", "?")
        logger.info("  → Publishing post %s (scheduled_at=%s)", post["id"], sched)
        await _publish_single_post(supabase, post)


# ═══════════════════════════════════════════════════════════════════════════════
# Single-Post Publisher (shared by Beat + Telegram callback)
# ═══════════════════════════════════════════════════════════════════════════════

async def _publish_single_post(supabase, post: dict) -> None:
    """Publish one scheduled post to Instagram and update DB."""
    from app.services.telegram_service import send_message, send_inline_keyboard
    from app.services.instagram_service import post_to_instagram

    post_id          = post["id"]
    user             = post.get("users", {})
    instagram_token  = user.get("instagram_token")
    instagram_id     = user.get("instagram_id")
    telegram_id      = user.get("telegram_id")
    lang             = user.get("language", "hi")

    # Guard — Post status must be 'scheduled'
    if post.get("status") != "scheduled":
        logger.warning("Post worker skipped | status=%s | post_id=%s", post.get("status"), post_id)
        return

    # Guard — Instagram must be connected
    if not instagram_token or not instagram_id:
        supabase.table("posts").update({
            "status":        "failed",
            "error_message": "Instagram not connected.",
        }).eq("id", post_id).execute()
        return

    # Guard — edited photo must exist
    if not post.get("edited_photo_url"):
        supabase.table("posts").update({
            "status":        "failed",
            "error_message": "Edited photo URL missing.",
        }).eq("id", post_id).execute()
        return

    try:
        hashtags = " ".join(post.get("hashtags") or [])
        caption  = f"{post.get('caption_hindi', '')} {hashtags}".strip()

        if post.get("is_carousel_duo") and post.get("secondary_photo_url"):
            from app.services.instagram_service import publish_carousel
            instagram_post_id = await publish_carousel(
                instagram_user_id=instagram_id,
                access_token=decrypt_token(instagram_token),
                image_urls=[post["edited_photo_url"], post["secondary_photo_url"]],
                caption=caption,
            )
        else:
            instagram_post_id = await post_to_instagram(
                instagram_user_id=instagram_id,
                access_token=decrypt_token(instagram_token),
                image_url=post["edited_photo_url"],
                caption=caption,
            )

        permalink = f"https://www.instagram.com/p/{instagram_post_id}/"

        supabase.table("posts").update({
            "status":              "posted",
            "posted_at":           datetime.now(timezone.utc).isoformat(),
            "instagram_post_id":   instagram_post_id,
            "instagram_permalink": permalink,
            "error_message":       None,
        }).eq("id", post_id).execute()

        # ── Notify user on Telegram ───────────────────────────────────────────
        if telegram_id:
            product = post.get("product_name", "आपका product")
            if lang == "hi":
                msg = (
                    f"✅ *{product}* Instagram पर post हो गया!\n\n"
                    f"🔗 देखें: {permalink}\n\n"
                    f"AI अब comments का reply करेगा 🤖"
                )
            else:
                msg = (
                    f"✅ *{product}* has been posted to Instagram!\n\n"
                    f"🔗 View: {permalink}\n\n"
                    f"AI will now auto-reply to comments 🤖"
                )

            await send_inline_keyboard(
                int(telegram_id),
                msg,
                buttons=[
                    [{"text": "📊 View Stats", "callback_data": f"view_stats:{post_id}"}],
                ],
            )

        # ── Trigger analytics snapshot (non-blocking) ─────────────────────────
        try:
            from app.services.analytics_service import sync_post_insights
            await sync_post_insights(post)
        except Exception as e:
            logger.warning("Post-publish analytics sync failed: %s", e)

    except Exception as e:
        err_str = str(e)
        logger.error("Failed to publish post %s: %s", post_id, err_str)

        # ── Instagram rate-limit: reschedule +1 hour instead of failing ───────
        if "code 32" in err_str.lower() or "rate" in err_str.lower():
            # Exponentially backoff or fixed 1h shift
            new_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            supabase.table("posts").update({
                "scheduled_at":  new_time,
                "status":        "scheduled", # Re-queue
                "error_message": f"Rate limit hit — rescheduled to {new_time[:16]} UTC",
            }).eq("id", post_id).execute()

            if telegram_id:
                notify_msg = (
                    f"⚠️ Instagram rate limit — *{post.get('product_name', 'Post')}* "
                    f"1 घंटे बाद auto-post होगा।"
                    if lang == "hi" else
                    f"⚠️ Instagram rate limit — *{post.get('product_name', 'Post')}* "
                    f"will be retried in 1 hour."
                )
                try:
                    await send_message(int(telegram_id), notify_msg)
                except Exception:
                    pass
            return

        # ── Generic failure ───────────────────────────────────────────────────
        supabase.table("posts").update({
            "status":        "failed",
            "error_message": err_str[:500],
        }).eq("id", post_id).execute()

        if telegram_id:
            fail_msg = (
                f"❌ Post करने में error: {err_str[:100]}\n\nDashboard पर जाएं।"
                if lang == "hi" else
                f"❌ Failed to post: {err_str[:100]}\n\nPlease check your dashboard."
            )
            try:
                from app.services.telegram_service import send_message
                await send_message(int(telegram_id), fail_msg)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# Smart Scheduling — Best Time Suggestion
# ═══════════════════════════════════════════════════════════════════════════════

async def suggest_best_post_time(user_id: str) -> str:
    """
    Analyse the user's past post engagement data to suggest the best posting
    hour (IST). Falls back to 7pm IST if insufficient data.
    Returns: 'HH:00' string
    """
    supabase = get_supabase()
    result   = (
        supabase.table("posts")
        .select("posted_at, engagement_rate")
        .eq("user_id", user_id)
        .eq("status", "posted")
        .not_.is_("engagement_rate", "null")
        .limit(50)
        .execute()
    )
    posts = result.data or []

    if len(posts) < 5:
        return "19:00"   # Default: 7pm IST

    from collections import defaultdict
    hourly: dict[int, list[float]] = defaultdict(list)

    for p in posts:
        try:
            # posted_at is UTC ISO string — convert to IST (+5:30) accurately
            dt       = datetime.fromisoformat(p["posted_at"].replace("Z", "+00:00"))
            dt_utc   = dt.astimezone(timezone.utc)
            dt_ist   = dt_utc + IST_OFFSET
            ist_hour = dt_ist.hour
            hourly[ist_hour].append(p.get("engagement_rate", 0) or 0)
        except Exception:
            continue

    if not hourly:
        return "19:00"

    # Find hour with highest average engagement
    best_hour = max(hourly, key=lambda h: sum(hourly[h]) / len(hourly[h]))
    return f"{best_hour:02d}:00"
