# backend/app/services/telegram_bot.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Enterprise Telegram Bot FSM (Finite State Machine)
# All conversational logic lives here; webhooks.py delegates to this module.
#
# State flow:
#   IDLE → AWAITING_PHOTO → AWAITING_PRODUCT_NAME → AWAITING_SCHEDULE → DONE
#
# Sessions are stored in Redis (TTL 1 hour). Falls back gracefully if Redis is
# unavailable (stateless mode — commands still work, multi-step flows won't).
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import logging
from typing import Any

import redis as _redis

from app.config import settings
from app.db.supabase import get_supabase
from app.middleware.plan_check import get_quota_info

logger = logging.getLogger(__name__)

# ── Redis session management ──────────────────────────────────────────────────
SESSION_TTL = 3600   # 1 hour
_redis_client: _redis.Redis | None = None


def _get_redis() -> _redis.Redis | None:
    """Get SSL-correct Redis client via centralized helper."""
    from app.db.redis_client import get_redis
    return get_redis()



def _get_session(telegram_id: int) -> dict:
    r = _get_redis()
    if r is None:
        return {"state": "IDLE", "context": {}, "lang": "hi"}
    raw = r.get(f"tg_session:{telegram_id}")
    if raw:
        return json.loads(raw)
    return {"state": "IDLE", "context": {}, "lang": "hi"}


def _save_session(telegram_id: int, session: dict) -> None:
    r = _get_redis()
    if r is None:
        return
    r.setex(f"tg_session:{telegram_id}", SESSION_TTL, json.dumps(session))


def _clear_session(telegram_id: int) -> None:
    r = _get_redis()
    if r is None:
        return
    r.delete(f"tg_session:{telegram_id}")


# ── Localisation helpers ──────────────────────────────────────────────────────

def _t(lang: str, key: str) -> str:
    """Simple inline translation lookup."""
    strings: dict[str, dict[str, str]] = {
        "hi": {
            "welcome": (
                "🙏 *नमस्ते! मैं आपका InstaAgent हूँ।*\n\n"
                "📸 कोई भी product photo भेजें — मैं 12 seconds में:\n\n"
                "✅ Background remove करूँगा\n"
                "✅ Photo professional बनाऊँगा\n"
                "✅ Hindi + English caption लिखूँगा\n"
                "✅ 20 hashtags suggest करूँगा\n"
                "✅ Instagram पर post करूँगा\n\n"
                "💡 *Pro Tip:* आप WhatsApp से सीधे यहाँ photo forward भी कर सकते हैं! 📲\n\n"
                "बस photo भेजो — शुरू करते हैं! 🚀"
            ),
            "help": (
                "📋 *Commands (Hindi/English दोनों काम करते हैं):*\n\n"
                "📸 *Photo भेजें* — AI processing शुरू\n"
                "*/posts* — आपके recent posts\n"
                "*/stats* — Instagram analytics\n"
                "*/schedule* — Auto-post time set करें\n"
                "*/connect* — Instagram जोड़ें\n"
                "*/language* — Hindi ↔ English switch\n"
                "*/cancel* — वर्तमान action रद्द करें\n\n"
                "🆘 Support: Dashboard पर जाएं"
            ),
            "guidelines": (
                "🛡️ *InstaAgent Authenticity Guide:*\n\n"
                "• *Enhancements:* Professional look के लिए अच्छे हैं।\n"
                "• *Authenticity:* Returns कम करने के लिए असली photo भी ज़रूरी है।\n"
                "💡 *Tip:* दोनों (Carousel) post करें ताकि ग्राहक को 'Studio' और 'Real' दोनों look मिलें!"
            ),
            "ask_enhancement": "✨ आप अपनी photo कैसे post करना चाहेंगे?",
            "preview_text": "📸 *Preview:* 'Enhanced' vs 'Original'. आपको कौनसा पसंद है?",
            "approved": "✅ Post approve कर दिया गया है!",
            "not_registered": (
                "❌ आपका account नहीं मिला।\n\n"
                "कृपया पहले यहाँ register करें:\n{url}"
            ),
            "ask_product_name": (
                "📝 Product का नाम बताएं (Hindi या English में):\n\n"
                "Example: *सोने की चूड़ी*, *Cotton Suit*, *Diya Set*"
            ),
            "processing": (
                "📸 Photo मिली! AI processing शुरू हो रही है...\n\n"
                "⏳ *~12 seconds* में तैयार होगा:\n"
                "✅ Background remove\n"
                "✅ Photo enhance\n"
                "✅ Caption generate\n"
                "✅ 20 Hashtags\n\n"
                "रुकें... 🔄"
            ),
            "no_instagram": (
                "⚠️ Instagram connect नहीं है।\n\n"
                "*/connect* command से जोड़ें।"
            ),
            "cancelled": "❌ Action रद्द किया।",
            "schedule_ask": (
                "⏰ *Auto-post time set करें*\n\n"
                "Format: `HH:MM` (24-hour IST)\n"
                "Example: `19:00` (7pm), `08:30` (8:30am)\n\n"
                "Type the time or /cancel:"
            ),
            "schedule_saved": "✅ Auto-post time set: *{time}* IST",
            "lang_switched": "✅ Language changed to *English*. Type /language to switch back.",
            "select_lang": "🌐 कृपया अपनी पसंदीदा भाषा चुनें / Please select your preferred language:",
        },
        "en": {
            "welcome": (
                "👋 *Welcome to InstaAgent!*\n\n"
                "📸 Send any product photo and I'll:\n\n"
                "✅ Remove the background\n"
                "✅ Enhance the photo professionally\n"
                "✅ Write Hindi + English captions\n"
                "✅ Suggest 20 hashtags\n"
                "✅ Post to Instagram\n\n"
                "💡 *Pro Tip:* You can forward photos directly from WhatsApp to this bot! 📲\n\n"
                "Just send a photo to get started! 🚀"
            ),
            "help": (
                "📋 *Available Commands:*\n\n"
                "📸 *Send a photo* — start AI processing\n"
                "*/posts* — view recent posts\n"
                "*/stats* — Instagram analytics\n"
                "*/schedule* — set auto-post time\n"
                "*/connect* — connect Instagram\n"
                "*/language* — switch to Hindi\n"
                "*/cancel* — cancel current action\n\n"
                "🆘 Support: visit your dashboard"
            ),
            "guidelines": (
                "🛡️ *InstaAgent Authenticity Guide:*\n\n"
                "• *Enhancements:* Great for a professional studio look.\n"
                "• *Authenticity:* Real photos build trust and reduce returns.\n"
                "💡 *Tip:* Try 'Both (Carousel)' to show customers the shoppable glow AND the real product!"
            ),
            "ask_enhancement": "✨ How would you like to post this photo?",
            "preview_text": "📸 *Preview:* 'Enhanced' vs 'Original'. Which one do you prefer?",
            "approved": "✅ Post approved!",
            "not_registered": (
                "❌ Your account was not found.\n\n"
                "Please register first at:\n{url}"
            ),
            "ask_product_name": (
                "📝 What is the product name?\n\n"
                "Example: *Gold Bangles*, *Cotton Suit*, *Diya Set*"
            ),
            "processing": (
                "📸 Photo received! AI processing started...\n\n"
                "⏳ Ready in *~12 seconds:*\n"
                "✅ Background removal\n"
                "✅ Photo enhancement\n"
                "✅ Caption generation\n"
                "✅ 20 Hashtags\n\n"
                "Please wait... 🔄"
            ),
            "no_instagram": (
                "⚠️ Instagram is not connected.\n\n"
                "Use */connect* to link your account."
            ),
            "cancelled": "❌ Action cancelled.",
            "schedule_ask": (
                "⏰ *Set Auto-Post Time*\n\n"
                "Format: `HH:MM` (24-hour IST)\n"
                "Example: `19:00` (7pm), `08:30` (8:30am)\n\n"
                "Type the time or /cancel:"
            ),
            "schedule_saved": "✅ Auto-post time set to *{time}* IST",
            "lang_switched": "✅ भाषा *Hindi* में बदल गई। वापस बदलने के लिए /language टाइप करें।",
        },
    }
    return strings.get(lang, strings["hi"]).get(key, key)


# ═══════════════════════════════════════════════════════════════════════════════
# Public Entry Points — called by webhooks.py
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_message(telegram_id: int, message: dict) -> None:
    """Route an incoming Telegram message to the correct handler."""
    session = _get_session(telegram_id)
    lang    = session.get("lang", "hi")
    state   = session.get("state", "IDLE")

    if "photo" in message:
        await _handle_photo(telegram_id, message, session)
    elif "text" in message:
        text = message["text"].strip()
        # Commands always take priority over FSM state
        if text.startswith("/") or text.upper() in (
            "START", "HELP", "POSTS", "STATS", "SCHEDULE", "CONNECT", "LANGUAGE", "CANCEL"
        ):
            await _handle_command(telegram_id, text, session)
        else:
            await _handle_fsm_text(telegram_id, text, session)
    # Ignore stickers, gifs, etc.


async def handle_callback_query(callback_query: dict) -> None:
    """Route inline button presses."""
    from app.services.telegram_service import answer_callback_query

    qid        = callback_query["id"]
    data       = callback_query.get("data", "")
    telegram_id = callback_query["from"]["id"]
    session    = _get_session(telegram_id)

    await answer_callback_query(qid, "Processing...")
    await _dispatch_callback(telegram_id, data, session)


# ═══════════════════════════════════════════════════════════════════════════════
# Command Handlers
# ═══════════════════════════════════════════════════════════════════════════════

async def _handle_command(telegram_id: int, text: str, session: dict) -> None:
    from app.services.telegram_service import send_message, send_inline_keyboard

    lang = session.get("lang", "hi")
    cmd  = text.split()[0].lstrip("/").upper()

    if cmd in ("START", "START@INSTAAGENTBOT"):
        _clear_session(telegram_id)
        user = await _get_user_by_telegram(telegram_id)
        if not user:
            await send_message(telegram_id, _t(lang, "not_registered").format(
                url=settings.FRONTEND_URL
            ))
            return
        new_session = {"state": "IDLE", "context": {}, "lang": session.get("lang", "hi")}
        _save_session(telegram_id, new_session)
        await send_message(telegram_id, _t(lang, "welcome"))

    elif cmd in ("HELP",):
        await send_message(telegram_id, _t(lang, "help"))

    elif cmd in ("CANCEL",):
        _clear_session(telegram_id)
        await send_message(telegram_id, _t(lang, "cancelled"))

    elif cmd in ("LANGUAGE",):
        new_lang = "en" if lang == "hi" else "hi"
        session["lang"] = new_lang
        _save_session(telegram_id, session)
        await send_message(telegram_id, _t(lang, "lang_switched"))

    elif cmd in ("CONNECT",):
        await _cmd_connect(telegram_id, session)

    elif cmd in ("POSTS",):
        await _cmd_posts(telegram_id, session)

    elif cmd in ("STATS",):
        await _cmd_stats(telegram_id, session)

    elif cmd in ("SCHEDULE",):
        session["state"] = "AWAITING_SCHEDULE"
        _save_session(telegram_id, session)
        await send_message(telegram_id, _t(lang, "schedule_ask"))

    else:
        await send_message(telegram_id,
            "❓ Unknown command. Type */help* for a list of commands.",
            parse_mode="Markdown",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Photo Handler
# ═══════════════════════════════════════════════════════════════════════════════

async def _handle_photo(telegram_id: int, message: dict, session: dict) -> None:
    from app.services.telegram_service import send_message, download_file
    from app.workers.photo_worker import process_photo_task
    import uuid

    lang = session.get("lang", "hi")
    supabase = get_supabase()

    user = await _get_user_by_telegram(telegram_id)
    if not user:
        await send_message(telegram_id, _t(lang, "not_registered").format(
            url=settings.FRONTEND_URL
        ))
        return

    # Download largest photo variant
    photo   = message["photo"][-1]
    caption = message.get("caption", "").strip()

    # Acknowledge immediately
    await send_message(telegram_id, _t(lang, "processing"))

    # Quota check warning
    quota = await get_quota_info(user["id"], user.get("plan", "free"))
    if quota["warning"]:
        warn_msg = (
            f"⚡ *Quick Tip:* You only have {quota['remaining']} free posts left this month. "
            "Upgrade your plan at dashboard to keep posting limitless!"
            if lang == "en" else
            f"⚡ *जरूरी जानकारी:* इस महीने के आपके सिर्फ {quota['remaining']} free posts बचे हैं। "
            "ज्यादा पोस्ट करने के लिए अपना plan upgrade करें!"
        )
        await send_message(telegram_id, warn_msg)

    try:
        photo_bytes = await download_file(photo["file_id"])
    except Exception as e:
        logger.error("Failed to download Telegram photo: %s", e)
        await send_message(telegram_id, "❌ Photo download failed. Please try again.")
        return

    post_id  = str(uuid.uuid4())
    user_id  = user["id"]
    filename = f"posts/{user_id}/{post_id}_original.jpg"

    supabase.storage.from_("post-photos").upload(
        path=filename,
        file=photo_bytes,
        file_options={"content-type": "image/jpeg"},
    )
    original_url = supabase.storage.from_("post-photos").get_public_url(filename)

    product_name = caption if caption else "Product"

    supabase.table("posts").insert({
        "id":                post_id,
        "user_id":           user_id,
        "original_photo_url": original_url,
        "product_name":      product_name,
        "product_type":      "other",
        "status":            "processing",
        "source":            "telegram",
    }).execute()

    if not caption:
        # Ask for product name before kicking off pipeline
        session["state"]   = "AWAITING_PRODUCT_NAME"
        session["context"] = {
            "post_id":      post_id,
            "original_url": original_url,
            "user_id":      user_id,
        }
        _save_session(telegram_id, session)
        await send_message(telegram_id, _t(lang, "ask_product_name"))
        return

    # We have the name — fire off pipeline immediately
    _queue_processing(post_id, user_id, telegram_id, original_url, product_name, user)
    _clear_session(telegram_id)


def _queue_processing(
    post_id: str,
    user_id: str,
    telegram_id: int,
    original_url: str,
    product_name: str,
    user: dict,
) -> None:
    from app.workers.photo_worker import process_photo_task
    process_photo_task.delay(
        post_id=post_id,
        user_id=user_id,
        telegram_id=telegram_id,
        original_photo_url=original_url,
        product_name=product_name,
        product_type="other",
        language=user.get("language", "hi"),
        additional_info="",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# FSM Text Handler (non-command text depending on state)
# ═══════════════════════════════════════════════════════════════════════════════

async def _handle_fsm_text(telegram_id: int, text: str, session: dict) -> None:
    from app.services.telegram_service import send_message

    lang  = session.get("lang", "hi")
    state = session.get("state", "IDLE")
    ctx   = session.get("context", {})

    if state == "AWAITING_PRODUCT_NAME":
        product_name = text.strip()
        post_id      = ctx.get("post_id")
        original_url = ctx.get("original_url")
        user_id      = ctx.get("user_id")

        supabase = get_supabase()
        supabase.table("posts").update({"product_name": product_name}).eq("id", post_id).execute()

        user_r = supabase.table("users").select("*").eq("id", user_id).single().execute()
        user   = user_r.data or {}

        _queue_processing(post_id, user_id, telegram_id, original_url, product_name, user)
        _clear_session(telegram_id)
        await send_message(
            telegram_id,
            f"✅ *{product_name}* — processing शुरू!\n\nTelegram पर notification आएगी।",
        )

    elif state == "AWAITING_SCHEDULE":
        import re
        match = re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", text.strip())
        if not match:
            await send_message(
                telegram_id,
                "❌ Invalid format. Please use HH:MM (e.g. `19:00`)",
                parse_mode="Markdown",
            )
            return

        time_str = text.strip()
        supabase = get_supabase()
        user = await _get_user_by_telegram(telegram_id)
        if user:
            supabase.table("users").update(
                {"preferred_post_time": time_str}
            ).eq("id", user["id"]).execute()

        _clear_session(telegram_id)
        await send_message(telegram_id, _t(lang, "schedule_saved").format(time=time_str))

    else:
        # Generic nudge
        await send_message(
            telegram_id,
            "📸 Photo भेजें या */help* type करें।" if lang == "hi"
            else "📸 Send a photo or type */help* to see commands.",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Inline Button Callback Dispatcher
# ═══════════════════════════════════════════════════════════════════════════════

async def _dispatch_callback(telegram_id: int, data: str, session: dict) -> None:
    from app.services.telegram_service import send_message

    if data.startswith("post_now:"):
        post_id = data.split(":", 1)[1]
        await _cb_post_now(telegram_id, post_id, session)

    elif data.startswith("schedule:"):
        post_id = data.split(":", 1)[1]
        session["state"]   = "AWAITING_SCHEDULE_POST"
        session["context"] = {"post_id": post_id}
        _save_session(telegram_id, session)
        lang = session.get("lang", "hi")
        await send_message(telegram_id, _t(lang, "schedule_ask"))

    elif data.startswith("view_stats:"):
        post_id = data.split(":", 1)[1]
        await _cb_view_post_stats(telegram_id, post_id, session)

    elif data.startswith("discard:"):
        post_id = data.split(":", 1)[1]
        supabase = get_supabase()
        supabase.table("posts").update({"status": "discarded"}).eq("id", post_id).execute()
        lang = session.get("lang", "hi")
        await send_message(telegram_id, "🗑️ Post discarded." if lang == "en" else "🗑️ Post हटा दिया।")

    elif data.startswith("approve:"):
        # approve:post_id:choice
        _, post_id, choice = data.split(":")
        await _cb_approve_choice(telegram_id, post_id, choice, session)

    else:
        await send_message(telegram_id, "⚠️ Unknown action. Please try again.")


async def _cb_approve_choice(telegram_id: int, post_id: str, choice: str, session: dict) -> None:
    from app.services.telegram_service import send_inline_keyboard, send_message
    
    lang = session.get("lang", "hi")
    supabase = get_supabase()
    
    # 1. Update post based on choice
    update_data: dict[str, Any] = {"status": "ready"}
    
    if choice == "original":
        # User wants the raw version as the main photo
        result = supabase.table("posts").select("original_photo_url").eq("id", post_id).single().execute()
        if result.data:
            update_data["edited_photo_url"] = result.data["original_photo_url"]
            update_data["is_enhanced"] = False
            
    elif choice == "enhanced":
        update_data["is_enhanced"] = True
        
    elif choice == "both":
        update_data["is_carousel_duo"] = True
        # For 'both', we assume worker uploaded 'original' as secondary

    supabase.table("posts").update(update_data).eq("id", post_id).execute()
    
    # 2. Show final approval + Post/Schedule buttons
    await send_message(telegram_id, _t(lang, "approved"))
    
    post_res = supabase.table("posts").select("product_name").eq("id", post_id).single().execute()
    product_name = post_res.data.get("product_name", "Product") if post_res.data else "Product"

    buttons = [
        [{"text": "🚀 POST NOW", "callback_data": f"post_now:{post_id}"}],
        [{"text": "⏰ SCHEDULE", "callback_data": f"schedule:{post_id}"}],
        [{"text": "🗑️ DISCARD",  "callback_data": f"discard:{post_id}"}]
    ]
    
    await send_inline_keyboard(
        telegram_id,
        f"✅ *{product_name}* is ready! Choose action:",
        buttons=buttons
    )


async def _cb_post_now(telegram_id: int, post_id: str, session: dict) -> None:
    from app.services.telegram_service import send_message
    from app.workers.post_worker import _publish_single_post

    supabase = get_supabase()
    result = supabase.table("posts").select(
        "*, users(instagram_token, instagram_id, telegram_id)"
    ).eq("id", post_id).single().execute()

    if not result.data:
        await send_message(telegram_id, "❌ Post not found. Please check your dashboard.")
        return

    lang = session.get("lang", "hi")
    await send_message(
        telegram_id,
        "⏳ Posting to Instagram..." if lang == "en" else "⏳ Instagram पर post हो रहा है..."
    )
    await _publish_single_post(supabase, result.data)


async def _cb_view_post_stats(telegram_id: int, post_id: str, session: dict) -> None:
    from app.services.telegram_service import send_message
    from app.services.analytics_service import get_post_stats_for_telegram

    try:
        msg = await get_post_stats_for_telegram(post_id)
        await send_message(telegram_id, msg)
    except Exception as e:
        logger.error("Failed to fetch post stats: %s", e)
        await send_message(telegram_id, "❌ Could not fetch stats. Try again later.")


# ═══════════════════════════════════════════════════════════════════════════════
# Command Implementations
# ═══════════════════════════════════════════════════════════════════════════════

async def _cmd_connect(telegram_id: int, session: dict) -> None:
    from app.services.telegram_service import send_inline_keyboard

    lang = session.get("lang", "hi")
    connect_url = f"{settings.FRONTEND_URL}/settings?action=connect-instagram"
    text = (
        "🔗 *अपना Instagram account जोड़ें:*\n\nनीचे button दबाएं और browser में authorize करें।"
        if lang == "hi" else
        "🔗 *Connect your Instagram account:*\n\nTap the button below and authorize in browser."
    )
    await send_inline_keyboard(
        telegram_id,
        text,
        buttons=[[{"text": "🔗 Connect Instagram", "url": connect_url}]],
    )


async def _cmd_posts(telegram_id: int, session: dict) -> None:
    from app.services.telegram_service import send_message, send_inline_keyboard

    lang = session.get("lang", "hi")
    supabase = get_supabase()
    user = await _get_user_by_telegram(telegram_id)
    if not user:
        await send_message(telegram_id, _t(lang, "not_registered").format(url=settings.FRONTEND_URL))
        return

    result = (
        supabase.table("posts")
        .select("id, product_name, status, created_at, instagram_permalink")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )

    posts = result.data or []
    if not posts:
        await send_message(
            telegram_id,
            "📭 कोई post नहीं मिला।\n\nPhoto भेजें!" if lang == "hi"
            else "📭 No posts found.\n\nSend a photo to get started!"
        )
        return

    STATUS_EMOJI = {
        "processing": "🔄", "ready": "✅", "scheduled": "⏰",
        "posted": "📤", "failed": "❌", "discarded": "🗑️",
    }
    lines = ["📋 *Your Recent Posts:*\n"]
    for p in posts:
        emoji = STATUS_EMOJI.get(p["status"], "❓")
        name  = p.get("product_name", "Unknown")
        date  = p.get("created_at", "")[:10]
        link  = f" | [View]({p['instagram_permalink']})" if p.get("instagram_permalink") else ""
        lines.append(f"{emoji} *{name}* — {p['status']} ({date}){link}")

    await send_message(telegram_id, "\n".join(lines))


async def _cmd_stats(telegram_id: int, session: dict) -> None:
    from app.services.telegram_service import send_message
    from app.services.analytics_service import get_dashboard_stats_for_telegram

    lang = session.get("lang", "hi")
    user = await _get_user_by_telegram(telegram_id)
    if not user:
        await send_message(telegram_id, _t(lang, "not_registered").format(url=settings.FRONTEND_URL))
        return

    if not user.get("instagram_token"):
        await send_message(telegram_id, _t(lang, "no_instagram"))
        return

    await send_message(
        telegram_id,
        "📊 Analytics fetch हो रही है..." if lang == "hi" else "📊 Fetching your analytics..."
    )

    try:
        msg = await get_dashboard_stats_for_telegram(user)
        await send_message(telegram_id, msg)
    except Exception as e:
        logger.error("Stats fetch failed: %s", e)
        await send_message(
            telegram_id,
            "❌ Analytics fetch नहीं हो सकी। Dashboard पर check करें।" if lang == "hi"
            else "❌ Could not fetch analytics. Please check your dashboard."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Admin Commands (gated by ADMIN_TELEGRAM_ID)
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_admin_command(telegram_id: int, text: str) -> None:
    """Handle admin-only commands — called after admin ID is confirmed by webhooks.py."""
    from app.services.telegram_service import send_message

    parts = text.strip().split(maxsplit=1)
    cmd   = parts[0].lstrip("/").upper()
    arg   = parts[1] if len(parts) > 1 else ""

    if cmd == "BROADCAST":
        if not arg:
            await send_message(telegram_id, "Usage: /broadcast <message>")
            return
        from app.workers.telegram_broadcast import broadcast_to_all_users_task
        broadcast_to_all_users_task.delay(message=arg)
        await send_message(telegram_id, f"✅ Broadcast queued for all active users.\nMessage: _{arg[:100]}_")

    elif cmd == "USERSTATS":
        supabase = get_supabase()
        total   = supabase.table("users").select("id", count="exact").execute()
        active  = supabase.table("users").select("id", count="exact").neq("plan", "free").execute()
        await send_message(
            telegram_id,
            f"📊 *Admin Stats*\n\n"
            f"👥 Total users: `{total.count}`\n"
            f"💎 Paid users: `{active.count}`\n"
            f"🆓 Free users: `{(total.count or 0) - (active.count or 0)}`",
        )
    else:
        await send_message(telegram_id, "Unknown admin command.")


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

async def _get_user_by_telegram(telegram_id: int) -> dict | None:
    """Fetch user from DB by telegram_id. Returns None if not found."""
    supabase = get_supabase()
    result = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
    return result.data[0] if result.data else None
