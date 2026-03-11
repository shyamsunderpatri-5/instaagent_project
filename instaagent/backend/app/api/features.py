# backend/app/api/features.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Feature Flags Public API
# GET /api/v1/features  →  returns all feature flags (no auth required)
# Frontend reads this on load and conditionally renders tabs/buttons.
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("", summary="Return all feature flags (public endpoint)")
async def get_features():
    """
    Returns the feature flag dict so the frontend can
    show/hide tabs and buttons without a code deploy.

    Example response:
    {
      "enable_ai_caption": true,
      "enable_reels": false,
      ...
    }
    """
    return {
        "ok":       True,
        "features": settings.features,
        "free_trial_posts": settings.FREE_TRIAL_POSTS,
        "telegram_bot_username": settings.TELEGRAM_BOT_USERNAME,
    }
