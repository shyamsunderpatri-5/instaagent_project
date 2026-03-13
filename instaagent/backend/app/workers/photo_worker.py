# backend/app/workers/photo_worker.py
# Celery Background Worker — Full photo-to-Instagram pipeline
# Triggered by: POST /api/v1/posts/create

import asyncio
import logging
from app.workers.celery_app import celery_app
from app.services.photo_service import full_photo_pipeline, image_to_base64
from app.services.caption_service import generate_caption, analyze_product_photo
from app.services.telegram_service import send_message, send_photo
import httpx
import time
from app.db.supabase import get_supabase

logger = logging.getLogger(__name__)


def _log(step: str, post_id: str, msg: str = "", error: bool = False):
    """Consistent step logger — visible in Celery terminal."""
    prefix = "❌" if error else "✅"
    line   = f"[PIPELINE] {prefix} [{step}] post={post_id} {msg}"
    if error:
        logger.error(line)
    else:
        logger.info(line)
    print(line, flush=True)   # Always visible in Celery worker terminal


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_photo_task(
    self,
    post_id: str,
    user_id: str,
    telegram_id: int,
    original_photo_url: str,
    product_name: str,
    product_type: str,
    language: str,
    additional_info: str,
    is_enhanced: bool = True,
    is_carousel_duo: bool = False,
):
    try:
        asyncio.run(_process_photo_async(
            post_id=post_id,
            user_id=user_id,
            telegram_id=telegram_id,
            original_photo_url=original_photo_url,
            product_name=product_name,
            product_type=product_type,
            language=language,
            additional_info=additional_info,
            is_enhanced=is_enhanced,
            is_carousel_duo=is_carousel_duo,
        ))
    except Exception as exc:
        _log("TASK_ERROR", post_id, f"error={exc}", error=True)
        supabase = get_supabase()
        supabase.table("posts").update({
            "status": "failed",
            "error_message": str(exc),
        }).eq("id", post_id).execute()
        if telegram_id:
            asyncio.run(send_message(
                telegram_id,
                f"❌ Sorry, processing failed for '{product_name}'.\nError: {str(exc)[:100]}\n\nPlease try again.",
            ))
        raise self.retry(exc=exc)


async def _process_photo_async(
    post_id: str,
    user_id: str,
    telegram_id: int,
    original_photo_url: str,
    product_name: str,
    product_type: str,
    language: str,
    additional_info: str,
    is_enhanced: bool = True,
    is_carousel_duo: bool = False,
):
    supabase = get_supabase()
    _log("START", post_id, f"product='{product_name}' enhanced={is_enhanced} duo={is_carousel_duo}")

    # ── Step 1: Download original photo ───────────────────────────────────────
    _log("STEP1_DOWNLOAD", post_id, f"url={original_photo_url[:80]}")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(original_photo_url)
            resp.raise_for_status()
            original_bytes = resp.content
        _log("STEP1_DOWNLOAD", post_id, f"success size={len(original_bytes)} bytes")
    except Exception as e:
        _log("STEP1_DOWNLOAD", post_id, f"FAILED: {e}", error=True)
        raise

    # Step 2 & 3: Photo processing pipeline ────────────────────────────────
    _log("STEP2_PIPELINE", post_id, f"calling full_photo_pipeline skip_editing={not is_enhanced}")
    try:
        # if is_enhanced is False, we skip all filters/sharpening to keep original
        pipeline_result = await full_photo_pipeline(original_bytes, skip_editing=not is_enhanced)
        edited_bytes = pipeline_result["edited_bytes"]
        enhance_failed = pipeline_result.get("enhance_failed", False)
        
        if enhance_failed:
            _log("STEP2_PIPELINE", post_id, "enhancement failed, using original/sharpened bytes", error=True)
            
        _log("STEP2_PIPELINE", post_id, f"success edited_size={len(edited_bytes)} bytes")
    except Exception as e:
        _log("STEP2_PIPELINE", post_id, f"FAILED: {e}", error=True)
        raise

    # Carousel duo: generate second image
    second_image_bytes = None
    if is_carousel_duo:
        _log("STEP2b_DUO", post_id, "generating second image for carousel")
        try:
            if not is_enhanced:
                pro_res = await full_photo_pipeline(original_bytes, subtle_only=False)
                second_image_bytes = pro_res["edited_bytes"]
            else:
                sub_res = await full_photo_pipeline(original_bytes, subtle_only=True)
                second_image_bytes = sub_res["edited_bytes"]
            _log("STEP2b_DUO", post_id, f"success second_size={len(second_image_bytes)} bytes")
        except Exception as e:
            _log("STEP2b_DUO", post_id, f"FAILED: {e}", error=True)
            raise

    # ── Step 4: Analyze with Claude Vision ────────────────────────────────────
    _log("STEP4_VISION", post_id, "calling Claude Vision analysis")
    try:
        # PLAN: Use original_bytes for better vision accuracy (untouched by sharpening/filters)
        photo_b64 = image_to_base64(original_bytes)
        vision_data = await analyze_product_photo(photo_b64)
        if product_type == "other" and vision_data.get("product_type"):
            product_type = vision_data["product_type"]
        _log("STEP4_VISION", post_id, f"detected product_type={product_type}")
    except Exception as e:
        # Non-fatal: AI vision failure should not stop the pipeline
        _log("STEP4_VISION", post_id, f"WARNING (non-fatal): {e} — continuing with default product_type", error=True)

    # ── Step 5: Generate caption ───────────────────────────────────────────────
    _log("STEP5_CAPTION", post_id, f"generating captions lang={language}")
    try:
        caption_data = await generate_caption(
            product_name=product_name,
            product_type=product_type,
            language=language,
            additional_info=additional_info,
            is_enhanced=is_enhanced or is_carousel_duo,
        )
        _log("STEP5_CAPTION", post_id, f"caption_en='{caption_data.get('caption_english','')[:60]}...'")
    except Exception as e:
        # Non-fatal: caption failure should not stop the pipeline
        _log("STEP5_CAPTION", post_id, f"WARNING (non-fatal): {e} — using default caption", error=True)
        caption_data = {
            "caption_hindi": f"✨ {product_name} — प्रीमियम क्वालिटी। ऑर्डर के लिए DM करें।",
            "caption_english": f"✨ {product_name} — Premium quality. DM to order!",
            "hashtags": ["#instaagent", "#smallbusiness", "#india"],
            "cta": "DM to Order",
        }

    # ── Step 6: Upload edited photo(s) to Supabase Storage ────────────────────
    _log("STEP6_UPLOAD", post_id, "uploading edited photo to Supabase")
    
    async def _upload_with_retry(bucket, path, data, options):
        # Implementation of exponential backoff for storage uploads
        for i in range(3):
            try:
                supabase.storage.from_(bucket).upload(path=path, file=data, file_options=options)
                return True
            except Exception as e:
                wait = (i + 1) * 2
                _log("STEP6_UPLOAD", post_id, f"Upload retry {i+1} after {wait}s: {e}", error=True)
                if i < 2: time.sleep(wait)
                else: raise
        return False

    try:
        edited_filename = f"posts/{user_id}/{post_id}_edited.jpg"
        await _upload_with_retry(
            "post-photos", 
            edited_filename, 
            edited_bytes, 
            {"content-type": "image/jpeg"}
        )
        edited_url = supabase.storage.from_("post-photos").get_public_url(edited_filename)
        _log("STEP6_UPLOAD", post_id, f"edited_url={edited_url[:80]}")
    except Exception as e:
        _log("STEP6_UPLOAD", post_id, f"FAILED: {e}", error=True)
        raise

    secondary_url = None
    if second_image_bytes:
        try:
            secondary_filename = f"posts/{user_id}/{post_id}_secondary.jpg"
            await _upload_with_retry(
                "post-photos",
                secondary_filename,
                second_image_bytes,
                {"content-type": "image/jpeg"}
            )
            secondary_url = supabase.storage.from_("post-photos").get_public_url(secondary_filename)
            _log("STEP6_UPLOAD", post_id, f"secondary_url={secondary_url[:80]}")
        except Exception as e:
            _log("STEP6_UPLOAD", post_id, f"secondary upload FAILED (non-fatal): {e}", error=True)

    # ── Step 7: Update DB ──────────────────────────────────────────────────────
    _log("STEP7_DB", post_id, "updating post record → status=ready")
    try:
        # NOTE: is_enhanced and is_carousel_duo are excluded until added to DB.
        supabase.table("posts").update({
            "edited_photo_url":   edited_url,
            "secondary_photo_url": secondary_url,
            "caption_hindi":      caption_data.get("caption_hindi", ""),
            "caption_english":    caption_data.get("caption_english", ""),
            "hashtags":           caption_data.get("hashtags", []),
            "status":             "ready",
            "error_message":      None,
        }).eq("id", post_id).execute()
        _log("STEP7_DB", post_id, "post status=ready saved ✔")
    except Exception as e:
        _log("STEP7_DB", post_id, f"FAILED: {e}", error=True)
        raise

    # ── Step 8: Notify user on Telegram (only for Telegram flow) ──────────────
    if telegram_id:
        _log("STEP8_TELEGRAM", post_id, f"sending notification to telegram_id={telegram_id}")
        try:
            await send_message(
                telegram_id,
                f"✅ Your photo for *{product_name}* is ready!\n\n"
                f"{caption_data.get('caption_english', '')[:200]}\n\n"
                f"View in your InstaAgent dashboard to approve and post.",
            )
            _log("STEP8_TELEGRAM", post_id, "Telegram message sent ✔")
        except Exception as e:
            _log("STEP8_TELEGRAM", post_id, f"FAILED (non-fatal): {e}", error=True)

    _log("COMPLETE", post_id, "🎉 Pipeline finished successfully!")


async def _post_to_instagram_async(
    ig_token: str,
    photo_url: str,
    caption: str,
    is_carousel: bool = False,
    secondary_url: str = None,
) -> str:
    """Post a photo (or carousel) to Instagram. Returns the IG post ID."""
    from app.services.instagram_service import publish_carousel, post_to_instagram
    import httpx

    # ENSURE TOKEN IS DECRYPTED
    from app.utils.crypto import decrypt_token
    dec_token = decrypt_token(ig_token)

    _log("IG_POST", "n/a", f"posting to Instagram carousel={is_carousel}")

    # Step 1: Get User ID using professional endpoint
    async with httpx.AsyncClient() as client:
        # Use graph.facebook.com/v19.0/me for professional accounts
        me_url = "https://graph.facebook.com/v19.0/me"
        me = await client.get(
            me_url,
            params={"fields": "id", "access_token": dec_token},
        )
        me.raise_for_status()
        ig_user_id = me.json()["id"]

    if is_carousel and secondary_url:
        post_id = await publish_carousel(
            instagram_user_id=ig_user_id,
            access_token=dec_token,
            image_urls=[photo_url, secondary_url],
            caption=caption,
        )
    else:
        post_id = await post_to_instagram(
            instagram_user_id=ig_user_id,
            access_token=dec_token,
            image_url=photo_url,
            caption=caption,
        )

    _log("IG_POST", "n/a", f"posted successfully ig_post_id={post_id}")
    return post_id
