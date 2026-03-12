# backend/app/api/subscription.py
# Subscription API — Create, cancel, and check Razorpay subscriptions

from fastapi import APIRouter, Depends, HTTPException
from app.middleware.auth import get_current_user
from app.db.supabase import get_supabase
from app.config import settings
from app.models.subscription import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionStatusResponse,
    CreateSubscriptionResponse,
    CancelSubscriptionResponse,
)

router = APIRouter()


def _build_plan_config():
    """Build plan config dynamically from settings (reads from .env)."""
    return {
        "free": {
            "amount_paise": 0,
            "price": 0,
            "name": "Free",
            "posts_limit": settings.PLAN_FREE_POSTS,
            "razorpay_plan_id": "",
            "features_list": [
                f"{settings.PLAN_FREE_POSTS} posts/month",
                "AI captions",
                "Background removal",
                "Telegram bot",
            ],
        },
        "starter": {
            "amount_paise": settings.PLAN_STARTER_PRICE * 100,
            "price": settings.PLAN_STARTER_PRICE,
            "name": "Starter",
            "posts_limit": settings.PLAN_STARTER_POSTS,
            "razorpay_plan_id": "",   # Fill after creating in Razorpay dashboard
            "features_list": [
                f"{settings.PLAN_STARTER_POSTS} posts/month",
                "All Free features",
                "Studio enhancement",
                "Priority processing",
            ],
        },
        "growth": {
            "amount_paise": settings.PLAN_GROWTH_PRICE * 100,
            "price": settings.PLAN_GROWTH_PRICE,
            "name": "Growth",
            "posts_limit": settings.PLAN_GROWTH_POSTS,
            "razorpay_plan_id": "",
            "features_list": [
                f"{settings.PLAN_GROWTH_POSTS} posts/month",
                "All Starter features",
                "Carousel duos",
                "Scheduled posting",
            ],
        },
        "agency": {
            "amount_paise": settings.PLAN_AGENCY_PRICE * 100,
            "price": settings.PLAN_AGENCY_PRICE,
            "name": "Agency",
            "posts_limit": settings.PLAN_AGENCY_POSTS,
            "razorpay_plan_id": "",
            "features_list": [
                f"{settings.PLAN_AGENCY_POSTS} posts/month",
                "All Growth features",
                "Multiple accounts",
                "Priority support",
            ],
        },
        "aggregator": {
            "amount_paise": settings.PLAN_AGGREGATOR_PRICE * 100,
            "price": settings.PLAN_AGGREGATOR_PRICE,
            "name": "Aggregator",
            "posts_limit": 150,
            "razorpay_plan_id": "",
            "features_list": [
                "Track Competitors",
                "AI Trend Analysis",
                "Daily Sync",
                "150 Posts/month Tracking",
            ],
        },
    }


PLAN_CONFIG = _build_plan_config()  # aliases for backward compat


# ─── GET /api/v1/subscription/plans ──────────────────────────────────────────
@router.get("/plans", summary="Get all subscription plans with current prices")
async def get_plans():
    """Returns all plans with prices sourced from .env/config."""
    config = _build_plan_config()
    return {
        "plans": [
            {
                "id": plan_id,
                "name": plan["name"],
                "price": plan["price"],
                "posts_limit": plan["posts_limit"],
                "features_list": plan.get("features_list", []),
            }
            for plan_id, plan in config.items()
        ]
    }



# ─── GET /api/v1/subscription/current ────────────────────────────────────────
@router.get("/current", response_model=SubscriptionStatusResponse, summary="Get current plan and subscription")
async def get_current_subscription(current_user: dict = Depends(get_current_user)):
    """
    Returns the user's current plan and active subscription details.
    """
    supabase = get_supabase()

    result = (
        supabase.table("subscriptions")
        .select("*")
        .eq("user_id", current_user["id"])
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    subscription = result.data[0] if result.data else None

    return SubscriptionStatusResponse(
        plan=current_user.get("plan", "free"),
        subscription=SubscriptionResponse(**subscription) if subscription else None,
    )


# ─── POST /api/v1/subscription/create ────────────────────────────────────────
@router.post("/create", response_model=CreateSubscriptionResponse, summary="Create a Razorpay subscription")
async def create_subscription(
    body: SubscriptionCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Creates a Razorpay subscription for the requested plan.
    Returns the subscription_id and razorpay_key — frontend uses these to open
    the Razorpay checkout modal.

    After payment succeeds, Razorpay calls /api/v1/webhooks/razorpay which
    activates the subscription and upgrades the user's plan automatically.
    """
    plan_key = body.plan.lower()
    if plan_key not in PLAN_CONFIG:
        raise HTTPException(400, f"Invalid plan '{body.plan}'. Choose: starter, growth, agency")

    plan = PLAN_CONFIG[plan_key]
    supabase = get_supabase()
    user_id = current_user["id"]

    # Cancel any existing active subscription first
    existing = (
        supabase.table("subscriptions")
        .select("razorpay_sub_id")
        .eq("user_id", user_id)
        .eq("status", "active")
        .execute()
    )
    if existing.data:
        raise HTTPException(
            400,
            "You already have an active subscription. Cancel it first before switching plans."
        )

    # Create or fetch Razorpay customer
    razorpay_cust_id = await _get_or_create_razorpay_customer(current_user)

    # Create Razorpay subscription
    razorpay_sub = await _create_razorpay_subscription(
        plan_id=plan["razorpay_plan_id"],
        customer_id=razorpay_cust_id,
        total_count=12,  # 12 months recurring
    )

    razorpay_sub_id = razorpay_sub["id"]

    # Save subscription record (status=pending — activated via webhook)
    sub_record = {
        "user_id":        user_id,
        "plan":           plan_key,
        "status":         "pending",
        "razorpay_sub_id": razorpay_sub_id,
        "razorpay_cust_id": razorpay_cust_id,
        "amount_paise":   plan["amount_paise"],
        "billing_cycle":  "monthly",
    }
    supabase.table("subscriptions").insert(sub_record).execute()

    return CreateSubscriptionResponse(
        subscription_id=razorpay_sub_id,
        razorpay_key=__import__("app.config", fromlist=["settings"]).settings.RAZORPAY_KEY_ID,
        plan=plan_key,
        amount_paise=plan["amount_paise"],
        user={
            "name":  current_user["full_name"],
            "email": current_user["email"],
            "phone": current_user.get("phone", ""),
        },
        message=f"Subscription created! Complete payment to activate {plan['name']} plan.",
    )


# ─── POST /api/v1/subscription/cancel ────────────────────────────────────────
@router.post("/cancel", response_model=CancelSubscriptionResponse, summary="Cancel current subscription")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    """
    Cancels the user's active Razorpay subscription.
    User keeps access until the end of the current billing period.
    Plan is downgraded to 'free' by the Razorpay webhook when the period ends.
    """
    supabase = get_supabase()
    user_id = current_user["id"]

    # Find active subscription
    result = (
        supabase.table("subscriptions")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(404, "No active subscription found.")

    sub = result.data[0]
    razorpay_sub_id = sub["razorpay_sub_id"]

    # Cancel in Razorpay (cancel_at_cycle_end=1 = user keeps access till period end)
    await _cancel_razorpay_subscription(razorpay_sub_id, cancel_at_cycle_end=True)

    # Update local record
    from datetime import datetime, timezone
    supabase.table("subscriptions").update({
        "status":       "cancelled",
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", sub["id"]).execute()

    # Access until end of current period
    access_until = sub.get("current_period_end")

    return CancelSubscriptionResponse(
        cancelled=True,
        message="Subscription cancelled. You keep full access until the end of this billing period.",
        access_until=access_until,
    )


# ─── Razorpay helpers ─────────────────────────────────────────────────────────

async def _get_or_create_razorpay_customer(user: dict) -> str:
    """Create a Razorpay customer and return customer ID."""
    import razorpay
    from app.config import settings

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    customer_data = client.customer.create({
        "name":    user["full_name"],
        "email":   user["email"],
        "contact": user.get("phone", ""),
        "fail_existing": "0",  # Return existing customer if email matches
    })

    return customer_data["id"]


async def _create_razorpay_subscription(
    plan_id: str,
    customer_id: str,
    total_count: int = 12,
) -> dict:
    """Create a recurring subscription in Razorpay."""
    import razorpay
    from app.config import settings

    if not plan_id:
        raise HTTPException(
            500,
            "Razorpay plan ID not configured. Add razorpay_plan_id to PLAN_CONFIG in subscription.py after creating plans in the Razorpay dashboard."
        )

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    subscription = client.subscription.create({
        "plan_id":     plan_id,
        "customer_id": customer_id,
        "total_count": total_count,
        "quantity":    1,
    })

    return subscription


async def _cancel_razorpay_subscription(
    subscription_id: str,
    cancel_at_cycle_end: bool = True,
) -> dict:
    """Cancel a subscription in Razorpay."""
    import razorpay
    from app.config import settings

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    return client.subscription.cancel(subscription_id, {
        "cancel_at_cycle_end": 1 if cancel_at_cycle_end else 0,
    })