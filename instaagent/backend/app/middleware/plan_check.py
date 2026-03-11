# backend/app/middleware/plan_check.py
from fastapi import HTTPException, Depends
from datetime import datetime
from app.db.supabase import get_supabase
from app.middleware.auth import get_current_user

PLAN_LIMITS = {
    "free": 5,
    "starter": 30,
    "growth": 90,
    "agency": 300,
}


async def check_post_quota(current_user: dict = Depends(get_current_user)):
    """Check if user has remaining post quota for this month."""
    supabase = get_supabase()
    user_id = current_user["id"]
    plan = current_user.get("plan", "free")

    # Check if in active trial
    trial_end = current_user.get("trial_end")
    if trial_end and not current_user.get("trial_used"):
        trial_end_dt = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))
        if datetime.utcnow().replace(tzinfo=trial_end_dt.tzinfo) < trial_end_dt:
            # Mark trial as used on first post
            supabase.table("users").update({"trial_used": True}).eq("id", user_id).execute()
            return  # Trial users get growth-level quota

    # Count posts this month
    month_year = datetime.now().strftime("%Y-%m")
    result = (
        supabase.table("usage_logs")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("action", "post_created")
        .eq("month_year", month_year)
        .execute()
    )

    posts_this_month = result.count or 0
    limit = PLAN_LIMITS.get(plan, 5)

    if posts_this_month >= limit:
        raise HTTPException(
            403,
            f"Monthly post limit reached ({posts_this_month}/{limit}). "
            f"Upgrade your plan at /billing to post more.",
        )


async def get_quota_info(user_id: str, plan: str):
    """Utility to get posts used, limit, and a warning if near limit."""
    supabase = get_supabase()
    month_year = datetime.now().strftime("%Y-%m")
    result = supabase.table("usage_logs").select("id", count="exact").eq("user_id", user_id).eq("action", "post_created").eq("month_year", month_year).execute()
    
    used = result.count or 0
    limit = PLAN_LIMITS.get(plan, 5)
    remaining = max(0, limit - used)
    
    return {
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "warning": remaining <= 2 and remaining > 0,
        "critical": remaining == 0
    }
