# backend/app/middleware/auth.py
# JWT token verification — used as FastAPI Depends() in every protected route

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.config import settings
from app.db.supabase import get_supabase
from app.utils.crypto import decrypt_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Verify JWT token from Authorization: Bearer <token> header.
    Returns full user dict from database.
    Raises 401 if token is missing, expired, or invalid.

    Usage in any route:
        @router.get("/protected")
        async def protected_route(current_user: dict = Depends(get_current_user)):
            return {"user": current_user}
    """
    token = credentials.credentials

    # ── Step 1: Decode and verify JWT signature ────────────────────────────────
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token — no user ID in payload")

    except JWTError as e:
        raise HTTPException(401, f"Token invalid or expired: {str(e)}")

    # ── Step 2: Fetch user from database ──────────────────────────────────────
    supabase = get_supabase()
    result = (
        supabase.table("users")
        .select("id, email, full_name, phone, city, language, plan, is_active, is_admin, instagram_token, instagram_username, instagram_id, instagram_token_expires_at, telegram_id, whatsapp_phone, preferred_post_time, trial_start, trial_end, trial_used, onboarding_done, created_at")
        .eq("id", user_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(401, "User not found — token may be for a deleted account")

    user = result.data

    # ── Step 3: Check account is active ───────────────────────────────────────
    if not user.get("is_active", True):
        raise HTTPException(403, "Account is deactivated. Please contact support.")

    # ── Step 4: Decrypt sensitive tokens ─────────────────────────────────────
    if user.get("instagram_token"):
        user["instagram_token"] = decrypt_token(user["instagram_token"])

    return user
