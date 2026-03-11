# backend/app/services/instagram_service.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Enterprise Instagram / Meta Graph API Service
# Covers: OAuth, Feed Posts, Carousels, Reels, Stories,
#         Token Refresh, Rate-Limit Guard, Post & Account Analytics
# Graph API Version: v19.0
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GRAPH_VERSION   = "v19.0"
GRAPH_BASE      = f"https://graph.instagram.com/{GRAPH_VERSION}"
AUTH_URL        = "https://api.instagram.com/oauth/authorize"
TOKEN_URL       = "https://api.instagram.com/oauth/access_token"
LONG_TOKEN_URL  = "https://graph.instagram.com/access_token"
REFRESH_TOKEN_URL = "https://graph.instagram.com/refresh_access_token"

# ── Default OAuth scopes ──────────────────────────────────────────────────────
# These are the NEW Instagram Business scopes (Instagram Login, not Facebook Login)
OAUTH_SCOPES = ",".join([
    "instagram_business_basic",
    "instagram_business_content_publish",
    "instagram_business_manage_comments",
    "instagram_business_manage_messages",
])

# ── Media container polling ───────────────────────────────────────────────────
CONTAINER_POLL_MAX_ATTEMPTS = 12
CONTAINER_POLL_INTERVAL_SEC = 5


# ═══════════════════════════════════════════════════════════════════════════════
# OAuth Flow
# ═══════════════════════════════════════════════════════════════════════════════

def get_oauth_url(state: str) -> str:
    """Generate Instagram OAuth authorization URL (Instagram Login for Business)."""
    return (
        f"{AUTH_URL}"
        f"?client_id={settings.INSTAGRAM_APP_ID}"
        f"&redirect_uri={settings.INSTAGRAM_REDIRECT_URI}"
        f"&scope={OAUTH_SCOPES}"
        f"&response_type=code"
        f"&state={state}"
    )


async def exchange_code_for_token(code: str) -> dict:
    """
    Exchange OAuth code for a long-lived (60-day) Instagram access token.
    Step 1: POST to get a short-lived token.
    Step 2: GET to exchange for a long-lived token.
    """
    async with httpx.AsyncClient(timeout=20.0) as client:
        # Step 1 — short-lived token (POST)
        short = await client.post(TOKEN_URL, data={
            "client_id":     settings.INSTAGRAM_APP_ID,
            "client_secret": settings.INSTAGRAM_APP_SECRET,
            "grant_type":    "authorization_code",
            "redirect_uri":  settings.INSTAGRAM_REDIRECT_URI,
            "code":          code,
        })
        short.raise_for_status()
        short_data = short.json()

        # Step 2 — long-lived token (GET)
        long = await client.get(LONG_TOKEN_URL, params={
            "grant_type":    "ig_exchange_token",
            "client_secret": settings.INSTAGRAM_APP_SECRET,
            "access_token":  short_data["access_token"],
        })
        long.raise_for_status()
        return long.json()   # {access_token, token_type, expires_in}


async def refresh_long_lived_token(access_token: str) -> dict:
    """
    Refresh a long-lived Instagram token before it expires (valid for another 60 days).
    Tokens can be refreshed when they are at least 24 hours old.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(REFRESH_TOKEN_URL, params={
            "grant_type":   "ig_refresh_token",
            "access_token": access_token,
        })
        resp.raise_for_status()
        return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# User Profile
# ═══════════════════════════════════════════════════════════════════════════════

async def get_user_profile(access_token: str) -> dict:
    """
    Get Instagram Business user ID and username.
    Works with the new Instagram Login (instagram_business_basic scope).
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{GRAPH_BASE}/me",
            params={
                "fields":       "user_id,username",
                "access_token": access_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        # Instagram Login returns user_id, not id — normalise here
        return {
            "id":       data.get("user_id") or data.get("id"),
            "username": data.get("username", ""),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Rate-Limit Guard
# ═══════════════════════════════════════════════════════════════════════════════

async def get_publishing_rate_limit(
    instagram_user_id: str,
    access_token: str,
) -> dict:
    """
    Check Meta's content publishing rate limit status.
    Instagram allows 25 API-published posts per 24 hours.
    Returns: {config: [{quota_total, quota_usage}], quota_usage, quota_total}
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{GRAPH_BASE}/{instagram_user_id}/content_publishing_limit",
            params={
                "fields":       "config,quota_usage",
                "access_token": access_token,
            },
        )
        resp.raise_for_status()
        data = resp.json().get("data", [{}])[0]
        config = data.get("config", {})
        return {
            "quota_usage": data.get("quota_usage", 0),
            "quota_total": config.get("quota_total", 25),
            "can_post":    data.get("quota_usage", 0) < config.get("quota_total", 25),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Single-Image Feed Post
# ═══════════════════════════════════════════════════════════════════════════════

async def create_media_container(
    instagram_user_id: str,
    access_token: str,
    image_url: str,
    caption: str,
) -> str:
    """Step 1 of 2-step posting — create single-image container. Returns container_id."""
    # Sanitise URL — remove trailing '?' or '&' which Meta API rejects
    image_url = image_url.rstrip("?&")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{GRAPH_BASE}/{instagram_user_id}/media",
            params={
                "image_url":    image_url,
                "caption":      caption,
                "access_token": access_token,
            },
        )
        if resp.status_code == 400:
            logger.error(f"❌ Instagram 400 Bad Request: {resp.text}")
        resp.raise_for_status()
        return resp.json()["id"]


async def publish_media_container(
    instagram_user_id: str,
    access_token: str,
    container_id: str,
) -> dict:
    """Step 2 of 2-step posting — publish the container. Returns {id}."""
    if settings.INSTAGRAM_SIMULATE:
        sim_id = f"sim_{container_id}"
        logger.info(f"🚀 [SIMULATION] Publishing container {container_id} for user {instagram_user_id}. Generated ID: {sim_id}")
        return {"id": sim_id, "simulated": True}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{GRAPH_BASE}/{instagram_user_id}/media_publish",
            params={
                "creation_id":  container_id,
                "access_token": access_token,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def post_to_instagram(
    instagram_user_id: str,
    access_token: str,
    image_url: str,
    caption: str,
) -> str:
    """Full 2-step single-image posting flow. Returns Instagram post ID."""
    container_id = await create_media_container(
        instagram_user_id, access_token, image_url, caption
    )
    result = await publish_media_container(
        instagram_user_id, access_token, container_id
    )
    return result["id"]


# ═══════════════════════════════════════════════════════════════════════════════
# Carousel (Multi-Image) Post
# ═══════════════════════════════════════════════════════════════════════════════

async def create_carousel_item_container(
    instagram_user_id: str,
    access_token: str,
    image_url: str,
    is_carousel_item: bool = True,
) -> str:
    """Create a single carousel item container. Returns item container_id."""
    # Sanitise URL
    image_url = image_url.rstrip("?&")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{GRAPH_BASE}/{instagram_user_id}/media",
            params={
                "image_url":        image_url,
                "is_carousel_item": "true" if is_carousel_item else "false",
                "access_token":     access_token,
            },
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def create_carousel_container(
    instagram_user_id: str,
    access_token: str,
    children_ids: list[str],
    caption: str,
) -> str:
    """
    Create the parent carousel container from a list of item container IDs.
    Supports 2–10 images.
    Returns: carousel container_id
    """
    if not 2 <= len(children_ids) <= 10:
        raise ValueError("Carousel must have 2–10 images.")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{GRAPH_BASE}/{instagram_user_id}/media",
            params={
                "media_type":   "CAROUSEL",
                "children":     ",".join(children_ids),
                "caption":      caption,
                "access_token": access_token,
            },
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def publish_carousel(
    instagram_user_id: str,
    access_token: str,
    image_urls: list[str],
    caption: str,
) -> str:
    """
    Full carousel posting flow.
    1. Creates item containers for each image URL.
    2. Creates the parent carousel container.
    3. Publishes it.
    Returns: Instagram post ID
    """
    # Step 1 — create individual item containers (can be parallelised)
    import asyncio
    item_tasks = [
        create_carousel_item_container(instagram_user_id, access_token, url)
        for url in image_urls
    ]
    children_ids = await asyncio.gather(*item_tasks)

    # Step 2 — create parent carousel container
    carousel_id = await create_carousel_container(
        instagram_user_id, access_token, list(children_ids), caption
    )

    # Step 3 — publish
    result = await publish_media_container(
        instagram_user_id, access_token, carousel_id
    )
    return result["id"]


# ═══════════════════════════════════════════════════════════════════════════════
# Reels Publishing
# ═══════════════════════════════════════════════════════════════════════════════

async def create_reel_container(
    instagram_user_id: str,
    access_token: str,
    video_url: str,
    caption: str,
    cover_url: str = "",
    share_to_feed: bool = True,
) -> str:
    """
    Create a Reel media container.
    video_url must be a publicly accessible MP4 URL.
    Returns: container_id
    """
    params: dict[str, Any] = {
        "media_type":    "REELS",
        "video_url":     video_url,
        "caption":       caption,
        "share_to_feed": "true" if share_to_feed else "false",
        "access_token":  access_token,
    }
    if cover_url:
        params["cover_url"] = cover_url

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{GRAPH_BASE}/{instagram_user_id}/media",
            params=params,
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def poll_container_status(
    container_id: str,
    access_token: str,
) -> str:
    """
    Poll container status until FINISHED or ERROR.
    Reels/containers must finish server-side processing before they can be published.
    Returns: status string (FINISHED | ERROR | IN_PROGRESS | EXPIRED | PUBLISHED)
    """
    import asyncio as _asyncio

    async with httpx.AsyncClient(timeout=15.0) as client:
        for attempt in range(CONTAINER_POLL_MAX_ATTEMPTS):
            resp = await client.get(
                f"{GRAPH_BASE}/{container_id}",
                params={
                    "fields":       "status_code,status",
                    "access_token": access_token,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status_code") or data.get("status", "IN_PROGRESS")
            logger.info("Container %s status: %s (attempt %d)", container_id, status, attempt + 1)

            if status == "FINISHED":
                return "FINISHED"
            if status == "ERROR":
                raise RuntimeError(f"Instagram container processing failed: {data.get('status')}")

            await _asyncio.sleep(CONTAINER_POLL_INTERVAL_SEC)

    raise TimeoutError(f"Container {container_id} did not finish within {CONTAINER_POLL_MAX_ATTEMPTS * CONTAINER_POLL_INTERVAL_SEC}s")


async def publish_reel(
    instagram_user_id: str,
    access_token: str,
    video_url: str,
    caption: str,
    cover_url: str = "",
    share_to_feed: bool = True,
) -> str:
    """
    Full Reel publishing flow with status polling.
    Returns: Instagram post ID
    """
    container_id = await create_reel_container(
        instagram_user_id, access_token, video_url, caption, cover_url, share_to_feed
    )
    await poll_container_status(container_id, access_token)
    result = await publish_media_container(
        instagram_user_id, access_token, container_id
    )
    return result["id"]


# ═══════════════════════════════════════════════════════════════════════════════
# Story Publishing
# ═══════════════════════════════════════════════════════════════════════════════

async def publish_photo_story(
    instagram_user_id: str,
    access_token: str,
    image_url: str,
) -> str:
    """
    Publish a photo Story.
    Returns: Story media ID
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create story container
        resp = await client.post(
            f"{GRAPH_BASE}/{instagram_user_id}/media",
            params={
                "media_type":   "STORIES",
                "image_url":    image_url,
                "access_token": access_token,
            },
        )
        resp.raise_for_status()
        container_id = resp.json()["id"]

    result = await publish_media_container(
        instagram_user_id, access_token, container_id
    )
    return result["id"]


async def publish_video_story(
    instagram_user_id: str,
    access_token: str,
    video_url: str,
) -> str:
    """
    Publish a video Story.
    Returns: Story media ID
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{GRAPH_BASE}/{instagram_user_id}/media",
            params={
                "media_type":   "STORIES",
                "video_url":    video_url,
                "access_token": access_token,
            },
        )
        resp.raise_for_status()
        container_id = resp.json()["id"]

    await poll_container_status(container_id, access_token)
    result = await publish_media_container(
        instagram_user_id, access_token, container_id
    )
    return result["id"]


# ═══════════════════════════════════════════════════════════════════════════════
# Post-Level Insights
# ═══════════════════════════════════════════════════════════════════════════════

async def get_post_insights(
    post_id: str,
    access_token: str,
) -> dict:
    """
    Get detailed metrics for a published feed post.
    Returns: impressions, reach, likes, comments, saved, shares, engagement, plays
    """
    metrics = [
        "impressions", "reach",
        "likes", "comments", "saved", "shares",
        "total_interactions",
    ]
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{GRAPH_BASE}/{post_id}/insights",
            params={
                "metric":       ",".join(metrics),
                "access_token": access_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        result: dict[str, Any] = {}
        for item in data.get("data", []):
            values = item.get("values") or item.get("value")
            if isinstance(values, list) and values:
                result[item["name"]] = values[0].get("value", 0)
            elif isinstance(values, (int, float)):
                result[item["name"]] = values
            else:
                result[item["name"]] = 0

        # Compute engagement rate if reach is available
        if result.get("reach", 0) > 0:
            interactions = result.get("total_interactions", 0)
            result["engagement_rate"] = round((interactions / result["reach"]) * 100, 2)
        else:
            result["engagement_rate"] = 0.0

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# Account-Level Insights
# ═══════════════════════════════════════════════════════════════════════════════

async def get_account_insights(
    instagram_user_id: str,
    access_token: str,
    period: str = "month",
) -> dict:
    """
    Get account-level analytics (requires instagram_manage_insights permission).
    period: 'day' | 'week' | 'month'
    Returns: followers_count, impressions, reach, profile_views, website_clicks
    """
    metrics = [
        "impressions",
        "reach",
        "profile_views",
        "website_clicks",
        "follower_count",
    ]
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{GRAPH_BASE}/{instagram_user_id}/insights",
            params={
                "metric":       ",".join(metrics),
                "period":       period,
                "access_token": access_token,
            },
        )
        resp.raise_for_status()
        raw = resp.json().get("data", [])
        result: dict[str, Any] = {}
        for item in raw:
            values = item.get("values", [])
            if values:
                # sum over period if multiple time buckets
                result[item["name"]] = sum(v.get("value", 0) for v in values)
            else:
                result[item["name"]] = 0
        return result


async def get_all_published_posts(
    instagram_user_id: str,
    access_token: str,
    limit: int = 50,
) -> list[dict]:
    """
    Retrieve the user's published feed posts.
    Returns list of: {id, caption, media_type, timestamp, permalink}
    """
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            f"{GRAPH_BASE}/{instagram_user_id}/media",
            params={
                "fields":       "id,caption,media_type,timestamp,permalink,thumbnail_url,media_url",
                "limit":        limit,
                "access_token": access_token,
            },
        )
        resp.raise_for_status()
        return resp.json().get("data", [])


# ═══════════════════════════════════════════════════════════════════════════════
# Comments & Replies
# ═══════════════════════════════════════════════════════════════════════════════

async def reply_to_comment(
    comment_id: str,
    access_token: str,
    reply_text: str,
) -> dict:
    """Post a reply to an Instagram comment."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{GRAPH_BASE}/{comment_id}/replies",
            params={"message": reply_text, "access_token": access_token},
        )
        resp.raise_for_status()
        return resp.json()


async def get_media_comments(
    media_id: str,
    access_token: str,
    limit: int = 50,
) -> list[dict]:
    """Retrieve comments on a media object."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{GRAPH_BASE}/{media_id}/comments",
            params={
                "fields":       "id,text,timestamp,username",
                "limit":        limit,
                "access_token": access_token,
            },
        )
        resp.raise_for_status()
        return resp.json().get("data", [])


async def hide_comment(comment_id: str, access_token: str, hide: bool = True) -> dict:
    """Hide or unhide an Instagram comment."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{GRAPH_BASE}/{comment_id}",
            params={"hide": str(hide).lower(), "access_token": access_token},
        )
        resp.raise_for_status()
        return resp.json()
