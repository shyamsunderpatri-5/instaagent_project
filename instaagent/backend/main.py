# backend/main.py
# ═══════════════════════════════════════════════════════════════════════════════
# InstaAgent — FastAPI Application Entry Point (Enterprise Edition)
# Features: structured JSON logging, Sentry APM, startup health validation,
#           request ID middleware, detailed /health endpoint
# Run: uvicorn main:app --reload --port 8000
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

# ── Sentry (APM + Error Tracking) ────────────────────────────────────────────
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# ── Application modules ───────────────────────────────────────────────────────
from app.config import settings, start_config_watcher
from app.api import auth, posts, instagram, subscription, usage, webhooks, analytics, features, admin, aggregator


# ═══════════════════════════════════════════════════════════════════════════════
# Structured Logging Setup
# ═══════════════════════════════════════════════════════════════════════════════

def _configure_logging() -> None:
    """Configure structlog for JSON output in production, pretty-print in dev."""
    is_prod = os.getenv("ENVIRONMENT", "development") == "production"

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if is_prod:
        processors = shared_processors + [structlog.processors.JSONRenderer()]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging to go through structlog
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )


_configure_logging()
log = structlog.get_logger("main")


# ═══════════════════════════════════════════════════════════════════════════════
# Sentry Initialization
# ═══════════════════════════════════════════════════════════════════════════════

_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,          # 10% of requests traced (adjust for cost)
        profiles_sample_rate=0.05,
        environment=os.getenv("ENVIRONMENT", "development"),
        release=f"instaagent@{os.getenv('APP_VERSION', '2.0.0')}",
        send_default_pii=False,          # GDPR compliance — no PII in Sentry
    )
    log.info("sentry_initialized", dsn_set=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Application Lifespan (startup + shutdown hooks)
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────────────────────────
    log.info("instaagent_starting", version="2.0.0", environment=os.getenv("ENVIRONMENT", "development"))

    # Start config hot-reload watcher (watches .env and config.yaml)
    try:
        start_config_watcher()
        log.info("config_watcher_started")
    except Exception as e:
        log.warning("config_watcher_failed", error=str(e))

    # Validate critical config on startup
    _validate_startup_config()

    log.info("instaagent_ready", docs="/docs", health="/health")

    yield  # Application is running

    # ── Shutdown ─────────────────────────────────────────────────────────────
    log.info("instaagent_shutting_down")


def _validate_startup_config() -> None:
    """Warn loudly if critical env vars are missing (don't crash, just warn)."""
    required = [
        ("ANTHROPIC_API_KEY",  settings.ANTHROPIC_API_KEY),
        ("SUPABASE_URL",       settings.SUPABASE_URL),
        ("SUPABASE_SERVICE_KEY", settings.SUPABASE_SERVICE_KEY),
        ("JWT_SECRET",         settings.JWT_SECRET),
        ("REDIS_URL",          settings.REDIS_URL),
    ]
    missing = [name for name, val in required if not val or val.startswith("your_")]
    if missing:
        log.warning("startup_config_incomplete", missing_vars=missing,
                    hint="Set these in backend/.env before going to production")
    else:
        log.info("startup_config_ok")


# ═══════════════════════════════════════════════════════════════════════════════
# FastAPI Application
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="InstaAgent API",
    description=(
        "AI-powered Instagram automation platform for Indian small businesses. "
        "Handles product photo enhancement, AI caption generation, and Instagram posting."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
    },
)


# ═══════════════════════════════════════════════════════════════════════════════
# Middleware Stack (order matters — outermost first)
# ═══════════════════════════════════════════════════════════════════════════════

# 1. Request ID — inject a unique ID for distributed tracing
@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# 2. Access logging with timing
@app.middleware("http")
async def access_log_middleware(request: Request, call_next) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    # Don't log health checks (would spam logs)
    if request.url.path not in ("/health", "/"):
        log.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            ip=request.client.host if request.client else "unknown",
        )
    return response


# 3. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining", "Retry-After"],
)


# 4. GZip (compress responses > 1KB)
app.add_middleware(GZipMiddleware, minimum_size=1024)


# ═══════════════════════════════════════════════════════════════════════════════
# Routers
# ═══════════════════════════════════════════════════════════════════════════════

app.include_router(features.router,     prefix="/api/v1/features",     tags=["Features"])
app.include_router(auth.router,         prefix="/api/v1/auth",         tags=["Auth"])
app.include_router(posts.router,        prefix="/api/v1/posts",        tags=["Posts"])
app.include_router(instagram.router,    prefix="/api/v1/instagram",    tags=["Instagram"])
app.include_router(subscription.router, prefix="/api/v1/subscription", tags=["Billing"])
app.include_router(usage.router,        prefix="/api/v1/usage",        tags=["Usage"])
app.include_router(analytics.router,    prefix="/api/v1/analytics",    tags=["Analytics"])
app.include_router(webhooks.router,     prefix="/api/v1/webhooks",     tags=["Webhooks"])
app.include_router(admin.router,        prefix="/api/v1/admin",        tags=["Admin"])
if settings.FEATURE_ENABLE_AGGREGATOR:
    app.include_router(aggregator.router, prefix="/api/v1/aggregator", tags=["Aggregator"])


# ═══════════════════════════════════════════════════════════════════════════════
# System Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["System"], include_in_schema=False)
async def root():
    return {
        "service": "InstaAgent API",
        "version": "2.0.0",
        "docs":    "/docs",
        "health":  "/health",
        "status":  "running",
    }


@app.get("/health", tags=["System"])
async def health_check():
    """
    Deep health check — verifies connectivity to all critical services.
    Returns 200 if all checks pass, 503 if any critical service is down.
    Used by Docker HEALTHCHECK, load balancers, and monitoring.
    """
    import asyncio
    checks: dict[str, dict] = {}
    overall_ok = True

    # ── Check Redis ──────────────────────────────────────────────────────────
    try:
        from app.db.redis_client import get_redis
        r = get_redis()
        if r:
            r.ping()
            checks["redis"] = {"status": "ok"}
        else:
            checks["redis"] = {"status": "unavailable"}
            overall_ok = False
    except Exception as e:
        checks["redis"] = {"status": "error", "detail": str(e)[:100]}
        overall_ok = False

    # ── Check Supabase ───────────────────────────────────────────────────────
    try:
        from app.db.supabase import get_supabase
        sb = get_supabase()
        # Lightweight query — just check connection
        sb.table("users").select("id").limit(1).execute()
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)[:100]}
        overall_ok = False

    # ── Check config ─────────────────────────────────────────────────────────
    checks["config"] = {
        "status":      "ok",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "version":     "2.0.0",
        "simulation":  {
            "instagram": settings.INSTAGRAM_SIMULATE,
            "ai":        settings.AI_SIMULATION,
        },
    }

    status_code = 200 if overall_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status":  "healthy" if overall_ok else "degraded",
            "checks":  checks,
            "timestamp": time.time(),
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Global Exception Handler
# ═══════════════════════════════════════════════════════════════════════════════

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler — logs unexpected errors and returns a safe response."""
    log.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    # Sentry automatically captures this via the SDK integration
    return JSONResponse(
        status_code=500,
        content={
            "detail":  "An unexpected error occurred. Our team has been notified.",
            "request_id": structlog.contextvars.get_contextvars().get("request_id", "unknown"),
        },
    )