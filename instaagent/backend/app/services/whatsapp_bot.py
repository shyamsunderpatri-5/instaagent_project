# backend/app/services/whatsapp_bot.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — WhatsApp Business Bot (Enterprise FSM)
#
# Flow:
#   1. Seller sends photo to InstaAgent WA Business number
#   2. Bot looks up seller by phone number (must be added in Settings)
#   3. Asks for product name (if not given in caption)
#   4. Triggers AI pipeline via Celery
#   5. Sends back enhanced preview + approve/discard buttons
#   6. On approve → posts to Instagram
#   7. Sends confirmation with post URL
#
# Session management: Redis FSM (same pattern as Telegram bot)
# Language: Read from user profile (hi/en/te/ta/kn/mr)
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import redis as redis_lib

from app.config import settings
from app.db.supabase import get_supabase
from app.db.redis_client import get_redis
from app.services.whatsapp_service import (
    send_wa_text,
    send_wa_image,
    send_wa_buttons,
    download_wa_media,
)

logger = logging.getLogger(__name__)

# ── Redis session config ───────────────────────────────────────────────────────
SESSION_TTL = 3600 * 4   # 4-hour FSM session lifetime
def _get_redis():
    """Delegates to central Redis client."""
    return get_redis()


def _get_session(phone: str) -> dict:
    r = _get_redis()
    if r is None:
        return {"state": "IDLE", "context": {}, "lang": "hi"}
    raw = r.get(f"wa_session:{phone}")
    if raw:
        return json.loads(raw)
    return {"state": "IDLE", "context": {}, "lang": "hi"}


def _save_session(phone: str, session: dict) -> None:
    r = _get_redis()
    if r is None:
        return
    r.setex(f"wa_session:{phone}", SESSION_TTL, json.dumps(session))


def _clear_session(phone: str) -> None:
    r = _get_redis()
    if r is None:
        return
    r.delete(f"wa_session:{phone}")


# ── Translations ───────────────────────────────────────────────────────────────

def _t(lang: str, key: str) -> str:
    strings: dict[str, dict[str, str]] = {
        "hi": {
            "welcome": (
                "🙏 *नमस्ते! मैं InstaAgent हूँ — आपका WhatsApp Instagram Assistant!*\n\n"
                "📸 कोई भी product photo भेजें — मैं:\n\n"
                "✅ Background remove करूँगा\n"
                "✅ Photo professional बनाऊँगा\n"
                "✅ Hindi + English caption लिखूँगा\n"
                "✅ 20 hashtags suggest करूँगा\n"
                "✅ Instagram पर post करूँगा\n\n"
                "बस photo भेजिए! 🚀"
            ),
            "not_registered": (
                "❌ *आपका account नहीं मिला।*\n\n"
                "कृपया InstaAgent पर register करें और Settings में अपना WhatsApp नंबर जोड़ें:\n"
                "{url}\n\n"
                "Register करने के बाद photo भेजें — मैं तैयार हूँ! 🎯"
            ),
            "ask_product_name": (
                "📝 *Product का नाम बताएं:*\n\n"
                "Example: *सोने की चूड़ी*, *Cotton Suit*, *Diya Set*\n\n"
                "(या नाम के साथ photo भेजें)"
            ),
            "processing": (
                "📸 Photo मिली! AI processing शुरू हो रही है...\n\n"
                "⏳ *~15 seconds* में तैयार होगा:\n"
                "✅ Background remove\n"
                "✅ Photo enhance\n"
                "✅ Caption generate\n"
                "✅ 20 Hashtags\n\n"
                "रुकें... 🔄"
            ),
            "no_instagram": (
                "⚠️ *Instagram connect नहीं है।*\n\n"
                "InstaAgent dashboard पर जाएं और Settings में Instagram जोड़ें:\n{url}"
            ),
            "cancelled": "❌ Action रद्द किया गया।",
            "plan_limit": (
                "⚠️ *इस महीने की post limit पूरी हो गई।*\n\n"
                "Upgrade करें: {url}"
            ),
            "ask_enhancement": "✨ इस photo को कैसे post करना चाहते हैं?",
            "approved_posting": "✅ Approve किया! Instagram पर post हो रहा है... ⏳",
            "posted_success": (
                "🎉 *Successfully Posted!*\n\n"
                "📸 Photo Instagram पर live है!\n"
                "🔗 Post: {url}\n\n"
                "अगली photo भेजें! 🚀"
            ),
            "post_failed": "❌ Instagram post में error आई। Dashboard से manually try करें।",
            "discard": "🗑️ Photo discard कर दी गई। नई photo भेजें।",
            "btn_enhanced": "✨ Enhanced",
            "btn_original": "🖼 Original",
            "btn_both": "📸 Both",
            "btn_discard": "🗑 Discard",
        },
        "en": {
            "welcome": (
                "👋 *Welcome to InstaAgent — Your WhatsApp Instagram Assistant!*\n\n"
                "📸 Send any product photo and I'll:\n\n"
                "✅ Remove the background\n"
                "✅ Enhance professionally\n"
                "✅ Write Hindi + English captions\n"
                "✅ Suggest 20 hashtags\n"
                "✅ Post to Instagram\n\n"
                "Just send a photo to get started! 🚀"
            ),
            "not_registered": (
                "❌ *Your account was not found.*\n\n"
                "Please register on InstaAgent and add your WhatsApp number in Settings:\n"
                "{url}\n\n"
                "After registering, send your photo — I'm ready! 🎯"
            ),
            "ask_product_name": (
                "📝 *What is the product name?*\n\n"
                "Example: *Gold Bangles*, *Cotton Suit*, *Diya Set*\n\n"
                "(Or send the photo with the name as caption)"
            ),
            "processing": (
                "📸 Photo received! AI processing started...\n\n"
                "⏳ Ready in *~15 seconds:*\n"
                "✅ Background removal\n"
                "✅ Photo enhancement\n"
                "✅ Caption generation\n"
                "✅ 20 Hashtags\n\n"
                "Please wait... 🔄"
            ),
            "no_instagram": (
                "⚠️ *Instagram is not connected.*\n\n"
                "Go to your InstaAgent dashboard → Settings → Connect Instagram:\n{url}"
            ),
            "cancelled": "❌ Action cancelled.",
            "plan_limit": (
                "⚠️ *You've reached your monthly post limit.*\n\n"
                "Upgrade your plan: {url}"
            ),
            "ask_enhancement": "✨ How would you like to post this photo?",
            "approved_posting": "✅ Approved! Posting to Instagram... ⏳",
            "posted_success": (
                "🎉 *Successfully Posted!*\n\n"
                "📸 Your photo is now live on Instagram!\n"
                "🔗 Post: {url}\n\n"
                "Send your next product photo! 🚀"
            ),
            "post_failed": "❌ Instagram post failed. Try from your dashboard.",
            "discard": "🗑️ Photo discarded. Send a new photo anytime.",
            "btn_enhanced": "✨ Enhanced",
            "btn_original": "🖼 Original",
            "btn_both": "📸 Both",
            "btn_discard": "🗑 Discard",
        },
    }
    lang_key = lang if lang in strings else "en"
    return strings[lang_key].get(key, key)


# ── User lookup ────────────────────────────────────────────────────────────────

def _lookup_user_by_phone(phone: str) -> Optional[dict]:
    """Look up user by whatsapp_phone field in Supabase."""
    supabase = get_supabase()
    # Normalize phone for lookup (try both with and without country code)
    phones_to_try = {phone}
    # 919876543210 → also try 9876543210
    if phone.startswith("91") and len(phone) == 12:
        phones_to_try.add(phone[2:])
    # 9876543210 → also try 919876543210
    if len(phone) == 10:
        phones_to_try.add("91" + phone)

    for ph in phones_to_try:
        result = (
            supabase.table("users")
            .select("id, email, full_name, plan, language, instagram_token, instagram_username, telegram_id, whatsapp_phone")
            .eq("whatsapp_phone", ph)
            .execute()
        )
        if result.data:
            return result.data[0]
    return None


def _check_plan_limit(user_id: str, plan: str) -> bool:
    """Returns True if user is within their monthly post limit."""
    plan_limits = {
        "free":    settings.PLAN_FREE_POSTS,
        "starter": settings.PLAN_STARTER_POSTS,
        "growth":  settings.PLAN_GROWTH_POSTS,
        "agency":  settings.PLAN_AGENCY_POSTS,
    }
    limit = plan_limits.get(plan, settings.PLAN_FREE_POSTS)

    supabase = get_supabase()
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    result = (
        supabase.table("posts")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("created_at", month_start)
        .execute()
    )
    used = result.count or 0
    logger.info("WA plan limit check | user_id=%s | plan=%s | used=%d | limit=%d", user_id, plan, used, limit)
    return used < limit


# ── Main entry points ──────────────────────────────────────────────────────────

async def handle_wa_message(from_phone: str, message: dict) -> None:
    """
    Route an incoming WhatsApp message.
    Called from webhooks.py after HMAC verification and idempotency check.
    """
    msg_type = message.get("type", "")
    logger.info("WA handle_wa_message | phone=%s | type=%s", from_phone, msg_type)

    session = _get_session(from_phone)
    lang    = session.get("lang", "hi")
    state   = session.get("state", "IDLE")

    try:
        if msg_type == "image":
            await _handle_photo(from_phone, message, session)
        elif msg_type == "text":
            text = message.get("text", {}).get("body", "").strip()
            logger.info("WA text | phone=%s | text=%r | state=%s", from_phone, text[:50], state)
            if text.lower() in ("hi", "hello", "start", "/start", "नमस्ते", "help"):
                await _handle_start(from_phone, session)
            elif state == "AWAIT_PRODUCT_NAME":
                await _handle_product_name_input(from_phone, text, session)
            else:
                await _handle_start(from_phone, session)
        elif msg_type == "interactive":
            # Button tap from approve/discard
            button_reply = message.get("interactive", {}).get("button_reply", {})
            button_id    = button_reply.get("id", "")
            logger.info("WA button | phone=%s | button_id=%s", from_phone, button_id)
            await _handle_button(from_phone, button_id, session)
        else:
            logger.info("WA unhandled type | phone=%s | type=%s", from_phone, msg_type)
    except Exception as e:
        logger.error("WA message handler error | phone=%s | error=%s", from_phone, e, exc_info=True)
        await send_wa_text(from_phone, "❌ An error occurred. Please try again in a moment.")


async def handle_wa_status_update(status_update: dict) -> None:
    """Handle delivery/read receipts — just log them, no user action needed."""
    status = status_update.get("status", "")
    msg_id = status_update.get("id", "")
    logger.debug("WA status update | msg_id=%s | status=%s", msg_id, status)


# ── FSM handlers ──────────────────────────────────────────────────────────────

async def _handle_start(phone: str, session: dict) -> None:
    """Send welcome message. If user not registered, send registration link."""
    user = _lookup_user_by_phone(phone)
    logger.info("WA _handle_start | phone=%s | user_found=%s", phone, bool(user))
    if not user:
        await send_wa_text(
            phone,
            _t("en", "not_registered").format(url=settings.FRONTEND_URL),
        )
        return

    lang = user.get("language", "hi")
    session["lang"] = lang
    _save_session(phone, session)
    await send_wa_text(phone, _t(lang, "welcome"))


async def _handle_photo(phone: str, message: dict, session: dict) -> None:
    """
    Handle an incoming photo:
    1. Look up user by phone
    2. Check plan limit
    3. Download media from Meta
    4. If caption provided → use as product name
    5. If no caption → ask for product name (FSM)
    6. Save post to DB + trigger Celery
    """
    user = _lookup_user_by_phone(phone)
    if not user:
        await send_wa_text(
            phone,
            _t("en", "not_registered").format(url=settings.FRONTEND_URL),
        )
        return

    lang    = user.get("language", "hi")
    user_id = user["id"]
    plan    = user.get("plan", "free")

    # Plan limit check
    if not _check_plan_limit(user_id, plan):
        await send_wa_text(phone, _t(lang, "plan_limit").format(url=settings.FRONTEND_URL))
        return

    # Instagram connectivity check
    from app.utils.crypto import decrypt_token
    ig_token = user.get("instagram_token")
    if ig_token:
        try:
            ig_token = decrypt_token(ig_token)
        except Exception:
            ig_token = None
    if not ig_token:
        await send_wa_text(phone, _t(lang, "no_instagram").format(url=settings.FRONTEND_URL))
        return

    # Get photo info
    image_obj = message.get("image", {})
    media_id  = image_obj.get("id")
    caption   = image_obj.get("caption", "").strip()

    if not media_id:
        await send_wa_text(phone, "❌ Could not retrieve photo. Please try again.")
        return

    # Download media IMMEDIATELY (expires in ~5 min)
    await send_wa_text(phone, _t(lang, "processing"))
    try:
        photo_bytes = await download_wa_media(media_id)
    except Exception as e:
        logger.error("WA media download failed | phone=%s | media_id=%s | error=%s", phone, media_id, e)
        await send_wa_text(phone, "❌ Could not download your photo. Please try again.")
        return

    # Upload to Supabase Storage
    supabase  = get_supabase()
    post_id   = str(uuid.uuid4())
    filename  = f"posts/{user_id}/{post_id}_original.jpg"
    try:
        supabase.storage.from_("post-photos").upload(
            path=filename,
            file=photo_bytes,
            file_options={"content-type": "image/jpeg"},
        )
        original_url = supabase.storage.from_("post-photos").get_public_url(filename)
    except Exception as e:
        logger.error("WA Supabase upload failed | post_id=%s | error=%s", post_id, e)
        await send_wa_text(phone, "❌ Storage error. Please try again.")
        return

    # If caption provided, use as product name and start pipeline immediately
    if caption:
        await _launch_pipeline(
            phone=phone,
            user=user,
            post_id=post_id,
            original_url=original_url,
            product_name=caption,
            session=session,
        )
    else:
        # Ask for product name
        session["state"]   = "AWAIT_PRODUCT_NAME"
        session["context"] = {
            "post_id":      post_id,
            "original_url": original_url,
            "lang":         lang,
        }
        session["lang"] = lang
        _save_session(phone, session)
        await send_wa_text(phone, _t(lang, "ask_product_name"))


async def _handle_product_name_input(phone: str, text: str, session: dict) -> None:
    """User replied with product name after being asked."""
    ctx      = session.get("context", {})
    post_id  = ctx.get("post_id")
    orig_url = ctx.get("original_url")

    if not post_id or not orig_url:
        # Lost session context, restart
        _clear_session(phone)
        await send_wa_text(phone, "❌ Session expired. Please send your photo again.")
        return

    user = _lookup_user_by_phone(phone)
    if not user:
        _clear_session(phone)
        return

    await send_wa_text(phone, _t(user.get("language", "hi"), "processing"))
    await _launch_pipeline(
        phone=phone,
        user=user,
        post_id=post_id,
        original_url=orig_url,
        product_name=text,
        session=session,
    )


async def _handle_button(phone: str, button_id: str, session: dict) -> None:
    """
    Handle approve/discard button tap from the preview message.
    button_id format: "approve:{post_id}:{enhancement_type}" or "discard:{post_id}"
    """
    parts = button_id.split(":")
    action = parts[0] if parts else ""

    if action == "discard":
        post_id = parts[1] if len(parts) > 1 else ""
        if post_id:
            supabase = get_supabase()
            supabase.table("posts").update({"status": "discarded"}).eq("id", post_id).execute()
        _clear_session(phone)
        lang = session.get("lang", "hi")
        await send_wa_text(phone, _t(lang, "discard"))
        return

    if action == "approve":
        post_id           = parts[1] if len(parts) > 1 else ""
        enhancement_type  = parts[2] if len(parts) > 2 else "enhanced"
        lang              = session.get("lang", "hi")

        if not post_id:
            await send_wa_text(phone, "❌ Invalid action. Please start again.")
            return

        await send_wa_text(phone, _t(lang, "approved_posting"))

        # Trigger Instagram post via worker
        try:
            from app.workers.whatsapp_worker import post_approved_wa_task
            post_approved_wa_task.delay(
                post_id=post_id,
                phone=phone,
                enhancement_type=enhancement_type,
                lang=lang,
            )
        except Exception as e:
            logger.error("WA approved post task failed | post_id=%s | error=%s", post_id, e)
            await send_wa_text(phone, _t(lang, "post_failed"))

        _clear_session(phone)


# ── Pipeline launcher ──────────────────────────────────────────────────────────

async def _launch_pipeline(
    phone: str,
    user: dict,
    post_id: str,
    original_url: str,
    product_name: str,
    session: dict,
    is_enhanced: bool = True,
    is_carousel_duo: bool = False,
) -> None:
    """
    Create the post record in DB and dispatch Celery task for AI processing.
    On completion the WA worker sends back preview + approval buttons.
    """
    supabase  = get_supabase()
    user_id   = user["id"]
    lang      = user.get("language", "hi")

    # 1. Create post record
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("posts").insert({
        "id":                post_id,
        "user_id":           user_id,
        "original_photo_url": original_url,
        "product_name":      product_name,
        "product_type":      "other",
        "status":            "processing",
        "source":            "whatsapp",
        "created_at":        now,
    }).execute()

    # 2. Update session to AWAIT_APPROVAL
    session["state"]   = "AWAIT_APPROVAL"
    session["context"] = {"post_id": post_id}
    session["lang"]    = lang
    _save_session(phone, session)

    # 3. Dispatch Celery worker
    try:
        from app.workers.whatsapp_worker import process_wa_photo_task
        process_wa_photo_task.delay(
            post_id=post_id,
            user_id=user_id,
            phone=phone,
            original_photo_url=original_url,
            product_name=product_name,
            product_type="other",
            language=lang,
            additional_info="",
            is_enhanced=is_enhanced,
            is_carousel_duo=is_carousel_duo,
        )
        logger.info("WA pipeline dispatched | post_id=%s | user_id=%s", post_id, user_id)
    except Exception as e:
        logger.error("WA Celery dispatch failed | post_id=%s | error=%s", post_id, e, exc_info=True)
        # Process inline as fallback (no queue)
        logger.info("WA fallback: processing inline | post_id=%s", post_id)
        await _process_inline_fallback(
            phone=phone, user=user, post_id=post_id,
            original_url=original_url, product_name=product_name,
            lang=lang, is_enhanced=is_enhanced,
        )


async def _process_inline_fallback(
    phone: str, user: dict, post_id: str,
    original_url: str, product_name: str,
    lang: str, is_enhanced: bool,
) -> None:
    """
    Fallback when Celery is unavailable: run AI pipeline synchronously.
    This is slower but ensures the seller still gets their post processed.
    """
    import asyncio
    from app.workers.photo_worker import _process_photo_async
    try:
        await _process_photo_async(
            post_id=post_id,
            user_id=user["id"],
            telegram_id=None,
            original_photo_url=original_url,
            product_name=product_name,
            product_type="other",
            language=lang,
            additional_info="",
            is_enhanced=is_enhanced,
            is_carousel_duo=False,
        )
        # Now send WA preview
        await _send_wa_preview(phone, post_id, lang)
    except Exception as e:
        logger.error("WA inline fallback failed | post_id=%s | error=%s", post_id, e)
        await send_wa_text(phone, "❌ Processing failed. Please try again.")


async def _send_wa_preview(phone: str, post_id: str, lang: str) -> None:
    """Send approved photo preview + approve/discard buttons."""
    supabase = get_supabase()
    result   = supabase.table("posts").select("*").eq("id", post_id).single().execute()
    if not result.data:
        await send_wa_text(phone, "❌ Post not found. Please try again.")
        return

    post         = result.data
    edited_url   = post.get("edited_photo_url")
    original_url = post.get("original_photo_url")
    caption_hi   = post.get("caption_hindi", "")[:500]
    caption_en   = post.get("caption_english", "")[:500]
    hashtags     = " ".join(post.get("hashtags", [])[:10])
    caption_text = f"{caption_hi}\n\n{caption_en}\n\n{hashtags}"

    # Send enhanced preview
    if edited_url:
        await send_wa_image(phone, edited_url, caption="✨ Enhanced Preview")

    # Send original too
    if original_url:
        await send_wa_image(phone, original_url, caption="🖼 Original Preview")

    # Send caption preview
    preview_text = (
        f"📝 *Generated Caption Preview:*\n\n{caption_text[:500]}\n\n"
        f"{'─'*20}\n"
        f"{_t(lang, 'ask_enhancement')}"
    )
    await send_wa_buttons(
        to=phone,
        body=preview_text[:1024],
        buttons=[
            {"id": f"approve:{post_id}:enhanced", "title": _t(lang, "btn_enhanced")},
            {"id": f"approve:{post_id}:original", "title": _t(lang, "btn_original")},
            {"id": f"discard:{post_id}",           "title": _t(lang, "btn_discard")},
        ],
    )
