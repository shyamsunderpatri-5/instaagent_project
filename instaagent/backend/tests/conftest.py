# backend/tests/conftest.py
"""
Shared pytest fixtures for InstaAgent backend tests.
All external dependencies (Supabase, Anthropic, Redis, HTTP) are mocked.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta


# ── Event loop for async tests ─────────────────────────────────────────────────
@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for all async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Settings override ──────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """
    Override settings so tests never hit real APIs.
    Sets AI_SIMULATION=True which triggers fallback paths in all services.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake-key")
    monkeypatch.setenv("REMOVEBG_API_KEY",  "test-removebg-key")
    monkeypatch.setenv("PHOTOROOM_API_KEY", "sandbox-test-key")
    monkeypatch.setenv("REDIS_URL",         "redis://localhost:6379")
    monkeypatch.setenv("AI_SIMULATION",     "true")

    # Patch the settings object directly in every module that imports it
    from app import config as cfg_module
    cfg_module.settings.AI_SIMULATION     = True
    cfg_module.settings.ANTHROPIC_API_KEY = "sk-test-fake-key"
    cfg_module.settings.REMOVEBG_API_KEY  = "test-removebg-key"
    cfg_module.settings.PHOTOROOM_API_KEY  = "sandbox-test-key"
    yield


# ── Supabase mock ──────────────────────────────────────────────────────────────
@pytest.fixture
def mock_supabase():
    """A Supabase client mock with chainable query methods."""
    client = MagicMock()
    # Make all chained calls return another MagicMock so we can chain .eq().execute() etc.
    client.table.return_value = client
    client.select.return_value = client
    client.eq.return_value     = client
    client.lte.return_value    = client
    client.not_.return_value   = client
    client.is_.return_value    = client
    client.limit.return_value  = client
    client.order.return_value  = client
    client.range.return_value  = client
    client.single.return_value = client
    client.insert.return_value = client
    client.update.return_value = client
    client.delete.return_value = client
    # Default empty result — override in individual tests
    client.execute.return_value = MagicMock(data=[])
    return client


# ── Sample post fixtures ───────────────────────────────────────────────────────
@pytest.fixture
def sample_ready_post():
    return {
        "id": "post-abc-123",
        "user_id": "user-xyz-456",
        "product_name": "Gold Bangles",
        "product_type": "jewellery",
        "status": "ready",
        "original_photo_url": "https://storage.example.com/post-original.jpg",
        "edited_photo_url":   "https://storage.example.com/post-edited.jpg",
        "caption_hindi": "✨ सोने की खूबसूरत चूड़ियाँ। DM करें।",
        "caption_english": "✨ Beautiful gold bangles. DM to order!",
        "hashtags": ["#jewellery", "#gold", "#india", "#smallbusiness", "#bangles"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scheduled_at": None,
        "posted_at": None,
        "users": {
            "instagram_token": "igtoken123",
            "instagram_id":    "ig_user_001",
            "telegram_id":     987654321,
            "language":        "hi",
            "preferred_post_time": "15:33",
        }
    }


@pytest.fixture
def sample_scheduled_post(sample_ready_post):
    """A post scheduled for 2 minutes from now (UTC)."""
    future = datetime.now(timezone.utc) + timedelta(minutes=2)
    return {
        **sample_ready_post,
        "status": "scheduled",
        "scheduled_at": future.isoformat(),
    }


@pytest.fixture
def sample_past_scheduled_post(sample_ready_post):
    """A post whose scheduled_at is 5 minutes in the past (UTC) — should fire."""
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    return {
        **sample_ready_post,
        "status": "scheduled",
        "scheduled_at": past.isoformat(),
    }


# ── Sample user fixture ────────────────────────────────────────────────────────
@pytest.fixture
def sample_user():
    return {
        "id":                   "user-xyz-456",
        "full_name":            "Test Seller",
        "email":                "seller@example.com",
        "language":             "hi",
        "preferred_post_time":  "15:33",   # IST
        "instagram_token":      "igtoken123",
        "instagram_id":         "ig_user_001",
        "instagram_username":   "testshop",
        "whatsapp_phone":       "919876543210",
        "plan":                 "professional",
    }
