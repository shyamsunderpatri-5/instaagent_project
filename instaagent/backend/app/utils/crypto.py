# backend/app/utils/crypto.py
from cryptography.fernet import Fernet
from app.config import settings

def encrypt_token(token: str) -> str:
    """Encrypts a token using the app-wide encryption key."""
    if not token or not settings.ENCRYPTION_KEY:
        return token
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.encrypt(token.encode()).decode()

import urllib.parse

def decrypt_token(token: str) -> str:
    """Decrypts an encrypted token."""
    if not token or not settings.ENCRYPTION_KEY:
        return token
        
    try: # Handle potential URL-encoded tokens that come from the database / URL encoding bugs
        token = urllib.parse.unquote(token)
    except Exception:
        pass

    try:
        f = Fernet(settings.ENCRYPTION_KEY.encode())
        return f.decrypt(token.encode()).decode()
    except Exception:
        # Fallback if the token wasn't encrypted or key is wrong
        return token
