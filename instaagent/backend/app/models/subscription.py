# backend/app/models/subscription.py
# Pydantic models for Subscription API requests and responses

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SubscriptionCreate(BaseModel):
    """Request body for creating a new subscription."""
    plan: str   # starter | growth | agency


class SubscriptionResponse(BaseModel):
    """Full subscription object returned in API responses."""
    id: str
    user_id: str
    plan: str
    status: str                             # active | cancelled | expired | paused | pending
    razorpay_sub_id: Optional[str] = None
    razorpay_cust_id: Optional[str] = None
    amount_paise: int
    billing_cycle: str = "monthly"
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubscriptionStatusResponse(BaseModel):
    """Returned by GET /subscription/current."""
    plan: str
    subscription: Optional[SubscriptionResponse] = None


class CreateSubscriptionResponse(BaseModel):
    """Returned after creating a Razorpay subscription — frontend uses this to open checkout."""
    subscription_id: str
    razorpay_key: str
    plan: str
    amount_paise: int
    user: dict
    message: str


class CancelSubscriptionResponse(BaseModel):
    """Returned after cancelling a subscription."""
    cancelled: bool
    message: str
    access_until: Optional[datetime] = None
