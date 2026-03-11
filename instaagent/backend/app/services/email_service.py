# backend/app/services/email_service.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Email Service via Gmail API
#
# Supports two auth modes — auto-detected from .env:
#
#   MODE A (your setup): Personal Gmail → pssundaar@gmail.com
#   ──────────────────────────────────────────────────────────
#   Uses OAuth2 Refresh Token. One-time 5-minute setup.
#   Required .env vars:
#       EMAIL_SENDER        = pssundaar@gmail.com
#       GMAIL_CLIENT_ID     = from GCP OAuth2 Desktop credentials
#       GMAIL_CLIENT_SECRET = from GCP OAuth2 Desktop credentials
#       GMAIL_REFRESH_TOKEN = run: python scripts/get_gmail_token.py
#
#   MODE B: Google Workspace only (@yourdomain.com accounts)
#   ─────────────────────────────────────────────────────────
#   Uses GCP Service Account + domain-wide delegation.
#   DOES NOT work with @gmail.com personal accounts.
#   Required .env vars:
#       EMAIL_SENDER = your@workspace-domain.com
#       GCP_SA_KEY   = entire service account JSON as one line
#
# Why NOT SMTP for your case:
#   • Cloud hosts (Render/Railway) block port 587 outbound
#   • Gmail SMTP requires App Password which breaks if 2FA changes
#   • Gmail API uses HTTPS (port 443) — never blocked
#   • 500 sends/day limit on Gmail API vs 100/day on SMTP
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import base64
import json
import logging
import threading
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings

log = logging.getLogger(__name__)

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

_service_cache: Optional[object] = None
_service_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────────────────────
# SERVICE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_gmail_service():
    """
    Build and cache a Gmail API v1 service client.
    Thread-safe — built once, reused for all emails.

    Auto-detects which auth mode to use:
      GMAIL_REFRESH_TOKEN present → OAuth2 (personal Gmail)  ← your setup
      GCP_SA_KEY present          → Service Account (Workspace only)
    """
    global _service_cache

    with _service_lock:
        if _service_cache is not None:
            return _service_cache

        from googleapiclient.discovery import build

        # ── MODE A: OAuth2 Refresh Token — works with pssundaar@gmail.com ──────
        if settings.GMAIL_REFRESH_TOKEN:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request

            creds = Credentials(
                token=None,                                      # auto-refreshed on first use
                refresh_token=settings.GMAIL_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GMAIL_CLIENT_ID,
                client_secret=settings.GMAIL_CLIENT_SECRET,
                scopes=[GMAIL_SEND_SCOPE],
            )

            # Validate credentials now — catch config errors at startup, not at send time
            creds.refresh(Request())

            _service_cache = build(
                "gmail", "v1",
                credentials=creds,
                cache_discovery=False,
            )
            log.info(
                "Gmail API ready | mode=OAuth2 | sender=%s",
                settings.EMAIL_SENDER,
            )

        # ── MODE B: Service Account — Google Workspace @yourdomain.com only ────
        elif settings.GCP_SA_KEY:
            from google.oauth2 import service_account

            try:
                sa_info = json.loads(settings.GCP_SA_KEY)
            except (json.JSONDecodeError, ValueError) as exc:
                raise RuntimeError(
                    "GCP_SA_KEY is not valid JSON.\n"
                    "Paste the ENTIRE service account JSON as one line.\n"
                    "Tip: python -c \"import json; print(json.dumps(json.load(open('key.json'))))\""
                ) from exc

            # WARNING: This will 403 with personal @gmail.com accounts.
            # Only works if EMAIL_SENDER is a Google Workspace address.
            creds = service_account.Credentials.from_service_account_info(
                sa_info, scopes=[GMAIL_SEND_SCOPE],
            ).with_subject(settings.EMAIL_SENDER)

            _service_cache = build(
                "gmail", "v1",
                credentials=creds,
                cache_discovery=False,
            )
            log.info(
                "Gmail API ready | mode=ServiceAccount | sender=%s",
                settings.EMAIL_SENDER,
            )

        else:
            raise RuntimeError(
                "Gmail not configured. Add to .env:\n"
                "  GMAIL_REFRESH_TOKEN + GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET\n"
                "Then run: python scripts/get_gmail_token.py"
            )

        return _service_cache


def _to_base64url(mime_msg: MIMEMultipart) -> str:
    return base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def _build_otp_mime(to_email: str, to_name: str, otp: str) -> MIMEMultipart:
    year    = datetime.now().year
    subject = f"Your InstaAgent verification code: {otp}"

    plain = (
        f"InstaAgent — Password Reset\n\n"
        f"Hi {to_name},\n\n"
        f"Your 6-digit OTP: {otp}\n\n"
        f"Expires in 10 minutes. Do not share with anyone.\n\n"
        f"Didn't request this? Ignore this email — your account is safe.\n\n"
        f"— InstaAgent Team, Hyderabad"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#060A14;
             font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
         style="background:#060A14;padding:48px 20px;">
    <tr><td align="center">
      <table role="presentation" width="520" cellspacing="0" cellpadding="0"
             style="background:#0A1221;border:1px solid rgba(255,255,255,0.07);
                    border-radius:18px;overflow:hidden;max-width:520px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#2D4FD6 0%,#6B8BFF 100%);
                     padding:26px 36px;text-align:center;">
            <table role="presentation" cellspacing="0" cellpadding="0" align="center">
              <tr>
                <td style="background:rgba(255,255,255,0.18);border-radius:10px;
                           width:42px;height:42px;text-align:center;vertical-align:middle;">
                  <span style="font-size:22px;line-height:42px;">📸</span>
                </td>
                <td style="padding-left:10px;vertical-align:middle;">
                  <span style="font-size:20px;font-weight:800;color:#fff;
                               letter-spacing:-0.3px;">InstaAgent</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 36px 28px;">
            <p style="margin:0 0 5px;font-size:11px;font-weight:700;
                      letter-spacing:0.09em;text-transform:uppercase;color:#4F72F8;">
              Password Reset
            </p>
            <h1 style="margin:0 0 14px;font-size:22px;font-weight:800;
                       color:#F1F5FC;line-height:1.2;letter-spacing:-0.3px;">
              Hi {to_name} 👋
            </h1>
            <p style="margin:0 0 28px;font-size:14px;color:#8A9BBF;line-height:1.65;">
              We received a password reset request for your InstaAgent account.
              Use the code below to verify. Valid for
              <strong style="color:#F1F5FC;">10 minutes</strong>, single use only.
            </p>

            <!-- OTP Box -->
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                   style="margin-bottom:28px;">
              <tr>
                <td style="background:#060A14;border:2px solid rgba(79,114,248,0.40);
                           border-radius:14px;padding:28px 20px;text-align:center;">
                  <p style="margin:0 0 8px;font-size:11px;font-weight:700;
                            letter-spacing:0.13em;text-transform:uppercase;color:#4A5A72;">
                    Verification Code
                  </p>
                  <p style="margin:0;font-size:48px;font-weight:900;color:#4F72F8;
                            letter-spacing:18px;
                            font-family:'Courier New',Courier,monospace;line-height:1;">
                    {otp}
                  </p>
                  <p style="margin:10px 0 0;font-size:12px;color:#4A5A72;">
                    Expires in 10 minutes
                  </p>
                </td>
              </tr>
            </table>

            <p style="margin:0 0 8px;font-size:13px;color:#4A5A72;line-height:1.6;">
              🔒 <strong style="color:#8A9BBF;">Never share this code</strong> with anyone,
              including InstaAgent support. We will never ask for your OTP.
            </p>
            <p style="margin:0;font-size:13px;color:#4A5A72;line-height:1.6;">
              Didn't request this? Ignore this email — your account is unchanged and safe.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="border-top:1px solid rgba(255,255,255,0.06);
                     padding:18px 36px;text-align:center;">
            <p style="margin:0;font-size:11px;color:#4A5A72;">
              © {year} InstaAgent · Hyderabad, India
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_SENDER}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))
    return msg


def _build_welcome_mime(to_email: str, to_name: str) -> MIMEMultipart:
    year    = datetime.now().year
    subject = f"Welcome to InstaAgent, {to_name}! 🚀"

    plain = (
        f"Hi {to_name},\n\n"
        f"Welcome to InstaAgent! Your free account is live.\n\n"
        f"  • Upload product photos via Telegram\n"
        f"  • Get AI captions in Hindi, Telugu, Tamil, Kannada & more\n"
        f"  • Background removal + photo enhancement included\n"
        f"  • Direct Instagram posting\n\n"
        f"Free plan: 5 posts/month. Upgrade anytime.\n\n"
        f"— InstaAgent Team, Hyderabad"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#060A14;
             font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
         style="background:#060A14;padding:48px 20px;">
    <tr><td align="center">
      <table role="presentation" width="520" cellspacing="0" cellpadding="0"
             style="background:#0A1221;border:1px solid rgba(255,255,255,0.07);
                    border-radius:18px;overflow:hidden;max-width:520px;">
        <tr>
          <td style="background:linear-gradient(135deg,#2D4FD6,#6B8BFF);
                     padding:26px 36px;text-align:center;">
            <span style="font-size:20px;font-weight:800;color:#fff;">📸 InstaAgent</span>
          </td>
        </tr>
        <tr>
          <td style="padding:36px;">
            <h1 style="margin:0 0 12px;font-size:24px;font-weight:800;
                       color:#F1F5FC;letter-spacing:-0.3px;">
              Welcome, {to_name}! 🎉
            </h1>
            <p style="margin:0 0 24px;font-size:14px;color:#8A9BBF;line-height:1.65;">
              Your free InstaAgent account is ready. Start creating AI-powered
              Instagram captions for your products today.
            </p>
            <table role="presentation" cellspacing="0" cellpadding="0">
              {"".join(
                f'<tr><td style="padding:5px 0;font-size:14px;color:#8A9BBF;">'
                f'<span style="color:#4F72F8;font-weight:700;margin-right:8px;">✓</span>'
                f'{f}</td></tr>'
                for f in [
                    "5 free posts/month",
                    "Hindi, Telugu, Tamil, Kannada, Marathi captions",
                    "Background removal + photo enhancement",
                    "Telegram bot notifications",
                    "Direct Instagram posting",
                ]
              )}
            </table>
          </td>
        </tr>
        <tr>
          <td style="border-top:1px solid rgba(255,255,255,0.06);
                     padding:18px 36px;text-align:center;">
            <p style="margin:0;font-size:11px;color:#4A5A72;">
              © {year} InstaAgent · Hyderabad, India
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_SENDER}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))
    return msg


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────

def _dispatch(mime_msg: MIMEMultipart, to_email: str, label: str) -> None:
    """
    Send email via Gmail API in a background daemon thread.
    Returns immediately — never blocks the API response.
    Failures are logged, never raised (prevents email enumeration).
    """
    def _worker():
        try:
            svc = _build_gmail_service()
            svc.users().messages().send(
                userId="me",
                body={"raw": _to_base64url(mime_msg)},
            ).execute()
            log.info("Email sent | type=%s | to=%s", label, to_email)
        except Exception as exc:
            log.error("Email failed | type=%s | to=%s | error=%s", label, to_email, exc)

    threading.Thread(
        target=_worker,
        daemon=True,
        name=f"email-{label}-{to_email.split('@')[0][:8]}",
    ).start()


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API — called from backend/app/api/auth.py
# ─────────────────────────────────────────────────────────────────────────────

def send_otp_email(to_email: str, to_name: str, otp: str) -> None:
    """
    Send OTP verification email for password reset.
    Non-blocking. Args: plain-text email, display name, 6-digit OTP string.
    """
    _dispatch(_build_otp_mime(to_email, to_name, otp), to_email, "otp")


def send_welcome_email(to_email: str, to_name: str) -> None:
    """Send welcome email after successful registration. Non-blocking."""
    _dispatch(_build_welcome_mime(to_email, to_name), to_email, "welcome")