# backend/app/api/posts.py
# POST /api/v1/posts — Create, list, publish, schedule posts
# FIXED: Null guards on caption_hindi and hashtags in publish_post
# FIXED: All scheduled_at times now stored as UTC (was IST — causing late posts)
# NEW: /publish-now and /schedule-from-settings endpoints

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
from app.config import settings
from app.db.supabase import get_supabase
from app.middleware.auth import get_current_user
from app.middleware.plan_check import check_post_quota
from app.workers.photo_worker import process_photo_task
from app.models.post import PostResponse
from app.utils.crypto import decrypt_token

router = APIRouter()

# IST is UTC+5:30
IST_OFFSET = timedelta(hours=5, minutes=30)


@router.post("/create", summary="Upload photo and start AI processing")
async def create_post(
    photo: UploadFile = File(..., description="Product photo JPG/PNG max 10MB"),
    product_name: str = Form(..., description="Product name in Hindi or English"),
    product_type: str = Form(default="other", description="jewellery|clothing|food|handmade|other"),
    additional_info: str = Form(default="", description="Price, materials, offers, festival"),
    is_enhanced: bool = Form(default=True, description="Enable AI sharpening & color lift"),
    remove_bg: bool = Form(default=False, description="Enable local background removal"),
    is_carousel_duo: bool = Form(default=False, description="Generate original + enhanced duo"),
    current_user: dict = Depends(get_current_user),
    _quota: None = Depends(check_post_quota),
):
    """
    Upload a product photo. The backend will:
    1. Save photo to Supabase Storage
    2. Queue background job (Celery) for processing
    3. Return immediately with post_id — processing happens in background
    4. User gets Telegram notification when ready (~12 seconds)
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    post_id = str(uuid.uuid4())

    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if photo.content_type not in allowed_types:
        raise HTTPException(400, "Only JPG, PNG, WEBP images are supported")

    # Validate file size (10MB max)
    content = await photo.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "Image must be smaller than 10MB")

    # Upload original to Supabase Storage
    original_filename = f"posts/{user_id}/{post_id}_original.jpg"
    supabase.storage.from_("post-photos").upload(
        path=original_filename,
        file=content,
        file_options={"content-type": "image/jpeg"},
    )
    original_url = supabase.storage.from_("post-photos").get_public_url(original_filename)

    # Create post record with status='processing'
    # NOTE: is_enhanced and is_carousel_duo are intentionally excluded until added to DB.
    # Run: ALTER TABLE posts ADD COLUMN IF NOT EXISTS is_enhanced BOOLEAN DEFAULT TRUE;
    # Run: ALTER TABLE posts ADD COLUMN IF NOT EXISTS is_carousel_duo BOOLEAN DEFAULT FALSE;
    post_data = {
        "id": post_id,
        "user_id": user_id,
        "original_photo_url": original_url,
        "product_name": product_name,
        "product_type": product_type,
        "additional_info": additional_info,
        "status": "processing",
    }
    supabase.table("posts").insert(post_data).execute()

    # Log usage
    month_year = datetime.now().strftime("%Y-%m")
    supabase.table("usage_logs").insert({
        "user_id": user_id,
        "action": "post_created",
        "api_service": "pipeline",
        "month_year": month_year,
    }).execute()

    # Queue background job — fire and forget
    process_photo_task.delay(
        post_id=post_id,
        user_id=user_id,
        telegram_id=current_user.get("telegram_id"),
        original_photo_url=original_url,
        product_name=product_name,
        product_type=product_type,
        language=current_user.get("language", "hi"),
        additional_info=additional_info,
        is_enhanced=is_enhanced,
        remove_bg=remove_bg,
        is_carousel_duo=is_carousel_duo,
    )

    return {
        "post_id": post_id,
        "original_photo_url": original_url,
        "status": "processing",
        "message": "Photo received! AI is processing. You'll get a Telegram notification in ~12 seconds.",
    }
@router.post("/bulk", summary="Batch upload photos for catalog processing")
async def bulk_create_posts(
    photos: List[UploadFile] = File(...),
    product_names: str = Form(..., description="Comma separated product names"),
    is_enhanced: bool = Form(default=True),
    remove_bg: bool = Form(default=False),
    current_user: dict = Depends(get_current_user),
    _quota: None = Depends(check_post_quota),
):
    """
    Experimental bulk upload. Accepts multiple photos and a comma-separated list of names.
    Processes each photo through the AI pipeline.
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    names = [n.strip() for n in product_names.split(",") if n.strip()]
    
    if len(photos) != len(names):
        raise HTTPException(400, f"Number of photos ({len(photos)}) does not match number of names ({len(names)})")

    results = []
    for photo, name in zip(photos, names):
        post_id = str(uuid.uuid4())
        content = await photo.read()
        
        # Upload
        filename = f"posts/{user_id}/{post_id}_original.jpg"
        supabase.storage.from_("post-photos").upload(path=filename, file=content)
        url = supabase.storage.from_("post-photos").get_public_url(filename)
        
        # Record
        supabase.table("posts").insert({
            "id": post_id, "user_id": user_id, "original_photo_url": url,
            "product_name": name, "status": "processing"
        }).execute()
        
        # Queue
        process_photo_task.delay(
            post_id=post_id, user_id=user_id, telegram_id=current_user.get("telegram_id"),
            original_photo_url=url, product_name=name, language=current_user.get("language", "hi"),
            is_enhanced=is_enhanced, remove_bg=remove_bg
        )
        results.append(post_id)

    return {"message": f"Successfully queued {len(results)} posts for processing", "post_ids": results}


@router.get("", summary="List all posts for current user")
async def list_posts(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    user_id = current_user["id"]

    query = supabase.table("posts").select("*").eq("user_id", user_id).order("created_at", desc=True)

    if status:
        query = query.eq("status", status)

    offset = (page - 1) * page_size
    query = query.range(offset, offset + page_size - 1)

    result = query.execute()
    return {"posts": result.data, "page": page, "page_size": page_size}


@router.get("/{post_id}", summary="Get single post details")
async def get_post(post_id: str, current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    result = supabase.table("posts").select("*").eq("id", post_id).eq("user_id", current_user["id"]).single().execute()
    if not result.data:
        raise HTTPException(404, "Post not found")
    return result.data


@router.post("/{post_id}/publish", summary="Publish post to Instagram now")
async def publish_post(post_id: str, current_user: dict = Depends(get_current_user)):
    from app.services.instagram_service import post_to_instagram

    supabase = get_supabase()
    user_id = current_user["id"]

    # Get post
    post_result = supabase.table("posts").select("*").eq("id", post_id).eq("user_id", user_id).single().execute()
    if not post_result.data:
        raise HTTPException(404, "Post not found")
    post = post_result.data

    if post["status"] not in ("ready", "scheduled"):
        raise HTTPException(400, f"Post is {post['status']} — can only publish ready or scheduled posts")

    # Get user's Instagram token
    user_result = supabase.table("users").select("instagram_token,instagram_id").eq("id", user_id).single().execute()
    user = user_result.data
    if not user.get("instagram_token"):
        raise HTTPException(400, "Instagram not connected. Please connect via Settings.")

    # ✅ FIXED: Null guards — caption_hindi or hashtags may be None
    caption_hindi = post.get("caption_hindi") or ""
    hashtags = post.get("hashtags") or []
    hashtag_str = " ".join(hashtags) if hashtags else ""
    caption = f"{caption_hindi}\n\n{hashtag_str}".strip()

    if not caption:
        raise HTTPException(400, "Post has no caption yet. Wait for AI processing to complete.")

    # Resolve which photo URL to use: edited (if available) else original
    image_url = post.get("edited_photo_url") or post.get("original_photo_url")
    if not image_url:
        raise HTTPException(400, "No photo URL found for this post.")

    # Post to Instagram
    instagram_post_id = await post_to_instagram(
        instagram_user_id=user["instagram_id"],
        access_token=decrypt_token(user["instagram_token"]),
        image_url=image_url,
        caption=caption,
    )

    permalink = f"https://www.instagram.com/p/{instagram_post_id}/"

    # Update post record — store posted_at as UTC
    supabase.table("posts").update({
        "status": "posted",
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "instagram_post_id": instagram_post_id,
        "instagram_permalink": permalink,
        "error_message": None,
    }).eq("id", post_id).execute()

    return {"status": "posted", "instagram_post_id": instagram_post_id, "permalink": permalink}


@router.post("/{post_id}/publish-now", summary="Publish post to Instagram immediately (alias)")
async def publish_now(post_id: str, current_user: dict = Depends(get_current_user)):
    """Alias for /publish — used by the 'Post Now' button in the UI."""
    return await publish_post(post_id, current_user)


@router.post("/{post_id}/schedule", summary="Schedule post for a specific time (UTC)")
async def schedule_post(
    post_id: str,
    scheduled_at: datetime,
    current_user: dict = Depends(get_current_user),
):
    """
    Schedule a post at an explicit time.
    The datetime must include timezone info, or it will be assumed to be IST and converted to UTC.
    Always stores scheduled_at as UTC in the DB.
    """
    supabase = get_supabase()

    # If naive datetime received, assume IST and convert to UTC
    if scheduled_at.tzinfo is None:
        scheduled_at_utc = (scheduled_at - IST_OFFSET).replace(tzinfo=timezone.utc)
    else:
        scheduled_at_utc = scheduled_at.astimezone(timezone.utc)

    supabase.table("posts").update({
        "status": "scheduled",
        "scheduled_at": scheduled_at_utc.isoformat(),
    }).eq("id", post_id).eq("user_id", current_user["id"]).execute()

    ist_display = scheduled_at_utc + IST_OFFSET
    return {
        "status": "scheduled",
        "scheduled_at_utc": scheduled_at_utc.isoformat(),
        "scheduled_at_ist": ist_display.strftime("%d %b %Y %I:%M %p IST"),
    }


@router.post("/{post_id}/schedule-from-settings", summary="Schedule at user's preferred IST time")
async def schedule_from_settings(
    post_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Schedules the post at the user's saved preferred_post_time (IST) for TODAY.
    If the time has already passed today, schedules for tomorrow.
    Always stores scheduled_at as UTC.
    """
    supabase = get_supabase()
    user_id = current_user["id"]

    # Fetch user's preferred time
    user_result = supabase.table("users").select("preferred_post_time").eq("id", user_id).single().execute()
    preferred_time = (user_result.data or {}).get("preferred_post_time") or "19:00"

    # Parse HH:MM (IST) and convert to UTC datetime for today
    if not preferred_time:
        from app.workers.post_worker import suggest_best_post_time
        preferred_time = await suggest_best_post_time(user_id)
        logger.info("A4.2: Using AI suggested time: %s for user %s", preferred_time, user_id)

    try:
        hour, minute = map(int, preferred_time.split(":"))
    except Exception:
        hour, minute = 19, 0  # Fallback: 7 PM IST

    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + IST_OFFSET

    # Build IST datetime for today
    scheduled_ist = now_ist.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If the time has already passed today (IST), schedule for tomorrow
    if scheduled_ist <= now_ist:
        scheduled_ist = scheduled_ist + timedelta(days=1)

    # Convert IST → UTC for storage
    scheduled_utc = (scheduled_ist - IST_OFFSET).replace(tzinfo=timezone.utc)

    # Verify post exists and belongs to user
    post_result = supabase.table("posts").select("id,status").eq("id", post_id).eq("user_id", user_id).single().execute()
    if not post_result.data:
        raise HTTPException(404, "Post not found")
    if post_result.data["status"] not in ("ready", "scheduled"):
        raise HTTPException(400, f"Post is {post_result.data['status']} — cannot schedule")

    supabase.table("posts").update({
        "status": "scheduled",
        "scheduled_at": scheduled_utc.isoformat(),
    }).eq("id", post_id).eq("user_id", user_id).execute()

    return {
        "status": "scheduled",
        "scheduled_at_utc": scheduled_utc.isoformat(),
        "scheduled_at_ist": scheduled_ist.strftime("%d %b %Y %I:%M %p IST"),
        "preferred_time_ist": preferred_time,
    }


@router.patch("/{post_id}", summary="Update post details (status, feedback)")
async def patch_post(
    post_id: str,
    update_data: dict,
    current_user: dict = Depends(get_current_user)
):
    supabase = get_supabase()
    # Filter allowed keys
    allowed = {"status", "return_feedback", "caption_hindi", "caption_english", "hashtags"}
    payload = {k: v for k, v in update_data.items() if k in allowed}
    
    if not payload:
        raise HTTPException(400, "No valid update fields provided")
        
    result = supabase.table("posts").update(payload).eq("id", post_id).eq("user_id", current_user["id"]).execute()
    if not result.data:
        raise HTTPException(404, "Post not found")
    return {"updated": True, "post": result.data[0]}


@router.delete("/{post_id}", summary="Delete a post")
async def delete_post(post_id: str, current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    result = supabase.table("posts").delete().eq("id", post_id).eq("user_id", current_user["id"]).execute()
    if not result.data:
        raise HTTPException(404, "Post not found or already deleted")
    return {"deleted": True}
