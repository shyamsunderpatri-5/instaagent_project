# backend/main.py
# InstaAgent — FastAPI Entry Point
# Run: uvicorn main:app --reload --port 8000

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings, start_config_watcher
from app.api import auth, posts, instagram, subscription, usage, webhooks, analytics, features, admin

app = FastAPI(
    title="InstaAgent API",
    description="AI-powered Instagram automation for Indian small businesses",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.on_event("startup")
def startup_event():
    start_config_watcher()

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── ROUTERS ──────────────────────────────────────────────────────────────────
app.include_router(features.router,     prefix="/api/v1/features",     tags=["Features"])
app.include_router(auth.router,         prefix="/api/v1/auth",         tags=["Auth"])
app.include_router(posts.router,        prefix="/api/v1/posts",        tags=["Posts"])
app.include_router(instagram.router,    prefix="/api/v1/instagram",    tags=["Instagram"])
app.include_router(subscription.router, prefix="/api/v1/subscription", tags=["Billing"])
app.include_router(usage.router,        prefix="/api/v1/usage",        tags=["Usage"])
app.include_router(analytics.router,    prefix="/api/v1/analytics",    tags=["Analytics"])
app.include_router(webhooks.router,     prefix="/api/v1/webhooks",     tags=["Webhooks"])
app.include_router(admin.router,        prefix="/api/v1/admin",        tags=["Admin"])

# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "InstaAgent API", "version": "1.0.0"}


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "InstaAgent API is running 🚀",
        "docs": "/docs",
        "health": "/health",
    }
