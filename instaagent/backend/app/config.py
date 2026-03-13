# backend/app/config.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Central Configuration (Enterprise Edition)
# All environment variables loaded from .env via pydantic-settings.
# Import everywhere as:  from app.config import settings
#
# FEATURE FLAGS — control which capabilities are active without code changes.
# Override any flag in .env:  FEATURE_ENABLE_REELS=false
# ─────────────────────────────────────────────────────────────────────────────

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Dict, Any, Optional
import yaml
import os


class Settings(BaseSettings):

    # ── Anthropic Claude ──────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str

    # ── Photo Processing APIs ─────────────────────────────────────────────────
    REMOVEBG_API_KEY: str
    PHOTOROOM_API_KEY: str

    # ── Supabase (PostgreSQL + Storage) ───────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str

    # ── Telegram Bot ──────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_BOT_USERNAME: str = "InstaAgent_bot"   # shown in Settings tab
    ADMIN_TELEGRAM_ID: str = ""                      # for /broadcast, /userstats

    # ── Instagram / Meta App ─────────────────────────────────────────────────
    INSTAGRAM_APP_ID: str = ""
    INSTAGRAM_APP_SECRET: str = ""
    INSTAGRAM_REDIRECT_URI: str = ""
    INSTAGRAM_VERIFY_TOKEN: str = ""
    INSTAGRAM_TOKEN_REFRESH_DAYS: int = 7            # refresh tokens with N days left
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    # ── Simulation & Testing ─────────────────────────────────────────────────
    INSTAGRAM_SIMULATE: bool = False                 # if true, log posts instead of hitting Meta API
    AI_SIMULATION: bool = False                      # if true, skip Claude/Photoroom and use mocks

    # ── WhatsApp Business Cloud API (Meta) ────────────────────────────────────
    WHATSAPP_TOKEN: str = ""                    # Permanent system user token from Meta
    WHATSAPP_PHONE_ID: str = ""                  # Business phone number ID from Meta
    WHATSAPP_APP_SECRET: str = ""               # App secret for HMAC-SHA256 webhook verification
    WHATSAPP_VERIFY_TOKEN: str = ""             # Custom token for webhook setup
    WHATSAPP_RATE_LIMIT_PHOTOS: int = 5         # Max photos per phone per hour

    # ── Razorpay Payments ─────────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # ── Redis (Upstash — use rediss:// with double-s for TLS) ─────────────────
    REDIS_URL: str

    # ── Gmail API — Email Delivery ─────────────────────────────────────────────
    EMAIL_SENDER: str = ""
    EMAIL_FROM_NAME: str = "InstaAgent"
    EMAIL_RECIPIENT: str = ""
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REFRESH_TOKEN: str = ""
    GCP_SA_KEY: str = ""

    # ── JWT & Security ────────────────────────────────────────────────────────
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 72
    # REQUIRED: Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str

    # ── Application ───────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"
    FREE_TRIAL_POSTS: int = 5            # posts allowed on free plan per month

    # ── Admin ─────────────────────────────────────────────────────────────────
    ADMIN_SECRET: str = ""               # Secret key to promote users to admin
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""

    # ── Subscription Plan Pricing (INR) ──────────────────────────────────────
    # Override any of these in .env to change pricing without code changes
    PLAN_FREE_POSTS:    int = 5          # free posts/month
    PLAN_STARTER_PRICE: int = 299        # ₹/month
    PLAN_STARTER_POSTS: int = 30
    PLAN_GROWTH_PRICE:  int = 599
    PLAN_GROWTH_POSTS:  int = 90
    PLAN_AGENCY_PRICE:  int = 1999
    PLAN_AGENCY_POSTS:  int = 300
    PLAN_AGGREGATOR_PRICE: int = 999     # ₹/month (Aggregator bundle)

    # ── FEATURE FLAGS ─────────────────────────────────────────────────────────
    # Each flag maps to FEATURE_<KEY>=true|false in .env
    # Default: enterprise-ready features ON, Reels OFF (needs Meta review)
    FEATURE_ENABLE_AI_CAPTION:        bool = True
    FEATURE_ENABLE_BG_REMOVAL:        bool = True
    FEATURE_ENABLE_PHOTO_ENHANCE:     bool = True
    FEATURE_ENABLE_AUTO_POST:         bool = True
    FEATURE_ENABLE_TELEGRAM_BOT:      bool = True
    FEATURE_ENABLE_SCHEDULED_POSTING: bool = True
    FEATURE_ENABLE_CAROUSELS:         bool = True
    FEATURE_ENABLE_REELS:             bool = False   # Requires Meta advanced permissions
    FEATURE_ENABLE_WHATSAPP_BOT:      bool = True    # WhatsApp → Instagram pipeline
    FEATURE_ENABLE_ANALYTICS:         bool = True
    FEATURE_ENABLE_BILLING:           bool = True
    FEATURE_ENABLE_STORIES:           bool = True
    FEATURE_ENABLE_AI_COMMENT_REPLY:  bool = True
    FEATURE_ENABLE_IG_DM_FORWARD:     bool = True
    FEATURE_ENABLE_TOKEN_REFRESH:     bool = True
    FEATURE_ENABLE_WEEKLY_REPORTS:    bool = True
    FEATURE_ENABLE_MONTHLY_REPORTS:   bool = True
    FEATURE_ENABLE_AGGREGATOR:       bool = True    # New: Competition Aggregator

    # ── WhatsApp (MVP Stub) ───────────────────────────────────────────────────
    WHATSAPP_FORWARD_ENABLED:         bool = True

    @property
    def features(self) -> Dict[str, bool]:
        """Return a flat dict of all feature flags (used by /api/v1/features endpoint)."""
        return {
            "enable_ai_caption":        self.FEATURE_ENABLE_AI_CAPTION,
            "enable_bg_removal":        self.FEATURE_ENABLE_BG_REMOVAL,
            "enable_photo_enhance":     self.FEATURE_ENABLE_PHOTO_ENHANCE,
            "enable_auto_post":         self.FEATURE_ENABLE_AUTO_POST,
            "enable_telegram_bot":      self.FEATURE_ENABLE_TELEGRAM_BOT,
            "enable_scheduled_posting": self.FEATURE_ENABLE_SCHEDULED_POSTING,
            "enable_carousels":         self.FEATURE_ENABLE_CAROUSELS,
            "enable_reels":             self.FEATURE_ENABLE_REELS,
            "enable_stories":           self.FEATURE_ENABLE_STORIES,
            "enable_ai_comment_reply":  self.FEATURE_ENABLE_AI_COMMENT_REPLY,
            "enable_ig_dm_forward":     self.FEATURE_ENABLE_IG_DM_FORWARD,
            "enable_analytics":         self.FEATURE_ENABLE_ANALYTICS,
            "enable_token_refresh":     self.FEATURE_ENABLE_TOKEN_REFRESH,
            "enable_billing":           self.FEATURE_ENABLE_BILLING,
            "enable_weekly_reports":    self.FEATURE_ENABLE_WEEKLY_REPORTS,
            "enable_monthly_reports":   self.FEATURE_ENABLE_MONTHLY_REPORTS,
            "enable_aggregator":        self.FEATURE_ENABLE_AGGREGATOR,
        }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Cached singleton — .env is read, then config.yaml is merged.
    config.yaml overrides .env for enterprise-level 'hot' tweaks.
    """
    s = Settings()
    
    yaml_file = "config.yaml"
    if os.path.exists(yaml_file):
        try:
            with open(yaml_file, "r") as f:
                y_data = yaml.safe_load(f)
                if y_data:
                    # Merge YAML keys into settings
                    for k, v in y_data.items():
                        if hasattr(s, k):
                            setattr(s, k, v)
                    print(f"📦 Merged {len(y_data)} keys from {yaml_file}")
        except Exception as e:
            print(f"⚠️ Failed to load {yaml_file}: {e}")
            
    return s

class _SettingsWrapper:
    """Singleton wrapper for settings to allow safe hot-reloading."""
    _instance = None
    _settings = None

    def __getattr__(self, name):
        if not self._settings:
            self._settings = get_settings()
        return getattr(self._settings, name)

    def refresh(self):
        """Clears cache and reloads settings thread-safely."""
        print("🔄 SettingsWrapper: Refreshing configuration...")
        get_settings.cache_clear()
        self._settings = get_settings()

settings = _SettingsWrapper()


# ── CONFIG HOT-RELOAD (Enterprise Sync) ──────────────────────────────────
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigReloader(FileSystemEventHandler):
    """Watches .env and config.yaml for changes and clears cache."""
    def on_modified(self, event):
        filename = os.path.basename(event.src_path)
        if filename in (".env", "config.yaml"):
            print(f"🔄 Config change detected ({filename}). Reloading settings...")
            settings.refresh()

def start_config_watcher():
    """Starts a background thread to watch for config changes."""
    observer = Observer()
    handler = ConfigReloader()
    
    # We watch the current directory for these files
    path = os.path.abspath(".")
    observer.schedule(handler, path, recursive=False)
    observer.daemon = True
    observer.start()
    print(f"🔭 Watching {path} for (.env, config.yaml) changes...")