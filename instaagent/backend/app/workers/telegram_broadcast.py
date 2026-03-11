# backend/app/workers/telegram_broadcast.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Enterprise Telegram Broadcast Worker
# Sends a message to all (or a subset of) active users.
# Respects Telegram's 30 msg/sec rate limit via asyncio sleep.
# Used for: admin broadcasts, weekly/monthly analytics reports.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.workers.celery_app import celery_app
from app.db.supabase import get_supabase

logger = logging.getLogger(__name__)

# Telegram Bot API allows ~30 messages/second to different chats
_RATE_LIMIT_DELAY = 0.04   # 40ms ≈ 25 msg/sec (conservative)


# ═══════════════════════════════════════════════════════════════════════════════
# Celery Tasks
# ═══════════════════════════════════════════════════════════════════════════════

@celery_app.task(name="app.workers.telegram_broadcast.broadcast_to_all_users_task")
def broadcast_to_all_users_task(message: str, plan_filter: Optional[str] = None) -> dict:
    """
    Broadcast a Telegram message to all users who have a telegram_id.
    plan_filter: if provided, only send to users on this plan (e.g. 'pro', 'starter')
    Returns: {sent, failed, skipped}
    """
    return asyncio.run(_broadcast(message, plan_filter=plan_filter))


@celery_app.task(name="app.workers.telegram_broadcast.send_weekly_reports_task")
def send_weekly_reports_task() -> dict:
    """Send personalised weekly analytics reports to all active users."""
    return asyncio.run(_send_periodic_reports(period="weekly"))


@celery_app.task(name="app.workers.telegram_broadcast.send_monthly_reports_task")
def send_monthly_reports_task() -> dict:
    """Send personalised monthly analytics reports to all active users."""
    return asyncio.run(_send_periodic_reports(period="monthly"))


# ═══════════════════════════════════════════════════════════════════════════════
# Internal Async Implementations
# ═══════════════════════════════════════════════════════════════════════════════

async def _broadcast(message: str, plan_filter: Optional[str] = None) -> dict:
    from app.services.telegram_service import send_message

    supabase = get_supabase()
    query    = supabase.table("users").select("telegram_id, language")

    if plan_filter:
        query = query.eq("plan", plan_filter)

    users  = query.execute().data or []
    sent   = 0
    failed = 0
    skipped = 0

    for user in users:
        tid = user.get("telegram_id")
        if not tid:
            skipped += 1
            continue
        try:
            await send_message(int(tid), message)
            sent += 1
        except Exception as e:
            logger.warning("Broadcast failed for telegram_id %s: %s", tid, e)
            failed += 1
        await asyncio.sleep(_RATE_LIMIT_DELAY)

    logger.info("Broadcast complete — sent:%d failed:%d skipped:%d", sent, failed, skipped)
    return {"sent": sent, "failed": failed, "skipped": skipped}


async def _send_periodic_reports(period: str) -> dict:
    """
    Fetch all active users with telegram_id + instagram connected,
    generate their personalised report, and deliver via Telegram.
    """
    from app.services.telegram_service import send_message
    from app.services.analytics_service import get_weekly_report, get_monthly_report

    supabase = get_supabase()
    users    = (
        supabase.table("users")
        .select("*")
        .neq("telegram_id", None)
        .neq("plan", "free")        # Only paid users get reports
        .execute()
        .data or []
    )

    sent   = 0
    failed = 0

    for user in users:
        tid = user.get("telegram_id")
        if not tid:
            continue
        try:
            if period == "weekly":
                report = await get_weekly_report(user)
            else:
                report = await get_monthly_report(user)
            await send_message(int(tid), report)
            sent += 1
        except Exception as e:
            logger.warning("Report send failed for user %s: %s", user.get("id"), e)
            failed += 1
        await asyncio.sleep(_RATE_LIMIT_DELAY)

    logger.info("%s reports — sent:%d failed:%d", period.capitalize(), sent, failed)
    return {"sent": sent, "failed": failed}
