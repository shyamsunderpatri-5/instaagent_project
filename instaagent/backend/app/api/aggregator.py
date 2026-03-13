# backend/app/api/aggregator.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.middleware.auth import get_current_user
from app.middleware.plan_check import check_aggregator_plan
from app.db.supabase import get_supabase
from app.models.aggregator import (
    AggregatorAccount, AggregatorAccountCreate, 
    AggregatedPost, AIInsightRequest, AIInsightResponse
)
from app.services.aggregator_service import aggregator_service
from app.workers.aggregator_worker import sync_aggregator_posts
from app.utils.crypto import encrypt_token
from app.config import settings
from app.db.redis_client import get_redis

MAX_ACCOUNTS_PER_USER = 10
INSIGHTS_COOLDOWN_SECONDS = 300 # 5 minutes

router = APIRouter()

@router.get("/accounts", response_model=List[AggregatorAccount])
async def list_accounts(current_user: dict = Depends(check_aggregator_plan)):
    supabase = get_supabase()
    resp = supabase.table("aggregator_accounts").select("*").eq("user_id", current_user["id"]).execute()
    return resp.data or []

@router.post("/accounts", response_model=AggregatorAccount)
async def add_account(
    account: AggregatorAccountCreate, 
    current_user: dict = Depends(check_aggregator_plan)
):
    supabase = get_supabase()
    user_id = str(current_user["id"])
    
    # Critical: Enforce per-user account limit
    existing = supabase.table("aggregator_accounts") \
        .select("id", count="exact") \
        .eq("user_id", user_id) \
        .execute()
    
    if (existing.count or 0) >= MAX_ACCOUNTS_PER_USER:
        raise HTTPException(
            status_code=429,
            detail=f"Maximum {MAX_ACCOUNTS_PER_USER} tracked accounts allowed. Remove one to add another."
        )

    acc_data = account.dict()
    acc_data["user_id"] = user_id
    if acc_data.get("access_token"):
        acc_data["access_token"] = encrypt_token(acc_data["access_token"])
    
    try:
        resp = supabase.table("aggregator_accounts").insert(acc_data).execute()
        new_acc = resp.data[0]
        # Trigger initial sync
        sync_aggregator_posts.delay(new_acc["id"])
        return new_acc
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add account: {str(e)}")

@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: UUID, 
    current_user: dict = Depends(check_aggregator_plan)
):
    supabase = get_supabase()
    # RLS should handle security, but we'll be explicit
    resp = supabase.table("aggregator_accounts").delete().eq("id", str(account_id)).eq("user_id", current_user["id"]).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Account not found or access denied")
    return {"message": "Account removed"}

@router.get("/posts", response_model=List[AggregatedPost])
async def get_posts(
    account_ids: Optional[List[UUID]] = Query(None),
    limit: int = Query(default=50, le=200, ge=1),
    current_user: dict = Depends(check_aggregator_plan)
):
    supabase = get_supabase()
    # High: Optimized to use direct user_id column on aggregated_posts (no join needed)
    query = supabase.table("aggregated_posts").select("*").eq("user_id", str(current_user["id"]))
    
    if account_ids:
        query = query.in_("aggregator_account_id", [str(aid) for aid in account_ids])
    
    query = query.order("posted_at", desc=True).limit(limit)
    
    resp = query.execute()
    return resp.data or []

@router.post("/insights", response_model=AIInsightResponse)
@router.post("/ai-analyze", response_model=AIInsightResponse, include_in_schema=False)
async def get_insights(
    req: AIInsightRequest, 
    current_user: dict = Depends(check_aggregator_plan)
):
    # Critical: Enforce AI insight rate limit (Redis-backed cooldown)
    redis_client = get_redis()
    user_id = str(current_user["id"])
    rate_key = f"aggregator_insights_cooldown:{user_id}"
    
    if redis_client.exists(rate_key):
        ttl = redis_client.ttl(rate_key)
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {ttl} seconds before generating insights again."
        )
    
    # Set cooldown
    redis_client.setex(rate_key, INSIGHTS_COOLDOWN_SECONDS, "1")
    
    insights = await aggregator_service.generate_ai_insights(req.account_ids, user_id=user_id)
    if "error" in insights:
        raise HTTPException(status_code=404, detail=insights["error"])
    return insights

# ── Admin Endpoints ──────────────────────────────────────────────────────────

@router.post("/refresh/{account_id}")
async def refresh_account(
    account_id: UUID, 
    current_user: dict = Depends(check_aggregator_plan)
):
    # Verify account belongs to user (RLS handles this but explicit check is safer for background tasks)
    supabase = get_supabase()
    resp = supabase.table("aggregator_accounts").select("id").eq("id", str(account_id)).eq("user_id", current_user["id"]).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Account not found")
        
    sync_aggregator_posts.delay(str(account_id))
    return {"message": "Sync triggered"}

@router.post("/posts/{post_id}/save")
async def save_aggregated_post(
    post_id: UUID, 
    current_user: dict = Depends(check_aggregator_plan)
):
    res = await aggregator_service.save_to_my_posts(post_id, current_user["id"])
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

# ── Admin Endpoints ──────────────────────────────────────────────────────────

@router.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    supabase = get_supabase()
    acc_count = supabase.table("aggregator_accounts").select("id", count="exact").execute().count
    post_count = supabase.table("aggregated_posts").select("id", count="exact").execute().count
    
    active_users_resp = supabase.table("users") \
        .select("id", count="exact") \
        .eq("plan", "aggregator") \
        .eq("is_active", True) \
        .execute()
    
    # Get user list with aggregator account counts
    users_with_accounts = supabase.rpc("get_aggregator_user_stats").execute()
    
    return {
        "total_tracked_accounts": acc_count,
        "total_aggregated_posts": post_count,
        "active_users": active_users_resp.count or 0,
        "user_details": users_with_accounts.data or []
    }

@router.get("/admin/trends")
async def get_admin_trends(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    trends = await aggregator_service.get_trending_hashtags(limit=20)
    return {"trends": trends}

@router.patch("/admin/posts/{post_id}")
async def moderate_post(
    post_id: UUID, 
    update_data: dict,
    current_user: dict = Depends(get_current_user)
):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    supabase = get_supabase()
    # Admins can update any post (e.g., hidden=true)
    # Note: If 'hidden' column is missing, run: ALTER TABLE aggregated_posts ADD COLUMN hidden BOOLEAN DEFAULT FALSE;
    resp = supabase.table("aggregated_posts").update(update_data).eq("id", str(post_id)).execute()
    return {"updated": True, "post": resp.data[0] if resp.data else None}

@router.delete("/admin/posts/{post_id}")
async def admin_delete_post(
    post_id: UUID, 
    current_user: dict = Depends(get_current_user)
):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    supabase = get_supabase()
    resp = supabase.table("aggregated_posts").delete().eq("id", str(post_id)).execute()
    return {"deleted": True, "post_id": post_id}
