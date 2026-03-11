# backend/app/workers/instagram_token_refresher.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Enterprise Token Auto-Refresh Worker
# Celery Beat task that runs daily at 3am IST.
# Finds users whose Instagram tokens expire within N days and refreshes them.
# Notifies users via Telegram if a refresh fails.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from app.workers.celery_app import celery_app
from app.db.supabase import get_supabase
from app.config import settings
from app.utils.crypto import decrypt_token

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.instagram_token_refresher.refresh_expiring_tokens")
def refresh_expiring_tokens() -> None:
    """
    Celery Beat daily task.
    Refreshes all Instagram tokens that expire within INSTAGRAM_TOKEN_REFRESH_DAYS.
    """
    asyncio.run(_refresh_all())


async def _refresh_all() -> None:
    from app.services.instagram_service import refresh_long_lived_token
    from app.services.telegram_service import send_message

    supabase    = get_supabase()
    refresh_days = getattr(settings, "INSTAGRAM_TOKEN_REFRESH_DAYS", 7)
    cutoff       = (datetime.now(timezone.utc) + timedelta(days=refresh_days)).isoformat()

    # Find users whose tokens expire soon
    result = (
        supabase.table("users")
        .select("id, instagram_token, instagram_token_expires_at, telegram_id, language")
        .neq("instagram_token", None)
        .lte("instagram_token_expires_at", cutoff)
        .execute()
    )
    users = result.data or []

    if not users:
        logger.info("Token refresher: no tokens expiring within %d days.", refresh_days)
        return

    logger.info("Token refresher: %d token(s) to refresh.", len(users))

    for user in users:
        user_id      = user["id"]
        access_token = user.get("instagram_token")
        telegram_id  = user.get("telegram_id")
        lang         = user.get("language", "hi")

        if not access_token:
            continue

        try:
            new_token_data = await refresh_long_lived_token(decrypt_token(access_token))
            new_token      = new_token_data["access_token"]
            expires_in_sec = new_token_data.get("expires_in", 5184000)   # default 60 days
            new_expiry     = (
                datetime.now(timezone.utc) + timedelta(seconds=expires_in_sec)
            ).isoformat()

            supabase.table("users").update({
                "instagram_token":            new_token,
                "instagram_token_expires_at": new_expiry,
            }).eq("id", user_id).execute()

            logger.info("Token refreshed for user %s. New expiry: %s", user_id, new_expiry)

        except Exception as e:
            logger.error("Token refresh FAILED for user %s: %s", user_id, e)

            # Notify user on Telegram if connected
            if telegram_id:
                msg = (
                    "⚠️ *Instagram Token Expired*\n\n"
                    "आपका Instagram token expire हो गया है।\n"
                    "कृपया Settings में जाकर Instagram फिर से connect करें।\n\n"
                    f"🔗 {settings.FRONTEND_URL}/settings"
                    if lang == "hi" else
                    "⚠️ *Instagram Token Expired*\n\n"
                    "Your Instagram access token has expired.\n"
                    "Please reconnect Instagram in your Settings.\n\n"
                    f"🔗 {settings.FRONTEND_URL}/settings"
                )
                try:
                    await send_message(telegram_id, msg)
                except Exception as notify_err:
                    logger.warning("Telegram notify failed for user %s: %s", user_id, notify_err)
