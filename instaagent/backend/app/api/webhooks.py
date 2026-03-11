# backend/app/api/webhooks.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Enterprise Webhook Handler
# Receives events from: Telegram, Instagram (Graph API), Razorpay
# All Telegram logic is delegated to telegram_bot.py (FSM).
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import hmac
import hashlib
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException, Header, Query

from app.config import settings
from app.db.supabase import get_supabase
from app.db.redis_client import get_redis
from app.utils.crypto import decrypt_token

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# TELEGRAM WEBHOOK
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/telegram", summary="Telegram sends all messages and callback events here")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=""),
):
    """
    Entry point for all Telegram updates. After security verification,
    routes to the enterprise FSM bot handler (telegram_bot.py).
    """
    # Verify webhook secret (if configured)
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(403, "Invalid Telegram webhook secret")

    body = await request.json()

    if "callback_query" in body:
        await _dispatch_callback(body["callback_query"])
        return {"ok": True}

    message = body.get("message", {})
    if not message:
        return {"ok": True}

    telegram_id = message.get("chat", {}).get("id")
    if not telegram_id:
        return {"ok": True}

    # ── Admin command gate ────────────────────────────────────────────────────
    admin_id = getattr(settings, "ADMIN_TELEGRAM_ID", "")
    text     = message.get("text", "")
    if admin_id and str(telegram_id) == str(admin_id) and text.startswith("/"):
        cmd = text.split()[0].lstrip("/").upper()
        if cmd in ("BROADCAST", "USERSTATS"):
            from app.services.telegram_bot import handle_admin_command
            await handle_admin_command(telegram_id, text)
            return {"ok": True}

    # ── Route to FSM bot ──────────────────────────────────────────────────────
    from app.services.telegram_bot import handle_message
    await handle_message(telegram_id, message)
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════════
# WHATSAPP WEBHOOK (Stub for Meta Cloud API)
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# WHATSAPP WEBHOOK — Meta Cloud API (Enterprise)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/whatsapp", summary="Meta webhook verification challenge")
async def whatsapp_webhook_verify(
    hub_mode:         str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge:    str = Query(default="", alias="hub.challenge"),
):
    """
    Meta calls this GET endpoint once during webhook setup to confirm ownership.
    Returns the hub.challenge value to confirm the webhook is yours.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verification successful")
        return int(hub_challenge)
    logger.warning("WhatsApp webhook verification failed | mode=%s | token=%s", hub_mode, hub_verify_token)
    raise HTTPException(403, "WhatsApp webhook verification failed — check WHATSAPP_VERIFY_TOKEN")


@router.post("/whatsapp", summary="Meta Cloud API inbound messages")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(default=""),
):
    """
    Receives all WhatsApp Cloud API events (messages, status updates).
    Always returns 200 quickly — heavy work runs in BackgroundTasks.
    """
    raw_body = await request.body()
    logger.info("WA webhook received | sig=%s | body_len=%d", x_hub_signature_256[:40] or "NONE", len(raw_body))

    # ── Security: HMAC-SHA256 Signature Verification ─────────────────────────
    if settings.WHATSAPP_APP_SECRET:
        if not _verify_wa_signature(raw_body, x_hub_signature_256, settings.WHATSAPP_APP_SECRET):
            logger.warning(
                "WhatsApp webhook HMAC FAILED | sig=%s",
                x_hub_signature_256[:40],
            )
            raise HTTPException(403, "Invalid WhatsApp webhook signature")
    else:
        logger.info("WA webhook: WHATSAPP_APP_SECRET not set — skipping HMAC check (dev mode)")

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

    logger.info("WA webhook body: %s", json.dumps(body)[:500])

    # Use FastAPI BackgroundTasks — this is properly managed and won't be GC'd
    background_tasks.add_task(_process_wa_body, body)
    return {"status": "ok"}


async def _process_wa_body(body: dict) -> None:
    """Process WhatsApp webhook body in background after returning 200."""
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "messages":
                    continue
                value = change.get("value", {})

                # Handle incoming messages
                for message in value.get("messages", []):
                    await _process_wa_message(message, value)

                # Handle delivery/read status updates (just log)
                for status_obj in value.get("statuses", []):
                    from app.services.whatsapp_bot import handle_wa_status_update
                    await handle_wa_status_update(status_obj)
    except Exception as e:
        logger.error("WhatsApp webhook processing error: %s", e, exc_info=True)


async def _process_wa_message(message: dict, value: dict) -> None:
    """
    Process a single WhatsApp message with full security checks.
    """
    wamid    = message.get("id", "")           # Unique WhatsApp message ID
    from_ph  = message.get("from", "")         # Sender's phone number
    msg_type = message.get("type", "")

    if not from_ph or not wamid:
        return

    # ── Security Layer 2: Idempotency (deduplicate Meta retries) ────────────
    # Meta retries if it doesn't get 200 quickly — we must not double-process
    try:
        r = get_redis()
        if not r:
            raise Exception("Redis not available")
        idem_key = f"wa_msg:{wamid}"
        if r.exists(idem_key):
            logger.info("WA message already processed — skipping | wamid=%s", wamid)
            return
        r.setex(idem_key, 3600 * 24, "1")    # Mark as processed for 24h
    except Exception as e:
        logger.warning("Redis idempotency check failed — processing anyway | error=%s", e)

    # ── Security Layer 3: Per-phone rate limiting ────────────────────────────
    # Prevent abuse: max WHATSAPP_RATE_LIMIT_PHOTOS photos per phone per hour
    if msg_type == "image":
        try:
            current_hour = int(__import__("time").time() // 3600)
            rl_key = f"wa_rate:{from_ph}:{current_hour}"
            count  = r.incr(rl_key)
            if count == 1:
                r.expire(rl_key, 7200)
            limit = settings.WHATSAPP_RATE_LIMIT_PHOTOS
            if count > limit:
                logger.warning("WA rate limit exceeded | phone=%s | count=%d", from_ph, count)
                from app.services.whatsapp_service import send_wa_text
                await send_wa_text(
                    from_ph,
                    f"⚠️ You've sent too many photos this hour (max {limit}/hour). "
                    f"Please wait before sending more."
                )
                return
        except Exception as e:
            logger.warning("WA rate limit check failed | error=%s", e)

    # ── Route to FSM bot ─────────────────────────────────────────────────────
    logger.info("WA message | phone=%s | type=%s | wamid=%s", from_ph, msg_type, wamid)
    from app.services.whatsapp_bot import handle_wa_message
    await handle_wa_message(from_ph, message)



async def _dispatch_callback(callback_query: dict) -> None:
    """Route inline button callbacks to the FSM bot."""
    from app.services.telegram_bot import handle_callback_query
    await handle_callback_query(callback_query)


def _verify_wa_signature(body: bytes, signature_header: str, app_secret: str) -> bool:
    """
    Verify Meta's HMAC-SHA256 webhook signature using constant-time comparison.

    Meta sends: X-Hub-Signature-256: sha256=<hex_digest>
    We compute: HMAC-SHA256(body, app_secret)
    
    Uses hmac.compare_digest to prevent timing attacks.
    Returns False if signature is missing or invalid.
    """
    if not signature_header.startswith("sha256="):
        return False
    received_sig = signature_header[7:]   # Strip "sha256=" prefix
    expected_sig = hmac.new(
        app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    # Constant-time comparison — prevents timing side-channel attacks
    return hmac.compare_digest(received_sig, expected_sig)


# ═══════════════════════════════════════════════════════════════════════════════
# INSTAGRAM WEBHOOK
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/instagram", summary="Instagram webhook verification (Meta challenge)")
async def instagram_webhook_verify(
    hub_mode:         str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge:    str = Query(default="", alias="hub.challenge"),
):
    """Meta calls this GET to verify the webhook endpoint during setup."""
    logger.info("Instagram webhook verify | mode=%s | token=%s", hub_mode, hub_verify_token[:10])
    if hub_mode == "subscribe" and hub_verify_token == settings.INSTAGRAM_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(403, "Webhook verification failed")


@router.post("/instagram", summary="Instagram Graph API events (comments, DMs, mentions)")
async def instagram_webhook_events(request: Request):
    """
    Receives all subscribed Instagram events:
    - New comment on a post → AI reply
    - New DM → forward summary to owner's Telegram
    - Story mention → notify owner on Telegram
    """
    body = await request.json()
    logger.debug("Instagram webhook: %s", json.dumps(body)[:500])

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            field = change.get("field", "")
            value = change.get("value", {})

            if field == "comments":
                await _handle_new_comment(value)

            elif field == "messages":
                await _handle_ig_dm(value)

            elif field == "story_insights" or field == "mentions":
                await _handle_story_mention(value)

    return {"status": "ok"}


async def _handle_new_comment(comment_data: dict) -> None:
    """Auto-reply to a new Instagram comment using AI."""
    from app.services.caption_service import generate_comment_reply
    from app.services.instagram_service import reply_to_comment

    supabase    = get_supabase()
    comment_id  = comment_data.get("id")
    comment_text = comment_data.get("text", "")
    media_id    = comment_data.get("media", {}).get("id", "")

    if not comment_text or not comment_id:
        return

    post_result = (
        supabase.table("posts")
        .select("*, users(instagram_token, language, telegram_id)")
        .eq("instagram_post_id", media_id)
        .single()
        .execute()
    )
    if not post_result.data:
        return

    post         = post_result.data
    user         = post.get("users", {})
    access_token = user.get("instagram_token")
    language     = user.get("language", "hi")

    if not access_token:
        return

    try:
        reply_text = await generate_comment_reply(
            comment_text=comment_text,
            product_name=post["product_name"],
            language=language,
        )
        await reply_to_comment(comment_id, decrypt_token(access_token), reply_text)

        supabase.table("comments").insert({
            "post_id":              post["id"],
            "user_id":              post["user_id"],
            "instagram_comment_id": comment_id,
            "comment_text":         comment_text,
            "reply_text":           reply_text,
            "reply_sent":           True,
        }).execute()

    except Exception as e:
        logger.error("Comment reply failed for comment %s: %s", comment_id, e)


async def _handle_ig_dm(dm_data: dict) -> None:
    """
    Forward an Instagram DM summary to the business owner on Telegram.
    dm_data structure depends on the Messenger webhook payload.
    """
    from app.services.telegram_service import send_message

    sender_id = dm_data.get("sender", {}).get("id", "")
    msg_text  = dm_data.get("message", {}).get("text", "")
    ig_user_id = dm_data.get("recipient", {}).get("id", "")

    if not msg_text or not ig_user_id:
        return

    supabase = get_supabase()
    result   = (
        supabase.table("users")
        .select("telegram_id, language, instagram_username")
        .eq("instagram_id", ig_user_id)
        .execute()
    )
    if not result.data:
        return

    user        = result.data[0]
    telegram_id = user.get("telegram_id")
    if not telegram_id:
        return

    lang     = user.get("language", "hi")
    username = user.get("instagram_username", "your account")

    if lang == "hi":
        notification = (
            f"💬 *नया Instagram DM!*\n\n"
            f"👤 Sender ID: `{sender_id}`\n"
            f"📩 Message: _{msg_text[:300]}_\n\n"
            f"Instagram app पर जाकर reply करें।"
        )
    else:
        notification = (
            f"💬 *New Instagram DM!*\n\n"
            f"👤 Sender ID: `{sender_id}`\n"
            f"📩 Message: _{msg_text[:300]}_\n\n"
            f"Reply directly in the Instagram app."
        )

    try:
        await send_message(int(telegram_id), notification)
    except Exception as e:
        logger.warning("Telegram DM forward failed: %s", e)


async def _handle_story_mention(mention_data: dict) -> None:
    """Notify the business owner when their account is mentioned in a Story."""
    from app.services.telegram_service import send_message

    media_id   = mention_data.get("media_id", "")
    ig_user_id = mention_data.get("mentioned_media", {}).get("id", "")

    if not ig_user_id and not media_id:
        return

    supabase = get_supabase()
    result   = (
        supabase.table("users")
        .select("telegram_id, language, instagram_username")
        .execute()
    )
    # Story mentions come from the account's webhook — match by instagram_id
    # (Meta sends this to the mentioned account's subscription)
    if not result.data:
        return

    for user in result.data:
        telegram_id = user.get("telegram_id")
        if not telegram_id:
            continue
        lang = user.get("language", "hi")
        msg = (
            f"⭐ *आपको एक Instagram Story में mention किया गया!*\n\n"
            f"Story ID: `{media_id}`\n"
            f"Instagram app पर check करें।"
            if lang == "hi" else
            f"⭐ *You were mentioned in an Instagram Story!*\n\n"
            f"Story ID: `{media_id}`\n"
            f"Check the Instagram app to respond."
        )
        try:
            await send_message(int(telegram_id), msg)
        except Exception as e:
            logger.warning("Story mention notify failed: %s", e)
        break   # Only notify the account owner once


# ═══════════════════════════════════════════════════════════════════════════════
# RAZORPAY WEBHOOK
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/razorpay", summary="Razorpay payment events (subscription lifecycle)")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
):
    """Handles payment lifecycle events: activated, cancelled, failed."""
    body_bytes = await request.body()

    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, x_razorpay_signature):
        raise HTTPException(400, "Invalid Razorpay webhook signature")

    body    = json.loads(body_bytes)
    event   = body.get("event", "")
    payload = body.get("payload", {})
    supabase = get_supabase()

    if event == "subscription.activated":
        await _rp_subscription_activated(supabase, payload)

    elif event == "subscription.cancelled":
        await _rp_subscription_cancelled(supabase, payload)

    elif event == "payment.failed":
        await _rp_payment_failed(supabase, payload)

    return {"status": "ok"}


async def _rp_subscription_activated(supabase, payload: dict) -> None:
    sub            = payload.get("subscription", {}).get("entity", {})
    razorpay_sub_id = sub.get("id")

    supabase.table("subscriptions").update({"status": "active"}).eq(
        "razorpay_sub_id", razorpay_sub_id
    ).execute()

    result = supabase.table("subscriptions").select("user_id, plan").eq(
        "razorpay_sub_id", razorpay_sub_id
    ).single().execute()

    if result.data:
        supabase.table("users").update({"plan": result.data["plan"]}).eq(
            "id", result.data["user_id"]
        ).execute()

        # Notify user on Telegram
        await _notify_payment_event(
            supabase, result.data["user_id"],
            hi_msg=(
                "🎉 *आपका subscription activate हो गया!*\n\n"
                f"Plan: *{result.data['plan'].upper()}*\n"
                "अब InstaAgent के सभी features use करें! 🚀"
            ),
            en_msg=(
                "🎉 *Your subscription is now active!*\n\n"
                f"Plan: *{result.data['plan'].upper()}*\n"
                "Enjoy all InstaAgent features! 🚀"
            ),
        )


async def _rp_subscription_cancelled(supabase, payload: dict) -> None:
    sub            = payload.get("subscription", {}).get("entity", {})
    razorpay_sub_id = sub.get("id")

    supabase.table("subscriptions").update({"status": "cancelled"}).eq(
        "razorpay_sub_id", razorpay_sub_id
    ).execute()

    result = supabase.table("subscriptions").select("user_id").eq(
        "razorpay_sub_id", razorpay_sub_id
    ).single().execute()

    if result.data:
        user_id = result.data["user_id"]
        supabase.table("users").update({"plan": "free"}).eq("id", user_id).execute()
        await _notify_payment_event(
            supabase, user_id,
            hi_msg=(
                "⚠️ *आपका subscription cancel हो गया।*\n\n"
                "आप अब free plan पर हैं।\n"
                f"Renew करें: {settings.FRONTEND_URL}/billing"
            ),
            en_msg=(
                "⚠️ *Your subscription has been cancelled.*\n\n"
                "You are now on the free plan.\n"
                f"Renew at: {settings.FRONTEND_URL}/billing"
            ),
        )


async def _rp_payment_failed(supabase, payload: dict) -> None:
    payment = payload.get("payment", {}).get("entity", {})
    notes   = payment.get("notes", {})
    user_id = notes.get("user_id")

    if not user_id:
        return

    await _notify_payment_event(
        supabase, user_id,
        hi_msg=(
            "❌ *Payment fail हो गई!*\n\n"
            "Payment process नहीं हो सकी। कृपया दोबारा try करें:\n"
            f"{settings.FRONTEND_URL}/billing"
        ),
        en_msg=(
            "❌ *Payment Failed!*\n\n"
            "Your payment could not be processed. Please try again:\n"
            f"{settings.FRONTEND_URL}/billing"
        ),
    )


async def _notify_payment_event(
    supabase, user_id: str, hi_msg: str, en_msg: str
) -> None:
    from app.services.telegram_service import send_message

    user_r = (
        supabase.table("users")
        .select("telegram_id, language")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not user_r.data:
        return

    user        = user_r.data
    telegram_id = user.get("telegram_id")
    if not telegram_id:
        return

    msg = hi_msg if user.get("language", "hi") == "hi" else en_msg
    try:
        await send_message(int(telegram_id), msg)
    except Exception as e:
        logger.warning("Payment notify failed for user %s: %s", user_id, e)
