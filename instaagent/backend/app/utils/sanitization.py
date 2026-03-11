# backend/app/utils/sanitization.py
import re

def sanitize_input(text: str) -> str:
    """Basic sanitization to prevent prompt injection and XSS."""
    if not text:
        return ""
    # Remove common injection characters but keep alphanumeric, space, and common punctuation
    # Focus on removing < > { } [ ] \ / |
    clean = re.sub(r'[<>{}\[\]\\/|]', '', text)
    return clean.strip()
