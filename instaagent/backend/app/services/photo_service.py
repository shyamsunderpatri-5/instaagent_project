# backend/app/services/photo_service.py
# Image Processing — Remove.bg + Photoroom + Pillow compression

import io
import base64
import logging
from PIL import Image, ImageFilter, ImageEnhance, UnidentifiedImageError
from typing import Dict, Any, Tuple, Optional
from app.config import settings

logger = logging.getLogger(__name__)

def compress_image(image_bytes: bytes, max_size_kb: int = 500) -> bytes:
    """Compress image before sending to APIs — reduces cost and speeds up processing."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except (UnidentifiedImageError, ValueError) as e:
        logger.error("Failed to open image: %s", e)
        # If we can't open it, we can't compress it. Return as is and let the worker handle it.
        return image_bytes

    # Convert to RGB (handles PNG with alpha, WEBP, etc.)
    if img.mode in ("RGBA", "P", "LA"):
        # Create white background
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            # Use alpha channel as mask
            background.paste(img, mask=img.split()[3])
        elif img.mode == "LA":
            # Use alpha channel (index 1) as mask
            background.paste(img, mask=img.split()[1])
        else:
            # Mode P (palette) — convert to RGBA first for safe alpha handling
            rgba_img = img.convert("RGBA")
            background.paste(rgba_img, mask=rgba_img.split()[3])
        img = background
    else:
        img = img.convert("RGB")

    # Resize if too large (Instagram max 1080px)
    max_dim = 1080
    if img.width > max_dim or img.height > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)

    # Compress to target size
    output = io.BytesIO()
    quality = 92
    while quality > 40:
        output.seek(0)
        output.truncate()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        if len(output.getvalue()) <= max_size_kb * 1024:
            break
        quality -= 8

    return output.getvalue()


def sharpen_image(image_bytes: bytes, subtle: bool = False) -> bytes:
    """Apply sharpening and subtle color enhancement to fix blurry phone photos."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # 1. Sharpen
        img = img.filter(ImageFilter.SHARPEN)
        if not subtle:
            img = img.filter(ImageFilter.DETAIL)  # Extra detail pop only if not subtle
        
        # 2. Enhance Color & Contrast
        enhancer = ImageEnhance.Color(img)
        # subtle mode: minimal enhancement (1.02)
        img = enhancer.enhance(1.02 if subtle else 1.1) 
        
        enhancer = ImageEnhance.Contrast(img)
        # subtle mode: max 5% enhancement per enterprise standard
        img = enhancer.enhance(1.05 if subtle else 1.1) 
        
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=95)
        return output.getvalue()
    except Exception as e:
        logger.warning("Sharpening failed: %s. Returning original.", e)
        return image_bytes


async def remove_background(image_bytes: bytes, bg_color: str = "ffffff") -> Tuple[bytes, bool]:
    """
    Call Remove.bg API to remove background.
    Simulation fallback: returns original bytes + failure flag.
    """
    if settings.AI_SIMULATION or not settings.REMOVEBG_API_KEY:
        logger.info("🛠️ SIMULATION: Mocking background removal")
        return sharpen_image(image_bytes, subtle=True), True # bytes, failed_flag

    try:
        compressed = compress_image(image_bytes)
        import httpx  # Late import for dependency management
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.remove.bg/v1.0/removebg",
                headers={"X-Api-Key": settings.REMOVEBG_API_KEY},
                files={"image_file": ("photo.jpg", compressed, "image/jpeg")},
                data={"size": "auto", "bg_color": bg_color},
            )
            response.raise_for_status()
            return response.content, False
    except Exception as e:
        logger.warning("Remove.bg failed: %s. Returning original.", e)
        return sharpen_image(image_bytes, subtle=True), True


async def enhance_photo(image_bytes: bytes) -> Tuple[bytes, bool]:
    """
    Call Photoroom API v2.
    Simulation fallback: returns input if key is invalid or simulation is ON.
    """
    if settings.AI_SIMULATION or not settings.PHOTOROOM_API_KEY or "sandbox" in settings.PHOTOROOM_API_KEY:
        logger.info("🛠️ SIMULATION: Mocking Photoroom enhancement")
        return image_bytes, True

    try:
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://image-api.photoroom.com/v2/edit",
                headers={
                    "x-api-key": settings.PHOTOROOM_API_KEY,
                    "Accept": "image/png, application/json",
                },
                files={"imageFile": ("photo.png", image_bytes, "image/png")},
                data={
                    "background.color": "FFFFFF",
                    "padding": "0.1",
                    "shadow.mode": "ai.soft",
                    "lighting.mode": "ai.auto",
                    "outputSize": "1080x1080",
                    "removeBackground": "false",
                },
            )
            if response.status_code == 200:
                return response.content, False
            
            logger.warning("Photoroom API error %s: %s", response.status_code, response.text)
            return image_bytes, True
    except Exception as e:
        logger.warning("Photoroom failed: %s. Returning original.", e)
        return image_bytes, True


def image_to_base64(image_bytes: bytes) -> str:
    """Convert image bytes to base64 string for Claude Vision API."""
    return base64.b64encode(image_bytes).decode("utf-8")


async def full_photo_pipeline(image_bytes: bytes, subtle_only: bool = False, skip_editing: bool = False) -> dict:
    """
    Photo processing pipeline (v2 — background removal REMOVED):
    1. Compress original to Instagram-safe size
    2. Sharpen & subtle colour/contrast lift (fixes blurry phone pics)
    3. Optional: Pro enhancement via Photoroom (only if API key is valid)

    If skip_editing is True, it ONLY compresses and returns the original.
    """
    # Step 1: Compress to ≤500KB / 1080px max-dim
    compressed = compress_image(image_bytes)
    logger.info("Pipeline: compressed %dKB → %dKB", len(image_bytes)//1024, len(compressed)//1024)

    if skip_editing:
        return {
            "original_bytes": compressed,
            "edited_bytes": compressed,
            "is_subtle": True,
            "is_skipped": True,
            "vision_failed": False
        }

    # Step 2: Sharpen + colour lift — always subtle to keep product looking real
    sharpened = sharpen_image(compressed, subtle=True)
    
    # Step 3: Photoroom enhancement (optional)
    enhance_failed = False
    if not subtle_only:
        enhanced, enhance_failed = await enhance_photo(sharpened)
        final_image = enhanced
    else:
        final_image = sharpened

    return {
        "original_bytes": compressed,
        "edited_bytes": final_image,
        "is_subtle": subtle_only,
        "enhance_failed": enhance_failed,
        "vision_failed": False # Placeholder for worker
    }
