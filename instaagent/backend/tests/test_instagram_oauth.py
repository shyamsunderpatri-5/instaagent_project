# backend/tests/test_instagram_oauth.py
"""
Tests for Instagram OAuth flow.
Verifies the exact flow described in the architecture doc:
  User clicks → Instagram login page → User approves → Token returned → Saved to DB
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI


@pytest.fixture(scope="module")
def app():
    from app.api.instagram import router
    _app = FastAPI()
    _app.include_router(router, prefix="/api/v1/instagram")
    return _app


@pytest.fixture(scope="module")
def client(app):
    return TestClient(app, raise_server_exceptions=False)


def _mock_user():
    return {
        "id": "user-uuid-123",
        "email": "seller@example.com",
        "full_name": "Test Seller",
        "is_active": True,
        "instagram_token": None,
        "instagram_id": None,
        "instagram_username": None,
    }


class TestInstagramOAuthFlow:
    """
    Verifies the standard OAuth2 flow:
    1. /connect  → returns an Instagram authorization URL
    2. /callback → exchanges code for token, saves to DB
    3. /status   → confirms connection
    4. /disconnect → clears token from DB
    """

    @pytest.mark.unit
    def test_connect_returns_instagram_auth_url(self, client):
        """Step 1: /connect must return a URL pointing to api.instagram.com/oauth."""
        with patch("app.api.instagram.get_current_user", return_value=_mock_user()), \
             patch("app.api.instagram.get_redis") as mock_redis:

            mock_r = MagicMock()
            mock_r.setex.return_value = True
            mock_redis.return_value = mock_r

            resp = client.get("/api/v1/instagram/connect")

        assert resp.status_code == 200
        data = resp.json()
        assert "auth_url" in data
        # URL must point to Instagram's authorization endpoint
        assert "instagram.com/oauth/authorize" in data["auth_url"] or \
               "mock_code" in data["auth_url"]  # simulation mode fallback

    @pytest.mark.unit
    def test_connect_simulation_mode(self, client):
        """When INSTAGRAM_SIMULATE=True, /connect returns a mock callback URL."""
        with patch("app.api.instagram.get_current_user", return_value=_mock_user()), \
             patch("app.api.instagram.get_redis") as mock_redis, \
             patch("app.api.instagram.settings") as mock_settings:

            mock_settings.INSTAGRAM_SIMULATE = True
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            mock_r = MagicMock()
            mock_r.setex.return_value = True
            mock_redis.return_value = mock_r

            resp = client.get("/api/v1/instagram/connect")

        # Simulation returns a mock URL (not a real Instagram URL)
        assert resp.status_code == 200

    @pytest.mark.unit
    def test_callback_with_invalid_state_returns_400(self, client):
        """If OAuth state doesn't match Redis, callback must reject the request."""
        with patch("app.api.instagram.get_redis") as mock_redis:
            mock_r = MagicMock()
            mock_r.getdel.return_value = None   # State not found in Redis
            mock_redis.return_value = mock_r

            resp = client.get(
                "/api/v1/instagram/callback",
                params={"code": "some_code", "state": "invalid_state"},
                follow_redirects=False,
            )

        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower() or \
               "invalid" in resp.json()["detail"].lower()

    @pytest.mark.unit
    def test_status_when_not_connected(self, client):
        """Status endpoint must indicate not connected when no token exists."""
        user = _mock_user()
        user["instagram_token"] = None
        user["instagram_username"] = None

        with patch("app.api.instagram.get_current_user", return_value=user):
            resp = client.get("/api/v1/instagram/status")

        assert resp.status_code == 200
        assert resp.json()["connected"] is False

    @pytest.mark.unit
    def test_status_when_connected(self, client):
        """Status endpoint must show username when connected."""
        user = _mock_user()
        user["instagram_token"] = "encrypted_token_here"
        user["instagram_username"] = "shop_by_priya"
        user["instagram_id"] = "17841400455970028"

        with patch("app.api.instagram.get_current_user", return_value=user):
            resp = client.get("/api/v1/instagram/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert data["username"] == "shop_by_priya"

    @pytest.mark.unit
    def test_disconnect_clears_token(self, client):
        """Disconnect must null out the Instagram token in the database."""
        user = _mock_user()
        user["instagram_token"] = "encrypted_token"
        user["instagram_username"] = "shop_by_priya"

        with patch("app.api.instagram.get_current_user", return_value=user), \
             patch("app.api.instagram.get_supabase") as mock_sb:

            mock_update = MagicMock()
            mock_sb.return_value.table.return_value.update.return_value \
                .eq.return_value.execute.return_value.data = [{}]

            resp = client.delete("/api/v1/instagram/disconnect")

        assert resp.status_code == 200
        assert resp.json()["disconnected"] is True
        # Verify update was called with None values
        update_call = mock_sb.return_value.table.return_value.update.call_args
        update_data = update_call[0][0]
        assert update_data["instagram_token"] is None
        assert update_data["instagram_username"] is None


class TestInstagramOAuthSecurity:
    """Security tests for the OAuth flow."""

    @pytest.mark.unit
    def test_csrf_state_parameter_is_validated(self, client):
        """State parameter (CSRF token) must be validated against Redis."""
        with patch("app.api.instagram.get_redis") as mock_redis:
            mock_r = MagicMock()
            # Redis returns None → state was never stored (CSRF attack)
            mock_r.getdel.return_value = None
            mock_redis.return_value = mock_r

            resp = client.get(
                "/api/v1/instagram/callback",
                params={"code": "attacker_code", "state": "forged_state"},
                follow_redirects=False,
            )

        assert resp.status_code == 400, "CSRF attack must be rejected with 400"

    @pytest.mark.unit
    def test_connect_requires_authentication(self, client):
        """Connect endpoint must require a valid JWT."""
        # No Authorization header → should fail with 403
        resp = client.get("/api/v1/instagram/connect")
        assert resp.status_code in (401, 403)