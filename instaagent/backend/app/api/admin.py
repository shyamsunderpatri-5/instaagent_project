# backend/app/api/admin.py
# ─────────────────────────────────────────────────────────────────────────────
# Admin API — Dashboard stats, user management, admin promotion
# Admin creation flow:
#   POST /api/v1/admin/promote  (requires X-Admin-Secret header)
#   This lets you bootstrap the first admin without being an admin already.
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from app.db.supabase import get_supabase
from app.middleware.auth import get_current_user
from app.config import settings
import logging
from datetime import datetime

log = logging.getLogger(__name__)
router = APIRouter()


# ─── Guard helpers ────────────────────────────────────────────────────────────

def require_admin(user: dict = Depends(get_current_user)):
    """Require the requesting user to have is_admin=True."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_admin_secret(x_admin_secret: str = Header(default="")):
    """Require the X-Admin-Secret header to match ADMIN_SECRET in .env.
    Used to bootstrap the very first admin account without needing to be admin.
    """
    if not settings.ADMIN_SECRET:
        raise HTTPException(
            500,
            "ADMIN_SECRET is not configured. Add it to your .env file to enable admin promotion."
        )
    if x_admin_secret != settings.ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin secret")


# ─── Promote user to admin ────────────────────────────────────────────────────

class PromoteRequest(BaseModel):
    email: str


@router.post("/promote", summary="Bootstrap: promote a user to admin (requires X-Admin-Secret header)")
async def promote_to_admin(
    body: PromoteRequest,
    _: None = Depends(require_admin_secret),
):
    """
    Promotes any registered user to admin.
    
    **How to create the first admin:**
    1. Add `ADMIN_SECRET=your_secret_key` to backend/.env
    2. Run:
       ```
       curl -X POST http://localhost:8000/api/v1/admin/promote \\
         -H "Content-Type: application/json" \\
         -H "X-Admin-Secret: your_secret_key" \\
         -d '{"email": "your@email.com"}'
       ```
    3. Log in as that user — the Admin Panel will appear in the sidebar.
    """
    supabase = get_supabase()
    result = (
        supabase.table("users")
        .select("id, email, full_name, is_admin")
        .eq("email", body.email.lower().strip())
        .execute()
    )

    if not result.data:
        raise HTTPException(404, f"No user found with email: {body.email}")

    user = result.data[0]

    if user.get("is_admin"):
        return {
            "promoted": False,
            "message": f"{user['email']} is already an admin.",
            "user": {"email": user["email"], "full_name": user["full_name"]},
        }

    supabase.table("users").update({"is_admin": True}).eq("id", user["id"]).execute()
    log.info("User %s promoted to admin.", user["email"])

    return {
        "promoted": True,
        "message": f"✅ {user['full_name']} ({user['email']}) is now an admin. They will see the Admin Panel on next login.",
        "user": {"email": user["email"], "full_name": user["full_name"]},
    }


# ─── Demote admin ─────────────────────────────────────────────────────────────

@router.post("/demote", summary="Remove admin access from a user")
async def demote_admin(
    body: PromoteRequest,
    admin: dict = Depends(require_admin),
):
    """Remove admin privileges from a user. Requires caller to be admin."""
    supabase = get_supabase()
    result = (
        supabase.table("users")
        .select("id, email, full_name")
        .eq("email", body.email.lower().strip())
        .execute()
    )

    if not result.data:
        raise HTTPException(404, f"No user found with email: {body.email}")

    user = result.data[0]

    if user["id"] == admin["id"]:
        raise HTTPException(400, "You cannot remove your own admin access.")

    supabase.table("users").update({"is_admin": False}).eq("id", user["id"]).execute()
    return {"demoted": True, "message": f"{user['email']} admin access removed."}


# ─── Dashboard stats ──────────────────────────────────────────────────────────

@router.get("/dashboard", summary="Global platform stats")
async def get_admin_stats(admin: dict = Depends(require_admin)):
    supabase = get_supabase()

    users_res = supabase.table("users").select("count", count="exact").execute()
    total_users = users_res.count if users_res else 0

    posts_res = supabase.table("posts").select("count", count="exact").execute()
    total_posts = posts_res.count if posts_res else 0

    plans_res = (
        supabase.table("subscriptions").select("plan_id").eq("status", "active").execute()
    )
    plans = plans_res.data if plans_res else []

    ig_res = (
        supabase.table("users")
        .select("count", count="exact")
        .not_.is_("instagram_token", "null")
        .execute()
    )
    ig_connected = ig_res.count if ig_res else 0

    return {
        "stats": {
            "total_users": total_users,
            "total_posts": total_posts,
            "active_subscriptions": len(plans),
            "instagram_connected": ig_connected,
        }
    }


# ─── User list ────────────────────────────────────────────────────────────────

@router.get("/users", summary="List all sellers")
async def list_users(admin: dict = Depends(require_admin)):
    supabase = get_supabase()
    res = (
        supabase.table("users")
        .select("id, email, full_name, plan, is_admin, instagram_username, telegram_id, created_at, is_active")
        .order("created_at", desc=True)
        .limit(200)
        .execute()
    )
    return {"users": res.data if res else []}


# ─── Broadcast ────────────────────────────────────────────────────────────────

@router.post("/broadcast", summary="Send platform-wide Telegram alert")
async def send_broadcast(message: str, admin: dict = Depends(require_admin)):
    try:
        from app.workers.telegram_broadcast import broadcast_to_all_users_task
        broadcast_to_all_users_task.delay(message=message)
        return {"queued": True, "message": f"Broadcast queued: {message[:80]}"}
    except Exception as e:
        raise HTTPException(500, f"Broadcast failed: {e}")


# ─── User Actions (Ban/Reset Quota) ──────────────────────────────────────────

@router.post("/users/{user_id}/ban", summary="Activate/Deactivate a user account")
async def ban_user(user_id: str, admin: dict = Depends(require_admin)):
    """Blocks a user from logging in."""
    supabase = get_supabase()
    
    # Check if target is admin (can't ban admins easily)
    target = supabase.table("users").select("id, is_admin, is_active").eq("id", user_id).single().execute()
    if not target.data:
        raise HTTPException(404, "User not found")
    
    if target.data.get("is_admin") and target.data.get("is_active"):
        raise HTTPException(400, "Cannot ban an active administrator.")

    new_status = not target.data.get("is_active", True)
    supabase.table("users").update({"is_active": new_status}).eq("id", user_id).execute()
    
    action = "activated" if new_status else "banned"
    log.info("Admin %s %s user %s", admin["email"], action, user_id)
    
    return {"success": True, "is_active": new_status, "message": f"User {action} successfully."}


@router.post("/users/{user_id}/reset-quota", summary="Reset a user's monthly post usage")
async def reset_user_quota(user_id: str, admin: dict = Depends(require_admin)):
    """Reset the usage count for a specific user."""
    supabase = get_supabase()
    current_month = datetime.now().strftime("%Y-%m")
    
    # 1. Clear detailed usage logs for the current month
    supabase.table("usage_logs")\
            .delete()\
            .eq("user_id", user_id)\
            .eq("month_year", current_month)\
            .execute()
    
    # 2. Reset the summary count in monthly_usage table if it exists
    # We use a try/except or just execute assuming it might be there
    try:
        supabase.table("monthly_usage")\
                .update({"posts_used": 0})\
                .eq("user_id", user_id)\
                .eq("month_year", current_month)\
                .execute()
    except Exception as e:
        log.warning("Could not update monthly_usage for %s: %s", user_id, e)

    log.info("Admin %s reset quota for user %s for %s", admin["email"], user_id, current_month)
    return {"success": True, "message": f"Usage quota reset for {current_month}."}
