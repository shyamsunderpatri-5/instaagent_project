# backend/app/services/whatsapp_service.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — WhatsApp Cloud API Client (Enterprise)
#
# All outbound WhatsApp messages go through this module.
# Meta Cloud API v19.0: https://graph.facebook.com/v19.0/{PHONE_ID}/messages
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Meta Graph API base
_META_BASE = "https://graph.facebook.com/v19.0"


def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type":  "application/json",
    }


# ─── Outbound messages ────────────────────────────────────────────────────────

async def send_wa_text(to: str, text: str) -> dict:
    """Send a plain text WhatsApp message."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                _clean_phone(to),
        "type":              "text",
        "text":              {"preview_url": False, "body": text},
    }
    return await _post_message(payload)


async def send_wa_image(to: str, image_url: str, caption: str = "") -> dict:
    """Send an image message from a public URL."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                _clean_phone(to),
        "type":              "image",
        "image": {
            "link":    image_url,
            "caption": caption,
        },
    }
    return await _post_message(payload)


async def send_wa_buttons(to: str, body: str, buttons: list[dict]) -> dict:
    """
    Send an interactive message with reply buttons (max 3 buttons).

    buttons = [
        {"id": "approve:post_id:enhanced", "title": "✨ Enhanced"},
        {"id": "approve:post_id:original", "title": "🖼 Original"},
        {"id": "discard:post_id",          "title": "🗑 Discard"},
    ]
    """
    # WhatsApp button IDs max 256 chars, titles max 20 chars
    wa_buttons = [
        {
            "type": "reply",
            "reply": {
                "id":    btn["id"][:256],
                "title": btn["title"][:20],
            },
        }
        for btn in buttons[:3]   # WA max 3 buttons
    ]

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                _clean_phone(to),
        "type":              "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body[:1024]},
            "action": {"buttons": wa_buttons},
        },
    }
    return await _post_message(payload)


async def send_wa_list(to: str, header: str, body: str, button_label: str, sections: list[dict]) -> dict:
    """Send an interactive list picker (for language or category selection)."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                _clean_phone(to),
        "type":              "interactive",
        "interactive": {
            "type":   "list",
            "header": {"type": "text", "text": header[:60]},
            "body":   {"text": body[:1024]},
            "action": {
                "button":   button_label[:20],
                "sections": sections,
            },
        },
    }
    return await _post_message(payload)


# ─── Media download ───────────────────────────────────────────────────────────

async def download_wa_media(media_id: str) -> bytes:
    """
    Download WhatsApp media securely.

    Step 1: Retrieve the temporary media URL (valid ~5 min)
    Step 2: Download the actual file bytes using Bearer auth

    IMPORTANT: Must be called promptly after receiving media_id — 
    Meta's media URLs expire quickly and cannot be re-fetched without the ID.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Get the media URL
        meta_resp = await client.get(
            f"{_META_BASE}/{media_id}",
            headers=_auth_headers(),
        )
        meta_resp.raise_for_status()
        media_url = meta_resp.json().get("url")

        if not media_url:
            raise ValueError(f"No media URL returned for media_id={media_id}")

        # Step 2: Download the actual bytes (must use Bearer auth!)
        file_resp = await client.get(
            media_url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
        )
        file_resp.raise_for_status()

    logger.info("WA media downloaded | media_id=%s | size=%d bytes", media_id, len(file_resp.content))
    return file_resp.content


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _clean_phone(phone: str) -> str:
    """
    Normalize phone number for Meta API:
    - Strip spaces, dashes, parentheses
    - Ensure starts with country code (e.g., 919876543210 for India)
    """
    cleaned = "".join(c for c in phone if c.isdigit())
    # If Indian number missing country code
    if len(cleaned) == 10:
        cleaned = "91" + cleaned
    return cleaned


async def _post_message(payload: dict) -> dict:
    """POST to Meta Cloud API and handle errors consistently."""
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_ID:
        logger.warning("WhatsApp not configured — WHATSAPP_TOKEN or WHATSAPP_PHONE_ID missing")
        return {"skipped": True}

    url = f"{_META_BASE}/{settings.WHATSAPP_PHONE_ID}/messages"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload, headers=_auth_headers())

    if resp.status_code not in (200, 201):
        logger.error(
            "WA send failed | to=%s | status=%d | body=%s",
            payload.get("to", "?"), resp.status_code, resp.text[:300],
        )
        resp.raise_for_status()

    data = resp.json()
    logger.info("WA message sent | to=%s | msg_id=%s", payload.get("to"), data.get("messages", [{}])[0].get("id"))
    return data
