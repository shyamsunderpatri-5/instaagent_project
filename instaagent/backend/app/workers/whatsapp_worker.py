# backend/app/workers/whatsapp_worker.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Celery Workers for WhatsApp Pipeline
#
# Two tasks:
#   1. process_wa_photo_task   — AI pipeline (bg-remove→enhance→caption)
#                                then sends WA preview + buttons
#   2. post_approved_wa_task   — Posts the approved photo to Instagram
#                                then confirms on WhatsApp
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import logging

from app.workers.celery_app import celery_app
from app.db.supabase import get_supabase

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, name="wa.process_photo")
def process_wa_photo_task(
    self,
    post_id: str,
    user_id: str,
    phone: str,
    original_photo_url: str,
    product_name: str,
    product_type: str,
    language: str,
    additional_info: str,
    is_enhanced: bool = True,
    is_carousel_duo: bool = False,
):
    """
    Celery task: Run the full AI photo pipeline for a WhatsApp photo.

    Steps:
    1. Download photo from Supabase Storage
    2. Remove background (Remove.bg)
    3. Enhance (Photoroom)
    4. Claude Vision analysis
    5. Generate caption (Hindi + English)
    6. Upload edited photo to Supabase Storage
    7. Update post DB record → status='ready'
    8. Send preview + approve/discard buttons back to seller on WhatsApp
    """
    try:
        asyncio.run(_process_and_notify(
            post_id=post_id,
            user_id=user_id,
            phone=phone,
            original_photo_url=original_photo_url,
            product_name=product_name,
            product_type=product_type,
            language=language,
            additional_info=additional_info,
            is_enhanced=is_enhanced,
            is_carousel_duo=is_carousel_duo,
        ))
    except Exception as exc:
        logger.error("WA photo task failed | post_id=%s | error=%s", post_id, exc, exc_info=True)

        # Mark post as failed
        try:
            supabase = get_supabase()
            supabase.table("posts").update({
                "status":       "failed",
                "error_message": str(exc)[:500],
            }).eq("id", post_id).execute()
        except Exception:
            pass

        # Notify seller on WA
        try:
            asyncio.run(_send_wa_error(phone, language, product_name))
        except Exception:
            pass

        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@celery_app.task(bind=True, max_retries=2, default_retry_delay=15, name="wa.post_approved")
def post_approved_wa_task(
    self,
    post_id: str,
    phone: str,
    enhancement_type: str,
    lang: str,
):
    """
    Celery task: Post the approved photo to Instagram, then
    send success/failure confirmation back to seller on WhatsApp.

    enhancement_type: "enhanced" | "original" | "both"
    """
    try:
        asyncio.run(_post_to_instagram_and_confirm(
            post_id=post_id,
            phone=phone,
            enhancement_type=enhancement_type,
            lang=lang,
        ))
    except Exception as exc:
        logger.error("WA approved post task failed | post_id=%s | error=%s", post_id, exc, exc_info=True)
        try:
            asyncio.run(_notify_wa_post_failed(phone, lang))
        except Exception:
            pass
        raise self.retry(exc=exc)


# ─── Async implementation functions ──────────────────────────────────────────

async def _process_and_notify(
    post_id: str,
    user_id: str,
    phone: str,
    original_photo_url: str,
    product_name: str,
    product_type: str,
    language: str,
    additional_info: str,
    is_enhanced: bool,
    is_carousel_duo: bool,
):
    """Run AI pipeline and send WA preview."""
    # Reuse the existing photo pipeline (same as Telegram)
    from app.workers.photo_worker import _process_photo_async
    await _process_photo_async(
        post_id=post_id,
        user_id=user_id,
        telegram_id=None,      # Skip Telegram notification
        original_photo_url=original_photo_url,
        product_name=product_name,
        product_type=product_type,
        language=language,
        additional_info=additional_info,
        is_enhanced=is_enhanced,
        is_carousel_duo=is_carousel_duo,
    )

    # Send preview + buttons to seller on WhatsApp
    from app.services.whatsapp_bot import _send_wa_preview
    await _send_wa_preview(phone, post_id, language)


async def _post_to_instagram_and_confirm(
    post_id: str,
    phone: str,
    enhancement_type: str,
    lang: str,
):
    """Post to Instagram and notify seller on WhatsApp."""
    from app.services.whatsapp_service import send_wa_text
    from app.services.whatsapp_bot import _t

    supabase = get_supabase()

    # Load post + user
    post_result = (
        supabase.table("posts")
        .select("*, users(instagram_token, instagram_username, language)")
        .eq("id", post_id)
        .single()
        .execute()
    )
    if not post_result.data:
        await send_wa_text(phone, "❌ Post not found.")
        return

    post = post_result.data
    user = post.get("users", {})

    from app.utils.crypto import decrypt_token
    raw_token = user.get("instagram_token", "")
    try:
        ig_token = decrypt_token(raw_token) if raw_token else None
    except Exception:
        ig_token = None

    if not ig_token:
        await send_wa_text(phone, _t(lang, "no_instagram").format(url="http://localhost:3000"))
        return

    # Choose which photo URL to post
    if enhancement_type == "original":
        photo_url = post.get("original_photo_url")
    else:
        photo_url = post.get("edited_photo_url") or post.get("original_photo_url")

    # Build caption
    caption_hi = post.get("caption_hindi", "")
    caption_en = post.get("caption_english", "")
    hashtags   = " ".join(post.get("hashtags", [])[:20])

    if lang == "en":
        caption = f"{caption_en}\n\n{hashtags}"
    else:
        caption = f"{caption_hi}\n\n{caption_en}\n\n{hashtags}"

    # Post to Instagram
    from app.workers.photo_worker import _post_to_instagram_async
    ig_post_id = await _post_to_instagram_async(
        ig_token=ig_token,
        photo_url=photo_url,
        caption=caption,
        is_carousel=(enhancement_type == "both"),
        secondary_url=post.get("secondary_photo_url") if enhancement_type == "both" else None,
    )

    # Update DB
    now = __import__("datetime").datetime.utcnow().isoformat()
    supabase.table("posts").update({
        "status":          "posted",
        "instagram_post_id": ig_post_id,
        "posted_at":       now,
        "source":          "whatsapp",
    }).eq("id", post_id).execute()

    ig_username = user.get("instagram_username", "your_account")
    post_url    = f"https://www.instagram.com/{ig_username}/" if ig_username else "https://www.instagram.com/"

    await send_wa_text(
        phone,
        _t(lang, "posted_success").format(url=post_url),
    )
    logger.info("WA → Instagram post success | post_id=%s | ig_post_id=%s", post_id, ig_post_id)


async def _send_wa_error(phone: str, lang: str, product_name: str) -> None:
    from app.services.whatsapp_service import send_wa_text
    await send_wa_text(
        phone,
        f"❌ Sorry, processing failed for '{product_name}'. Please send the photo again.",
    )


async def _notify_wa_post_failed(phone: str, lang: str) -> None:
    from app.services.whatsapp_service import send_wa_text
    from app.services.whatsapp_bot import _t
    await send_wa_text(phone, _t(lang, "post_failed"))
