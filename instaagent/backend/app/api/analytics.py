# backend/app/api/analytics.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Enterprise Analytics API Router
# Endpoints: dashboard, per-post breakdown, period reports, account insights
# All data is live + supplemented from DB cache.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.supabase import get_supabase
from app.middleware.auth import get_current_user
from app.services.analytics_service import (
    get_user_dashboard_stats,
    get_weekly_report,
    get_monthly_report,
    snapshot_account_metrics,
    sync_post_insights,
)

router = APIRouter()


# ── GET /api/v1/analytics/dashboard ──────────────────────────────────────────
@router.get("/dashboard", summary="Full analytics dashboard for the logged-in user")
async def analytics_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Returns aggregated stats:
    - total_posts, total_likes, total_comments, total_reach, total_saved, total_shares
    - avg_engagement_rate
    - top_posts (top 3 by engagement rate)
    """
    stats = await get_user_dashboard_stats(current_user["id"])
    return {"ok": True, "data": stats}


# ── GET /api/v1/analytics/posts ───────────────────────────────────────────────
@router.get("/posts", summary="Per-post metrics breakdown")
async def analytics_posts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, le=100),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns all posted items with live metrics (likes, reach, engagement).
    Metrics are synced from Instagram Graph API on demand.
    """
    supabase = get_supabase()
    offset   = (page - 1) * page_size

    result = (
        supabase.table("posts")
        .select(
            "id, product_name, status, likes_count, comments_count, reach, "
            "shares, engagement_rate, posted_at, instagram_permalink, edited_photo_url"
        )
        .eq("user_id", current_user["id"])
        .eq("status", "posted")
        .order("posted_at", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )
    return {
        "ok":        True,
        "posts":     result.data,
        "page":      page,
        "page_size": page_size,
    }


# ── POST /api/v1/analytics/posts/{post_id}/sync ───────────────────────────────
@router.post("/posts/{post_id}/sync", summary="Force-sync live metrics for a post")
async def sync_post_metrics(
    post_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Fetches the latest insights from Instagram Graph API for a specific post
    and persists them in the DB. Returns updated metrics.
    """
    supabase = get_supabase()
    result   = (
        supabase.table("posts")
        .select("*")
        .eq("id", post_id)
        .eq("user_id", current_user["id"])
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Post not found.")

    post = result.data
    if not post.get("instagram_post_id"):
        raise HTTPException(400, "Post has not been published to Instagram yet.")

    await sync_post_insights(post)

    # Re-fetch updated post
    updated = (
        supabase.table("posts")
        .select("id, likes_count, comments_count, reach, shares, engagement_rate")
        .eq("id", post_id)
        .single()
        .execute()
    )
    return {"ok": True, "data": updated.data}


# ── GET /api/v1/analytics/report ─────────────────────────────────────────────
@router.get("/report", summary="Weekly or monthly performance report")
async def analytics_report(
    period: Literal["weekly", "monthly"] = Query(default="weekly"),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns a formatted performance report for the specified period.
    period: 'weekly' (last 7 days) | 'monthly' (last 30 days)
    """
    if period == "weekly":
        report = await get_weekly_report(current_user)
    else:
        report = await get_monthly_report(current_user)

    return {"ok": True, "period": period, "report": report}


# ── GET /api/v1/analytics/account ────────────────────────────────────────────
@router.get("/account", summary="Live account-level Instagram insights")
async def analytics_account(
    period: Literal["day", "week", "month"] = Query(default="month"),
    current_user: dict = Depends(get_current_user),
):
    """
    Fetches account-level metrics directly from Instagram Graph API:
    - impressions, reach, profile_views, website_clicks, follower_count
    Requires instagram_manage_insights permission.
    """
    if not current_user.get("instagram_token"):
        raise HTTPException(400, "Instagram is not connected. Please connect via /settings.")

    from app.services.instagram_service import get_account_insights
    try:
        insights = await get_account_insights(
            current_user["instagram_id"],
            current_user["instagram_token"],
            period=period,
        )
    except Exception as e:
        raise HTTPException(502, f"Instagram API error: {str(e)}")

    return {"ok": True, "period": period, "data": insights}


# ── POST /api/v1/analytics/snapshot ──────────────────────────────────────────
@router.post("/snapshot", summary="Take an account metrics snapshot (for trend tracking)")
async def take_snapshot(current_user: dict = Depends(get_current_user)):
    """
    Saves a point-in-time snapshot of account metrics to the
    analytics_snapshots table for historical trend analysis.
    """
    await snapshot_account_metrics(current_user)
    return {"ok": True, "message": "Snapshot saved."}


# ── GET /api/v1/analytics/snapshots ──────────────────────────────────────────
@router.get("/snapshots", summary="Historical metric snapshots for trend view")
async def list_snapshots(
    limit: int = Query(default=30, le=90),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns the last N daily snapshots for the user.
    Use this to render a follower growth / reach trend chart on the dashboard.
    """
    supabase = get_supabase()
    try:
        result = (
            supabase.table("analytics_snapshots")
            .select("*")
            .eq("user_id", current_user["id"])
            .order("snapshotted_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"ok": True, "snapshots": result.data or []}
    except Exception:
        # Table may not exist yet — return empty list instead of 500
        return {"ok": True, "snapshots": []}
