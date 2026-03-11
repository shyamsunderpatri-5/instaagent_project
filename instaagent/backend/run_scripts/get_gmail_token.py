"""
Run this script ONCE to get your Gmail Refresh Token.
Steps:
  1. Fill in your GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in .env first
  2. Run: python run_scripts/get_gmail_token.py
  3. A browser will open — login and allow permissions
  4. Copy the printed Refresh Token into your .env file
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GMAIL_CLIENT_ID     = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")

if not GMAIL_CLIENT_ID or "your_client_id" in GMAIL_CLIENT_ID:
    print("❌ ERROR: Please set GMAIL_CLIENT_ID in your .env file first!")
    exit(1)

if not GMAIL_CLIENT_SECRET or "your_client_secret" in GMAIL_CLIENT_SECRET:
    print("❌ ERROR: Please set GMAIL_CLIENT_SECRET in your .env file first!")
    exit(1)

# Gmail send scope
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Build client config from env vars
client_config = {
    "installed": {
        "client_id":     GMAIL_CLIENT_ID,
        "client_secret": GMAIL_CLIENT_SECRET,
        "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
        "token_uri":     "https://oauth2.googleapis.com/token",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
    }
}

print("🌐 Opening browser for Gmail authorization...")
print("   → Login with your sender Gmail account")
print("   → Click 'Allow' to grant send permissions\n")

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
creds = flow.run_local_server(port=0)

print("\n" + "="*60)
print("✅ SUCCESS! Copy this into your .env file:")
print("="*60)
print(f"\nGMAIL_REFRESH_TOKEN={creds.refresh_token}\n")
print("="*60)

# python run_scripts/get_gmail_token.py