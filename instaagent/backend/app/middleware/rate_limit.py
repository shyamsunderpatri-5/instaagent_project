# backend/app/middleware/rate_limit.py
# Rate Limiting — max 100 API requests per hour per user
# Uses Redis (Upstash) to track request counts
# Returns HTTP 429 Too Many Requests if limit exceeded

from fastapi import HTTPException, Depends, Request
from app.config import settings
from app.middleware.auth import get_current_user
import time

from app.db.redis_client import get_redis as _get_redis



async def rate_limit(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    FastAPI dependency — limits each user to 100 requests per hour.

    Usage in any route:
        @router.post("/create")
        async def create(
            current_user: dict = Depends(get_current_user),
            _: None = Depends(rate_limit),
        ):

    Redis key format: rate_limit:{user_id}:{current_hour}
    Each key auto-expires after 2 hours.
    """
    user_id = current_user["id"]

    # Key resets every hour automatically
    current_hour = int(time.time() // 3600)
    redis_key = f"rate_limit:{user_id}:{current_hour}"

    try:
        r = _get_redis()

        # Increment counter and set expiry
        count = r.incr(redis_key)
        if count == 1:
            r.expire(redis_key, 7200)   # Expire after 2 hours (safety margin)

        # Check limit
        limit = 100
        if count > limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {limit} requests per hour. Try again in {3600 - (int(time.time()) % 3600)} seconds.",
                    "requests_made": count,
                    "limit": limit,
                },
                headers={"Retry-After": str(3600 - (int(time.time()) % 3600))},
            )

    except HTTPException:
        raise

    except Exception:
        # If Redis is down, allow the request — don't break the app
        # Log this in production with Sentry
        pass
