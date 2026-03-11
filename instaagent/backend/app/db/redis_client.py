# backend/app/db/redis_client.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Centralized Redis Client
#
# Problem: Upstash Redis uses TLS (rediss://) but the ?ssl_cert_reqs=CERT_NONE
# query param in the URL is NOT parsed by redis-py's from_url(). This caused:
#   "Invalid SSL Certificate Requirements Flag: CERT_NONE"
# on every Redis connection — blocking Instagram OAuth, WA idempotency, etc.
#
# Fix: Parse the URL ourselves and pass ssl_cert_reqs=ssl.CERT_NONE directly.
#
# Usage (anywhere in the backend):
#   from app.db.redis_client import get_redis
#   r = get_redis()
#   r.setex("key", 60, "value")
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import ssl
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Optional

import redis

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """
    Return a singleton Redis client.
    Handles Upstash TLS quirks (ssl_cert_reqs=CERT_NONE) properly.
    Returns None if Redis is unavailable — callers should handle gracefully.
    """
    global _client
    if _client is not None:
        return _client

    url = settings.REDIS_URL
    if not url:
        logger.warning("REDIS_URL not configured — Redis features disabled")
        return None

    try:
        # Strip ?ssl_cert_reqs=... from the URL (redis-py ignores it and errors)
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        ssl_cert_reqs_str = query_params.pop("ssl_cert_reqs", ["CERT_REQUIRED"])[0].upper()

        # Rebuild URL without that param
        clean_query = urlencode({k: v[0] for k, v in query_params.items()})
        clean_url   = urlunparse(parsed._replace(query=clean_query))

        # Map string → ssl constant
        ssl_cert_reqs_map = {
            "CERT_NONE":     ssl.CERT_NONE,
            "CERT_OPTIONAL": ssl.CERT_OPTIONAL,
            "CERT_REQUIRED": ssl.CERT_REQUIRED,
        }
        ssl_cert_reqs = ssl_cert_reqs_map.get(ssl_cert_reqs_str, ssl.CERT_NONE)

        # Build client with explicit ssl_cert_reqs
        if clean_url.startswith("rediss://"):
            _client = redis.from_url(
                clean_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                ssl_cert_reqs=ssl_cert_reqs,
            )
        else:
            _client = redis.from_url(
                clean_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )

        # Verify connection
        _client.ping()
        logger.info("Redis connected ✅ | url=%s...", clean_url[:40])
        return _client

    except redis.exceptions.ConnectionError as e:
        logger.error("Redis connection failed: %s", e)
        _client = None
        return None
    except Exception as e:
        logger.error("Redis init error: %s", e)
        _client = None
        return None


def reset_redis() -> None:
    """Force reconnect (useful after settings change in dev)."""
    global _client
    _client = None
