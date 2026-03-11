# backend/app/services/payment_service.py
# Razorpay payment service — subscription management helpers
# Place this at: backend/app/services/payment_service.py

import razorpay
import hmac
import hashlib
from app.config import settings

# Razorpay client — initialized once
_client = None


def get_razorpay_client() -> razorpay.Client:
    """Get cached Razorpay client."""
    global _client
    if _client is None:
        _client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    return _client


def verify_webhook_signature(body_bytes: bytes, signature: str) -> bool:
    """
    Verify Razorpay webhook HMAC-SHA256 signature.
    Call this before processing any webhook event.

    Returns True if signature is valid, False if tampered/invalid.
    """
    expected = hmac.new(
        key=settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        msg=body_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def create_customer(name: str, email: str, phone: str = "") -> dict:
    """
    Create or fetch existing Razorpay customer by email.
    Returns customer dict with 'id' field.
    """
    client = get_razorpay_client()
    return client.customer.create({
        "name":         name,
        "email":        email,
        "contact":      phone,
        "fail_existing": "0",   # Returns existing customer if email already registered
    })


def create_subscription(plan_id: str, customer_id: str, total_count: int = 12) -> dict:
    """
    Create a recurring monthly subscription in Razorpay.

    Args:
        plan_id: Razorpay plan ID (create plans in Razorpay dashboard first)
        customer_id: Razorpay customer ID from create_customer()
        total_count: Number of billing cycles (12 = 1 year)

    Returns:
        Razorpay subscription dict with 'id', 'status', 'short_url'
    """
    client = get_razorpay_client()
    return client.subscription.create({
        "plan_id":     plan_id,
        "customer_id": customer_id,
        "total_count": total_count,
        "quantity":    1,
    })


def cancel_subscription(subscription_id: str, cancel_at_cycle_end: bool = True) -> dict:
    """
    Cancel a Razorpay subscription.

    Args:
        cancel_at_cycle_end: If True, user keeps access until billing period ends.
                             If False, cancelled immediately.
    """
    client = get_razorpay_client()
    return client.subscription.cancel(subscription_id, {
        "cancel_at_cycle_end": 1 if cancel_at_cycle_end else 0,
    })


def fetch_subscription(subscription_id: str) -> dict:
    """Fetch subscription details from Razorpay."""
    client = get_razorpay_client()
    return client.subscription.fetch(subscription_id)


def fetch_payment(payment_id: str) -> dict:
    """Fetch payment details from Razorpay."""
    client = get_razorpay_client()
    return client.payment.fetch(payment_id)


# ─── Plan pricing (single source of truth) ───────────────────────────────────
PLAN_PRICES = {
    "starter": {
        "amount_paise":     59900,      # Rs 599/month
        "name":             "Starter",
        "posts_per_month":  30,
        "razorpay_plan_id": "",         # ← Fill this from Razorpay dashboard
    },
    "growth": {
        "amount_paise":     99900,      # Rs 999/month
        "name":             "Growth",
        "posts_per_month":  90,
        "razorpay_plan_id": "",         # ← Fill this from Razorpay dashboard
    },
    "agency": {
        "amount_paise":     199900,     # Rs 1999/month
        "name":             "Agency",
        "posts_per_month":  300,
        "razorpay_plan_id": "",         # ← Fill this from Razorpay dashboard
    },
}


def get_plan_config(plan: str) -> dict:
    """Get price and config for a plan. Raises ValueError if plan not found."""
    config = PLAN_PRICES.get(plan.lower())
    if not config:
        raise ValueError(f"Unknown plan '{plan}'. Valid plans: {list(PLAN_PRICES.keys())}")
    return config