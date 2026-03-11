# backend/app/api/auth.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Authentication API Router
#
# Endpoints:
#   POST /api/v1/auth/register          → Create new account
#   POST /api/v1/auth/login             → Email + password → JWT
#   GET  /api/v1/auth/me                → Authenticated user profile
#   PUT  /api/v1/auth/me                → Update profile fields
#   POST /api/v1/auth/change-password   → Change password (requires current)
#   POST /api/v1/auth/forgot-password   → Send 6-digit OTP to email
#   POST /api/v1/auth/verify-otp        → Verify OTP → one-time reset_token
#   POST /api/v1/auth/reset-password    → Set new password with reset_token
#
# Security notes:
#   • Passwords hashed with bcrypt (cost=12)
#   • JWT tokens signed with HS256, 72h expiry (configurable in config.py)
#   • OTPs: 6-digit, bcrypt-hashed before storage, 10-min Redis TTL
#   • Reset tokens: 64-char URL-safe, bcrypt-hashed, 15-min Redis TTL, single-use
#   • forgot-password always returns 200 regardless of email existence
#     (prevents email enumeration attacks)
#   • login uses constant-time comparison (bcrypt) to prevent timing attacks
#   • Max 5 OTP attempts enforced in Redis before forcing a new OTP request
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import logging
import re
import secrets
import smtplib
import threading
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import bcrypt
import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from pydantic import BaseModel, EmailStr, field_validator

from app.config import settings
from app.db.supabase import get_supabase
from app.middleware.auth import get_current_user

log = logging.getLogger(__name__)
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# REDIS CLIENT — reused from the project's existing Upstash/Redis setup
# ─────────────────────────────────────────────────────────────────────────────

from app.db.redis_client import get_redis


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

OTP_TTL_SECONDS         = 10 * 60          # 10 minutes
RESET_TOKEN_TTL_SECONDS = 15 * 60          # 15 minutes
MAX_OTP_ATTEMPTS        = 5                # lock after 5 wrong guesses
BCRYPT_ROUNDS           = 12               # bcrypt work factor

REDIS_KEY_OTP   = "ia:otp:{email}"        # OTP data for email
REDIS_KEY_TOKEN = "ia:rst:{token_prefix}" # reset token → email mapping

# ─────────────────────────────────────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    city: Optional[str] = None
    language: str = "hi"

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_policy(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("language")
    @classmethod
    def valid_language(cls, v: str) -> str:
        allowed = {"hi", "te", "ta", "kn", "mr", "en"}
        if v not in allowed:
            raise ValueError(f"Language must be one of: {', '.join(sorted(allowed))}")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    language: Optional[str] = None
    telegram_id: Optional[int] = None
    preferred_post_time: Optional[str] = None
    whatsapp_phone: Optional[str] = None   # Used by WA bot to identify the seller
    is_admin: Optional[bool] = None # Admin only



class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_policy(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("New password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("New password must contain at least one number")
        return v


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str

    @field_validator("otp")
    @classmethod
    def otp_digits(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP must be exactly 6 digits")
        return v


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_policy(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _hash(plain: str) -> str:
    """bcrypt-hash a plain-text string. Used for passwords, OTPs, and reset tokens."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def _verify(plain: str, hashed: str) -> bool:
    """Constant-time bcrypt comparison. Returns False on any exception."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def _issue_jwt(user_id: str) -> str:
    """Sign and return a JWT access token for the given user ID."""
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "exp": exp,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _generate_otp() -> str:
    """Return a cryptographically secure 6-digit OTP string."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _generate_reset_token() -> str:
    """Return a 64-character URL-safe random reset token."""
    return secrets.token_urlsafe(48)


def _safe_user_response(user: dict) -> dict:
    """Strip sensitive fields before returning user data to the client."""
    return {
        k: user.get(k)
        for k in (
            "id", "email", "full_name", "phone", "city", "language",
            "plan", "instagram_username", "is_active", "created_at",
            "telegram_id", "trial_start", "trial_end", "trial_used",
            "preferred_post_time", "is_admin", "whatsapp_phone",

        )
    }


# ─────────────────────────────────────────────────────────────────────────────
# OTP EMAIL SENDER — runs in a background thread (non-blocking)
# ─────────────────────────────────────────────────────────────────────────────

def _send_otp_email(to_email: str, to_name: str, otp: str) -> None:
    """
    Send a branded OTP email to the user.
    Runs in a daemon thread so the API response is not blocked by SMTP latency.
    Failures are logged but never surfaced to the API caller (prevents enumeration).
    """

    def _worker() -> None:
        try:
            subject = f"Your InstaAgent verification code: {otp}"

            html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#060A14;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#060A14;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="500" cellpadding="0" cellspacing="0"
               style="background:#0A1221;border:1px solid rgba(255,255,255,0.07);
                      border-radius:16px;overflow:hidden;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#2D4FD6,#6B8BFF);
                       padding:28px 36px;text-align:center;">
              <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
                <tr>
                  <td style="background:rgba(255,255,255,0.15);border-radius:10px;
                             width:40px;height:40px;text-align:center;
                             vertical-align:middle;padding:0;">
                    <span style="font-size:20px;line-height:40px;">📸</span>
                  </td>
                  <td style="padding-left:10px;">
                    <span style="font-size:20px;font-weight:800;color:#fff;
                                 letter-spacing:-0.3px;">InstaAgent</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 36px 28px;">
              <p style="margin:0 0 6px;font-size:12px;font-weight:700;
                        letter-spacing:0.08em;text-transform:uppercase;
                        color:#4F72F8;">Password Reset OTP</p>
              <h1 style="margin:0 0 14px;font-size:22px;font-weight:800;
                         color:#F1F5FC;letter-spacing:-0.3px;">
                Hi {to_name} 👋
              </h1>
              <p style="margin:0 0 28px;font-size:14px;color:#8A9BBF;line-height:1.6;">
                We received a request to reset your InstaAgent password.
                Use the code below to complete verification.
                This code is valid for <strong style="color:#F1F5FC;">10 minutes</strong>
                and can only be used once.
              </p>

              <!-- OTP Box -->
              <div style="background:#060A14;border:2px solid rgba(79,114,248,0.3);
                          border-radius:12px;padding:24px 20px;text-align:center;
                          margin:0 0 28px;">
                <p style="margin:0 0 6px;font-size:11px;font-weight:700;
                          letter-spacing:0.12em;text-transform:uppercase;
                          color:#4A5A72;">Your verification code</p>
                <p style="margin:0;font-size:44px;font-weight:900;color:#4F72F8;
                          letter-spacing:14px;font-family:'Courier New',monospace;">
                  {otp}
                </p>
              </div>

              <p style="margin:0 0 10px;font-size:13px;color:#4A5A72;line-height:1.55;">
                🔒 <strong style="color:#8A9BBF;">Never share this code</strong> with anyone,
                including InstaAgent support staff. We will never ask for your OTP.
              </p>
              <p style="margin:0;font-size:13px;color:#4A5A72;line-height:1.55;">
                If you did not request a password reset, please ignore this email.
                Your account remains secure and unchanged.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="border-top:1px solid rgba(255,255,255,0.06);
                       padding:18px 36px;text-align:center;">
              <p style="margin:0;font-size:11px;color:#4A5A72;">
                © {datetime.now().year} InstaAgent · Hyderabad, India ·
                <a href="#" style="color:#4F72F8;text-decoration:none;">Privacy Policy</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

            plain_body = (
                f"InstaAgent — Password Reset OTP\n\n"
                f"Hi {to_name},\n\n"
                f"Your 6-digit OTP is: {otp}\n\n"
                f"This code expires in 10 minutes.\n"
                f"Do not share it with anyone.\n\n"
                f"If you did not request this, ignore this email.\n\n"
                f"— InstaAgent Team"
            )

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"]      = to_email
            msg["X-Mailer"] = "InstaAgent"

            msg.attach(MIMEText(plain_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body,  "html",  "utf-8"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())

            log.info("OTP email delivered | to=%s", to_email)

        except Exception as exc:
            # Do NOT re-raise. A failed email should not expose user existence.
            log.error("OTP email failed | to=%s | error=%s", to_email, exc)

    thread = threading.Thread(target=_worker, daemon=True, name=f"otp-mail-{to_email[:8]}")
    thread.start()


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Create a new user account")
async def register(body: RegisterRequest):
    """
    Creates a new InstaAgent account.

    - Validates password strength via Pydantic validators.
    - Rejects duplicate emails with a clear 409 error.
    - Returns a JWT token immediately — no email verification step.
    """
    supabase = get_supabase()

    # Check for existing email (case-insensitive)
    existing = (
        supabase.table("users")
        .select("id")
        .eq("email", body.email.lower())
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user_id       = str(uuid.uuid4())
    password_hash = _hash(body.password)
    now           = datetime.now(timezone.utc).isoformat()

    new_user = {
        "id":            user_id,
        "email":         body.email.lower().strip(),
        "full_name":     body.full_name.strip(),
        "password_hash": password_hash,
        "phone":         body.phone or None,
        "city":          body.city  or None,
        "language":      body.language,
        "plan":          "free",
        "is_active":     True,
        "created_at":    now,
        "updated_at":    now,
    }

    result = supabase.table("users").insert(new_user).execute()
    if not result.data:
        log.error("User insert returned no data | email=%s", body.email)
        raise HTTPException(status_code=500, detail="Failed to create account. Please try again.")

    token = _issue_jwt(user_id)
    log.info("New user registered | id=%s email=%s", user_id, body.email.lower())

    return {
        "token":   token,
        "message": "Account created successfully.",
        "user": {
            "id":        user_id,
            "email":     body.email.lower(),
            "full_name": body.full_name.strip(),
            "plan":      "free",
            "language":  body.language,
        },
    }


@router.post("/login", summary="Authenticate and receive JWT token")
async def login(body: LoginRequest):
    """
    Verifies email + password and returns a signed JWT.

    Security:
    - Always runs bcrypt comparison (even for unknown emails) to prevent
      timing-based email enumeration attacks.
    - Deactivated accounts receive a 403 instead of 401.
    """
    supabase = get_supabase()

    result = (
        supabase.table("users")
        .select("id, email, full_name, password_hash, plan, language, is_active, telegram_id")
        .eq("email", body.email.lower().strip())
        .execute()
    )
    user = result.data[0] if result.data else None

    # Always run bcrypt to prevent timing attacks on unknown emails
    dummy_hash    = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/3dZQ7e2"
    stored_hash   = user["password_hash"] if user else dummy_hash
    password_ok   = _verify(body.password, stored_hash)

    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact support.",
        )

    token = _issue_jwt(user["id"])
    log.info("User authenticated | id=%s", user["id"])

    return {
        "token": token,
        "user": {
            "id":          user["id"],
            "email":       user["email"],
            "full_name":   user["full_name"],
            "plan":        user.get("plan", "free"),
            "language":    user.get("language", "hi"),
            "telegram_id": user.get("telegram_id"),
        },
    }


@router.get("/me", summary="Get authenticated user's profile")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Returns the authenticated user's profile. Sensitive fields are excluded."""
    return _safe_user_response(current_user)


@router.put("/me", summary="Update profile fields")
@router.patch("/me", summary="Partial update profile fields")
@router.patch("/profile", summary="Partial update profile fields (alias)")
@router.put("/profile", summary="Update profile fields (alias)")
async def update_profile(
    body: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    updates  = {k: v for k, v in body.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    supabase.table("users").update(updates).eq("id", current_user["id"]).execute()

    updated_user = (
        supabase.table("users")
        .select("id, email, full_name, phone, city, language, plan, "
                "instagram_username, is_active, created_at, telegram_id, "
                "trial_start, trial_end, trial_used, preferred_post_time, "
                "is_admin, whatsapp_phone")
        .eq("id", current_user["id"])
        .single()
        .execute()
    )
    user_data = _safe_user_response(updated_user.data) if updated_user.data else {}

    return {"message": "Profile updated successfully.", "user": user_data}


@router.post("/change-password", summary="Change password (requires current password)")
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()

    # Re-fetch to get the current hash (current_user dict may be cached)
    result = (
        supabase.table("users")
        .select("password_hash")
        .eq("id", current_user["id"])
        .single()
        .execute()
    )
    if not _verify(body.current_password, result.data["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from the current password.",
        )

    new_hash = _hash(body.new_password)
    supabase.table("users").update({
        "password_hash": new_hash,
        "updated_at":    datetime.now(timezone.utc).isoformat(),
    }).eq("id", current_user["id"]).execute()

    log.info("Password changed | user_id=%s", current_user["id"])
    return {"message": "Password changed successfully."}


@router.post("/forgot-password", summary="Send OTP to email for password reset")
async def forgot_password(body: ForgotPasswordRequest):
    """
    Sends a 6-digit OTP to the given email address.

    Anti-enumeration: Always returns HTTP 200 with the same message, regardless
    of whether the email exists in the database. This prevents attackers from
    using this endpoint to discover registered emails.

    OTP data stored in Redis:
        Key:   ia:otp:{email}
        Value: JSON { otp_hash, attempts, created_at }
        TTL:   OTP_TTL_SECONDS (10 minutes)
    """
    supabase = get_supabase()
    email    = body.email.lower().strip()

    # Look up user — silently skip if not found
    result = (
        supabase.table("users")
        .select("id, full_name, email")
        .eq("email", email)
        .execute()
    )

    if result.data:
        user      = result.data[0]
        otp       = _generate_otp()
        otp_data  = {
            "otp_hash":   _hash(otp),
            "attempts":   0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        redis = get_redis()
        redis_key = REDIS_KEY_OTP.format(email=email)

        # Delete any previous OTP for this email before creating a new one
        redis.delete(redis_key)
        redis.setex(redis_key, OTP_TTL_SECONDS, json.dumps(otp_data))

        # Fire-and-forget email (non-blocking)
        _send_otp_email(
            to_email=user["email"],
            to_name=user["full_name"],
            otp=otp,
        )

        log.info("OTP issued | email=%s", email)

    # Always return identical response — anti-enumeration
    return {
        "message": (
            "If an account is registered with this email, you will receive "
            "a 6-digit verification code within a few minutes. "
            "The code expires in 10 minutes."
        )
    }


@router.post("/verify-otp", summary="Verify OTP and receive a one-time reset token")
async def verify_otp(body: VerifyOtpRequest):
    """
    Validates the 6-digit OTP.

    On success: returns a one-time reset_token (valid for 15 minutes).
    On failure: increments attempt counter. After 5 failures the OTP is deleted
                and the user must request a new one.

    Reset token stored in Redis:
        Key:   ia:rst:{first_16_chars_of_token}
        Value: JSON { email, token_hash, created_at }
        TTL:   RESET_TOKEN_TTL_SECONDS (15 minutes)
    """
    email     = body.email.lower().strip()
    redis     = get_redis()
    redis_key = REDIS_KEY_OTP.format(email=email)

    raw = redis.get(redis_key)
    if not raw:
        raise HTTPException(
            status_code=400,
            detail="OTP has expired or was not found. Please request a new one.",
        )

    otp_data: dict = json.loads(raw)

    # Enforce attempt limit
    if otp_data["attempts"] >= MAX_OTP_ATTEMPTS:
        redis.delete(redis_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many incorrect attempts. Please request a new OTP.",
        )

    # Verify OTP
    if not _verify(body.otp, otp_data["otp_hash"]):
        otp_data["attempts"] += 1
        remaining = MAX_OTP_ATTEMPTS - otp_data["attempts"]

        # Persist updated attempt count (preserve remaining TTL)
        ttl = redis.ttl(redis_key)
        redis.setex(redis_key, max(ttl, 1), json.dumps(otp_data))

        if remaining <= 0:
            redis.delete(redis_key)
            raise HTTPException(
                status_code=400,
                detail="OTP is invalid. Maximum attempts reached. Please request a new OTP.",
            )

        raise HTTPException(
            status_code=400,
            detail=f"Incorrect OTP. {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
        )

    # OTP correct — delete it (single-use)
    redis.delete(redis_key)

    # Issue one-time reset token
    reset_token   = _generate_reset_token()
    token_prefix  = reset_token[:16]   # index key (non-secret portion)
    token_data    = {
        "email":       email,
        "token_hash":  _hash(reset_token),
        "created_at":  datetime.now(timezone.utc).isoformat(),
    }

    token_key = REDIS_KEY_TOKEN.format(token_prefix=token_prefix)
    redis.setex(token_key, RESET_TOKEN_TTL_SECONDS, json.dumps(token_data))

    log.info("OTP verified, reset token issued | email=%s", email)

    return {
        "reset_token":       reset_token,
        "expires_in_minutes": RESET_TOKEN_TTL_SECONDS // 60,
        "message": "OTP verified. Use reset_token to set your new password.",
    }


@router.post("/reset-password", summary="Set a new password using the reset token")
async def reset_password(body: ResetPasswordRequest):
    """
    Resets the user's password using the one-time reset token issued by /verify-otp.

    The token is deleted from Redis after successful use (single-use guarantee).
    """
    redis        = get_redis()
    reset_token  = body.reset_token.strip()
    token_prefix = reset_token[:16]
    token_key    = REDIS_KEY_TOKEN.format(token_prefix=token_prefix)

    raw = redis.get(token_key)
    if not raw:
        raise HTTPException(
            status_code=400,
            detail="Reset token has expired or is invalid. Please restart the process.",
        )

    token_data: dict = json.loads(raw)

    # Verify the full token against the stored hash
    if not _verify(reset_token, token_data["token_hash"]):
        raise HTTPException(
            status_code=400,
            detail="Reset token is invalid. Please restart the process.",
        )

    # Delete token immediately — single-use enforcement
    redis.delete(token_key)

    # Find user by email
    supabase = get_supabase()
    result = (
        supabase.table("users")
        .select("id")
        .eq("email", token_data["email"])
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="Account not found.",
        )

    user_id  = result.data[0]["id"]
    new_hash = _hash(body.new_password)

    supabase.table("users").update({
        "password_hash": new_hash,
        "updated_at":    datetime.now(timezone.utc).isoformat(),
    }).eq("id", user_id).execute()

    log.info("Password reset completed | user_id=%s", user_id)

    return {"message": "Password reset successfully. You can now sign in with your new password."}