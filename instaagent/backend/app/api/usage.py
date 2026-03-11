# backend/app/api/usage.py
# GET /api/v1/usage — Monthly usage stats for the logged-in user

from fastapi import APIRouter, Depends
from datetime import datetime
from app.middleware.auth import get_current_user
from app.db.supabase import get_supabase
from app.middleware.plan_check import PLAN_LIMITS

router = APIRouter()


@router.get("", summary="Get usage stats for current month")
async def get_usage(current_user: dict = Depends(get_current_user)):
    """
    Returns:
    - posts used this month
    - posts remaining
    - plan limit
    - breakdown by API service (Claude, Remove.bg, etc.)
    - total cost this month in paise
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    plan = current_user.get("plan", "free")
    month_year = datetime.now().strftime("%Y-%m")

    # Count posts this month
    posts_result = (
        supabase.table("usage_logs")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("action", "post_created")
        .eq("month_year", month_year)
        .execute()
    )
    posts_used = posts_result.count or 0

    # Get all usage logs for cost breakdown
    logs_result = (
        supabase.table("usage_logs")
        .select("api_service, cost_paise, tokens_in, tokens_out")
        .eq("user_id", user_id)
        .eq("month_year", month_year)
        .execute()
    )

    # Aggregate by service
    breakdown = {}
    total_cost = 0
    for log in (logs_result.data or []):
        service = log.get("api_service") or "other"
        breakdown[service] = breakdown.get(service, 0) + (log.get("cost_paise") or 0)
        total_cost += log.get("cost_paise") or 0

    limit = PLAN_LIMITS.get(plan, 5)

    return {
        "month": month_year,
        "plan": plan,
        "posts_used": posts_used,
        "posts_limit": limit,
        "posts_remaining": max(0, limit - posts_used),
        "total_cost_paise": total_cost,
        "total_cost_rupees": round(total_cost / 100, 2),
        "breakdown_by_service": breakdown,
    }


@router.get("/analytics", summary="Post performance data for charts")
async def get_analytics(
    days: int = 7,
    current_user: dict = Depends(get_current_user),
):
    """Returns daily reach, likes, comments for the last N days."""
    supabase = get_supabase()
    user_id = current_user["id"]

    result = (
        supabase.table("posts")
        .select("posted_at, likes_count, comments_count, reach, product_name, status")
        .eq("user_id", user_id)
        .eq("status", "posted")
        .order("posted_at", desc=True)
        .limit(50)
        .execute()
    )

    return {
        "posts": result.data or [],
        "total_reach": sum(p.get("reach", 0) for p in (result.data or [])),
        "total_likes": sum(p.get("likes_count", 0) for p in (result.data or [])),
        "total_comments": sum(p.get("comments_count", 0) for p in (result.data or [])),
    }
