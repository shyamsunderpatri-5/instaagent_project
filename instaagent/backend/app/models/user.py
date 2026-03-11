# backend/app/models/user.py
# Pydantic models for User API requests and responses

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """Used when registering a new user."""
    email: EmailStr
    password: str
    full_name: str
    phone: str = ""
    city: str = ""
    language: str = "hi"   # hi, te, ta, kn, mr, en


class UserLogin(BaseModel):
    """Used when logging in."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Safe user object returned in API responses — no password_hash."""
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    city: Optional[str] = None
    language: str = "hi"
    plan: str = "free"
    instagram_username: Optional[str] = None
    instagram_id: Optional[str] = None
    telegram_id: Optional[int] = None
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    trial_used: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Used when updating user profile settings."""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    language: Optional[str] = None
    telegram_id: Optional[int] = None
    preferred_post_time: Optional[str] = None


class AuthResponse(BaseModel):
    """Returned by /register and /login."""
    token: str
    user: UserResponse
    message: Optional[str] = None
