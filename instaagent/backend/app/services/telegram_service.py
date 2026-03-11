# backend/app/services/telegram_service.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Enterprise Telegram Bot Service
# Low-level API calls: send messages, photos, documents, keyboards, media groups
# Used by: webhooks.py, telegram_bot.py, workers
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
FILE_API     = f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}"


# ═══════════════════════════════════════════════════════════════════════════════
# Core Message Sending
# ═══════════════════════════════════════════════════════════════════════════════

async def send_message(
    telegram_id: int,
    text: str,
    parse_mode: str = "Markdown",
    disable_web_page_preview: bool = True,
    reply_to_message_id: int | None = None,
) -> dict:
    """Send a plain text message."""
    payload: dict[str, Any] = {
        "chat_id":                  telegram_id,
        "text":                     text[:4096],   # Telegram limit
        "parse_mode":               parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
        resp.raise_for_status()
        return resp.json()


async def edit_message(
    telegram_id: int,
    message_id: int,
    text: str,
    parse_mode: str = "Markdown",
) -> dict:
    """Edit an existing message in place (e.g. live processing status updates)."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/editMessageText",
            json={
                "chat_id":    telegram_id,
                "message_id": message_id,
                "text":       text[:4096],
                "parse_mode": parse_mode,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def delete_message(telegram_id: int, message_id: int) -> dict:
    """Delete a message (clean up temporary status messages)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/deleteMessage",
            json={"chat_id": telegram_id, "message_id": message_id},
        )
        resp.raise_for_status()
        return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# Media Sending
# ═══════════════════════════════════════════════════════════════════════════════

async def send_photo(
    telegram_id: int,
    photo_bytes: bytes,
    caption: str = "",
    parse_mode: str = "Markdown",
) -> dict:
    """Send a photo + optional caption."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/sendPhoto",
            data={
                "chat_id":    str(telegram_id),
                "caption":    caption[:1024],
                "parse_mode": parse_mode,
            },
            files={"photo": ("photo.jpg", photo_bytes, "image/jpeg")},
        )
        resp.raise_for_status()
        return resp.json()


async def send_photo_url(
    telegram_id: int,
    photo_url: str,
    caption: str = "",
    parse_mode: str = "Markdown",
) -> dict:
    """Send a photo by URL (avoids re-downloading bytes)."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/sendPhoto",
            json={
                "chat_id":    telegram_id,
                "photo":      photo_url,
                "caption":    caption[:1024],
                "parse_mode": parse_mode,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def send_media_group(
    telegram_id: int,
    photo_urls: list[str],
    caption: str = "",
) -> dict:
    """
    Send a media album (carousel preview) — up to 10 photos.
    Caption only appears on the first photo.
    """
    media = [
        {
            "type":    "photo",
            "media":   url,
            "caption": caption if i == 0 else "",
            "parse_mode": "Markdown",
        }
        for i, url in enumerate(photo_urls[:10])
    ]
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/sendMediaGroup",
            json={"chat_id": telegram_id, "media": media},
        )
        resp.raise_for_status()
        return resp.json()


async def send_document(
    telegram_id: int,
    document_bytes: bytes,
    filename: str,
    caption: str = "",
) -> dict:
    """Send a file/document (e.g. PDF or CSV analytics report)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/sendDocument",
            data={"chat_id": str(telegram_id), "caption": caption[:1024]},
            files={"document": (filename, document_bytes, "application/octet-stream")},
        )
        resp.raise_for_status()
        return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# Interactive Keyboards
# ═══════════════════════════════════════════════════════════════════════════════

async def send_inline_keyboard(
    telegram_id: int,
    text: str,
    buttons: list[list[dict]],
    parse_mode: str = "Markdown",
) -> dict:
    """
    Send a message with inline buttons.

    buttons format (list of rows, each row a list of button dicts):
        [
            [{"text": "✅ Post Now",    "callback_data": "post_now:POST_ID"}],
            [{"text": "⏰ Schedule",    "callback_data": "schedule:POST_ID"}],
            [{"text": "✏️ Edit Caption", "callback_data": "edit_caption:POST_ID"}],
        ]
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id":      telegram_id,
                "text":         text[:4096],
                "parse_mode":   parse_mode,
                "reply_markup": {"inline_keyboard": buttons},
            },
        )
        resp.raise_for_status()
        return resp.json()


async def send_reply_keyboard(
    telegram_id: int,
    text: str,
    keyboard: list[list[str]],
    one_time_keyboard: bool = True,
    resize_keyboard: bool = True,
) -> dict:
    """
    Send a persistent reply keyboard (custom buttons under the text input).
    keyboard format: [["Option A", "Option B"], ["Option C"]]
    """
    reply_markup = {
        "keyboard":          [[{"text": btn} for btn in row] for row in keyboard],
        "one_time_keyboard": one_time_keyboard,
        "resize_keyboard":   resize_keyboard,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id":      telegram_id,
                "text":         text,
                "reply_markup": reply_markup,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def remove_keyboard(telegram_id: int, text: str) -> dict:
    """Remove the custom reply keyboard."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id":      telegram_id,
                "text":         text,
                "reply_markup": {"remove_keyboard": True},
            },
        )
        resp.raise_for_status()
        return resp.json()


async def answer_callback_query(
    callback_query_id: str,
    text: str = "",
    show_alert: bool = False,
) -> dict:
    """Acknowledge a button press — removes the Telegram loading spinner."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/answerCallbackQuery",
            json={
                "callback_query_id": callback_query_id,
                "text":              text,
                "show_alert":        show_alert,
            },
        )
        resp.raise_for_status()
        return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# File Download
# ═══════════════════════════════════════════════════════════════════════════════

async def download_file(file_id: str) -> bytes:
    """
    Download any file sent to the bot (photo, document, video).
    Returns raw bytes.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get file path
        meta = await client.get(
            f"{TELEGRAM_API}/getFile",
            params={"file_id": file_id},
        )
        meta.raise_for_status()
        file_path = meta.json()["result"]["file_path"]

        # Download the file
        file_resp = await client.get(f"{FILE_API}/{file_path}")
        file_resp.raise_for_status()
        return file_resp.content


# ═══════════════════════════════════════════════════════════════════════════════
# Webhook Management
# ═══════════════════════════════════════════════════════════════════════════════

async def set_webhook(webhook_url: str) -> dict:
    """
    Register backend URL as the Telegram webhook.
    Call once during deployment.
    webhook_url: e.g. https://yourapp.render.com/api/v1/webhooks/telegram
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/setWebhook",
            json={
                "url":             webhook_url,
                "secret_token":    settings.TELEGRAM_WEBHOOK_SECRET,
                "allowed_updates": ["message", "callback_query"],
            },
        )
        resp.raise_for_status()
        return resp.json()


async def delete_webhook() -> dict:
    """Remove the Telegram webhook (useful for local testing)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{TELEGRAM_API}/deleteWebhook")
        resp.raise_for_status()
        return resp.json()


async def get_webhook_info() -> dict:
    """Get current webhook configuration and status."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{TELEGRAM_API}/getWebhookInfo")
        resp.raise_for_status()
        return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# Bot Commands Setup
# ═══════════════════════════════════════════════════════════════════════════════

async def set_my_commands() -> dict:
    """Register the bot's command list visible in the Telegram UI."""
    commands = [
        {"command": "start",    "description": "🙏 Welcome / नमस्ते"},
        {"command": "help",     "description": "📋 Help / सभी commands"},
        {"command": "posts",    "description": "📸 My recent posts"},
        {"command": "stats",    "description": "📊 Instagram analytics"},
        {"command": "schedule", "description": "⏰ Set auto-post schedule"},
        {"command": "connect",  "description": "🔗 Connect Instagram"},
        {"command": "language", "description": "🌐 Hindi / English toggle"},
        {"command": "cancel",   "description": "❌ Cancel current action"},
    ]
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/setMyCommands",
            json={"commands": commands},
        )
        resp.raise_for_status()
        return resp.json()
