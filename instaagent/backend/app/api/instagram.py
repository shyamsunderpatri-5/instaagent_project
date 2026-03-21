# backend/app/api/instagram.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Enterprise Instagram API Router
# Endpoints: OAuth connect/callback/disconnect/status,
#            publish Carousel & Reel, rate-limit status, account analytics
# OAuth state stored in Redis (survives server restarts).
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import secrets
from datetime import datetime, timezone, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

from app.config import settings
from app.db.supabase import get_supabase
from app.middleware.auth import get_current_user
from app.services.instagram_service import (
    get_oauth_url,
    exchange_code_for_token,
    get_user_profile,
    publish_carousel,
    publish_reel,
    get_publishing_rate_limit,
    get_account_insights,
    publish_photo_story,
)
from app.utils.crypto import encrypt_token, decrypt_token

import redis

from app.db.redis_client import get_redis as _get_redis_client

router = APIRouter()

# ── Redis (OAuth state) ───────────────────────────────────────────────────────
OAUTH_STATE_TTL = 600   # 10 minutes


def get_redis() -> redis.Redis:
    r = _get_redis_client()
    if r is None:
        raise HTTPException(503, "Redis unavailable — please try again in a moment.")
    return r


# ── Pydantic request models ───────────────────────────────────────────────────

class CarouselPublishRequest(BaseModel):
    image_urls: List[str]
    caption: str = ""

class ReelPublishRequest(BaseModel):
    video_url: str
    caption: str = ""
    cover_url: str = ""
    share_to_feed: bool = True

class StoryPublishRequest(BaseModel):
    image_url: str


# ═══════════════════════════════════════════════════════════════════════════════
# OAuth Flow
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/connect", summary="Start Instagram OAuth flow")
async def connect_instagram(current_user: dict = Depends(get_current_user)):
    """
    Return the Instagram OAuth URL as JSON.

    The frontend uses window.location.href to navigate there.
    We cannot use RedirectResponse here because fetch() cannot follow
    cross-origin redirects to navigate the browser tab.
    If INSTAGRAM_SIMULATE is True, return a mock callback URL to skip Meta.
    """
    state = secrets.token_urlsafe(32)
    try:
        r = get_redis()
        r.setex(f"oauth_state:{state}", OAUTH_STATE_TTL, current_user["id"])
    except Exception as e:
        raise HTTPException(500, f"Failed to initiate OAuth flow: {e}")

    # Simulation Bypass: Skip Meta and redirect to our own callback with a mock code
    if settings.INSTAGRAM_SIMULATE:
        mock_callback = (
            f"http://localhost:8000/api/v1/instagram/callback"
            f"?code=mock_code_{secrets.token_hex(8)}"
            f"&state={state}"
        )
        # Note: Frontend handles the redirect. We return the "auth_url" as this mock link.
        return {"auth_url": mock_callback}

    return {"auth_url": get_oauth_url(state)}


@router.get("/callback", summary="Instagram OAuth callback — called by Meta")
async def instagram_callback(code: str, state: str):
    """Exchange code for long-lived token and save to DB."""
    try:
        r         = get_redis()
        user_id   = r.getdel(f"oauth_state:{state}")
    except Exception:
        raise HTTPException(500, "Failed to verify OAuth state. Please try again.")

    if not user_id:
        raise HTTPException(
            400,
            "OAuth session expired or invalid. Please go back and try connecting again.",
        )

    try:
        if code.startswith("mock_code_") and settings.INSTAGRAM_SIMULATE:
            token_data = {
                "access_token": "sim_token_" + secrets.token_hex(16),
                "expires_in": 5184000
            }
        else:
            token_data = await exchange_code_for_token(code)
    except Exception as e:
        raise HTTPException(400, f"Failed to exchange OAuth code: {e}")

    access_token  = token_data["access_token"]
    expires_in    = int(token_data.get("expires_in", 5184000))   # ~60 days default
    token_expiry  = (
        datetime.now(timezone.utc) + timedelta(seconds=float(expires_in))
    ).isoformat()

    try:
        if str(access_token).startswith("sim_token_") and settings.INSTAGRAM_SIMULATE:
            profile = {
                "id": "sim_user_" + secrets.token_hex(4),
                "username": "simulated_seller"
            }
        else:
            profile = await get_user_profile(access_token)
    except Exception as e:
        raise HTTPException(400, f"Failed to fetch Instagram profile: {e}")

    supabase = get_supabase()
    supabase.table("users").update({
        "instagram_token":            encrypt_token(access_token),
        "instagram_id":               profile["id"],
        "instagram_username":         profile["username"],
        "instagram_token_expires_at": token_expiry,
    }).eq("id", user_id).execute()

    return RedirectResponse(
        url=(
            f"{settings.FRONTEND_URL}"
            f"?instagram=connected&username={profile['username']}"
        )
    )


@router.get("/status", summary="Check if Instagram is connected")
async def instagram_status(current_user: dict = Depends(get_current_user)):
    """Returns current Instagram connection status."""
    return {
        "connected":          bool(current_user.get("instagram_token")),
        "username":           current_user.get("instagram_username"),
        "instagram_id":       current_user.get("instagram_id"),
        "token_expires_at":   current_user.get("instagram_token_expires_at"),
    }


@router.delete("/disconnect", summary="Disconnect Instagram account")
async def disconnect_instagram(current_user: dict = Depends(get_current_user)):
    """Remove Instagram token from the database."""
    supabase = get_supabase()
    supabase.table("users").update({
        "instagram_token":            None,
        "instagram_id":               None,
        "instagram_username":         None,
        "instagram_token_expires_at": None,
    }).eq("id", current_user["id"]).execute()
    return {"disconnected": True, "message": "Instagram account disconnected."}


# ═══════════════════════════════════════════════════════════════════════════════
# Content Publishing
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/publish/carousel", summary="Publish a carousel (multi-image) post")
async def publish_carousel_post(
    body: CarouselPublishRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Publish 2–10 images as an Instagram carousel.
    All image_urls must be publicly accessible.
    """
    _require_instagram(current_user)

    if not 2 <= len(body.image_urls) <= 10:
        raise HTTPException(400, "Carousel must have between 2 and 10 images.")

    try:
        post_id = await publish_carousel(
            instagram_user_id=current_user["instagram_id"],
            access_token=decrypt_token(current_user["instagram_token"]),
            image_urls=body.image_urls,
            caption=body.caption,
        )
    except Exception as e:
        raise HTTPException(502, f"Instagram publish failed: {e}")

    return {
        "ok":                 True,
        "instagram_post_id":  post_id,
        "permalink":          f"https://www.instagram.com/p/{post_id}/",
    }


@router.post("/publish/reel", summary="Publish a Reel (video post)")
async def publish_reel_post(
    body: ReelPublishRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Publish a Reel from a publicly accessible MP4 URL.
    The endpoint polls Meta's container status until processing finishes (~60s).
    """
    _require_instagram(current_user)

    try:
        post_id = await publish_reel(
            instagram_user_id=current_user["instagram_id"],
            access_token=decrypt_token(current_user["instagram_token"]),
            video_url=body.video_url,
            caption=body.caption,
            cover_url=body.cover_url,
            share_to_feed=body.share_to_feed,
        )
    except TimeoutError:
        raise HTTPException(504, "Reel processing timed out. The video may still publish — check Instagram.")
    except Exception as e:
        raise HTTPException(502, f"Instagram Reel publish failed: {e}")

    return {
        "ok":                True,
        "instagram_post_id": post_id,
        "permalink":         f"https://www.instagram.com/reel/{post_id}/",
    }


@router.post("/publish/story", summary="Publish a photo Story")
async def publish_story(
    body: StoryPublishRequest,
    current_user: dict = Depends(get_current_user),
):
    """Publish an image as an Instagram Story."""
    _require_instagram(current_user)
    try:
        story_id = await publish_photo_story(
            instagram_user_id=current_user["instagram_id"],
            access_token=decrypt_token(current_user["instagram_token"]),
            image_url=body.image_url,
        )
    except Exception as e:
        raise HTTPException(502, f"Instagram Story publish failed: {e}")
    return {"ok": True, "story_id": story_id}


# ═══════════════════════════════════════════════════════════════════════════════
# Rate Limit & Account Insights
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/rate-limit", summary="Check Instagram content publishing rate limit")
async def instagram_rate_limit(current_user: dict = Depends(get_current_user)):
    """
    Returns current 24-hour publishing quota usage.
    Instagram allows 25 API-published posts per 24 hours.
    """
    _require_instagram(current_user)
    try:
        limit = await get_publishing_rate_limit(
            current_user["instagram_id"],
            decrypt_token(current_user["instagram_token"]),
        )
    except Exception as e:
        raise HTTPException(502, f"Could not fetch rate limit: {e}")
    return {"ok": True, "data": limit}


@router.get("/analytics", summary="Live account-level Instagram analytics")
async def instagram_account_analytics(
    period: str = "month",
    current_user: dict = Depends(get_current_user),
):
    """
    Returns live account insights from Instagram Graph API.
    period: 'day' | 'week' | 'month'
    Metrics: impressions, reach, profile_views, website_clicks, follower_count.
    """
    _require_instagram(current_user)
    try:
        insights = await get_account_insights(
            current_user["instagram_id"],
            decrypt_token(current_user["instagram_token"]),
            period=period,
        )
    except Exception as e:
        raise HTTPException(502, f"Instagram insights error: {e}")
    return {"ok": True, "period": period, "data": insights}


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _require_instagram(user: dict) -> None:
    if not user.get("instagram_token") or not user.get("instagram_id"):
        raise HTTPException(
            400,
            "Instagram is not connected. Please connect via /api/v1/instagram/connect.",
        )