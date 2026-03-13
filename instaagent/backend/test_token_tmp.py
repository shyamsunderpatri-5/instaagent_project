
import sys
import os
from jose import jwt
from datetime import datetime, timedelta, timezone

# Add backend to path
sys.path.append(os.getcwd())

from app.config import settings

def test_token_logic():
    print(f"Testing with JWT_SECRET: {settings.JWT_SECRET[:10]}...")
    print(f"Algorithm: {settings.JWT_ALGORITHM}")
    
    user_id = "test-user-id"
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "exp": exp,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    print(f"Generated token: {token[:20]}...")
    
    try:
        decoded = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        print("Successfully decoded token!")
        print(f"Decoded payload sub: {decoded.get('sub')}")
        if decoded.get('sub') == user_id:
            print("Token logic is consistent.")
        else:
            print("Token sub mismatch!")
    except Exception as e:
        print(f"Token verification failed: {e}")

if __name__ == "__main__":
    test_token_logic()
