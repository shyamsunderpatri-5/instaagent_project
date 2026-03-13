# backend/app/services/photo_service.py
# Image Processing — Remove.bg + Photoroom + Pillow compression

import io
import base64
import logging
from PIL import Image, ImageFilter, ImageEnhance, UnidentifiedImageError
from typing import Dict, Any, Tuple, Optional
from app.config import settings

logger = logging.getLogger(__name__)

def compress_image(image_input: bytes | Image.Image, max_size_kb: int = 500) -> bytes:
    """
    Compress image before sending to APIs — reduces cost and speeds up processing.
    Accepts bytes or PIL.Image.Image. Always returns bytes (for API/Storage).
    """
    try:
        if isinstance(image_input, Image.Image):
            img = image_input.copy()
        else:
            img = Image.open(io.BytesIO(image_input))
    except (UnidentifiedImageError, ValueError) as e:
        logger.error("Failed to open image: %s", e)
        return image_input if isinstance(image_input, bytes) else b""

    # Convert to RGB (handles PNG with alpha, WEBP, etc.)
    if img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            background.paste(img, mask=img.split()[3])
        elif img.mode == "LA":
            background.paste(img, mask=img.split()[1])
        else:
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


def _sharpen_image_obj(img: Image.Image, subtle: bool = False) -> Image.Image:
    """Internal helper that operates on PIL Image objects to prevent re-encoding loss."""
    # 1. Sharpen
    img = img.filter(ImageFilter.SHARPEN)
    if not subtle:
        img = img.filter(ImageFilter.DETAIL)
    
    # 2. Enhance Color & Contrast
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.02 if subtle else 1.1) 
    
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.05 if subtle else 1.1) 
    return img


def sharpen_image(image_bytes: bytes, subtle: bool = False) -> bytes:
    """Wrapper that preserves the public 'bytes' interface but uses the object helper."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = _sharpen_image_obj(img, subtle)
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
        return image_bytes, True # bytes (original, not sharpened), failed_flag

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
        logger.warning("Remove.bg failed: %s. Returning pristine original.", e)
        return image_bytes, True


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
    # Step 1: Open and Compress to ≤500KB / 1080px max-dim
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        logger.error("Pipeline failed to parse image: %s", e)
        return {"original_bytes": image_bytes, "edited_bytes": image_bytes, "vision_failed": True, "error": str(e)}

    # Initial compression for API compatibility (max dimensions/size)
    compressed_bytes = compress_image(img, max_size_kb=500)
    logger.info("Pipeline: input %dKB → compressed %dKB", len(image_bytes)//1024, len(compressed_bytes)//1024)

    if skip_editing:
        return {
            "original_bytes": compressed_bytes,
            "edited_bytes": compressed_bytes,
            "is_subtle": True,
            "is_skipped": True,
            "vision_failed": False
        }

    # Step 2: Sharpen + colour lift — always subtle to keep product looking real
    # Refactor A1.3: Apply sharpening to the PIL object directly to avoid re-encoding
    img = _sharpen_image_obj(img, subtle=True)
    
    # Step 3: Photoroom enhancement (optional)
    enhance_failed = False
    if not subtle_only:
        # Convert to bytes for Photoroom API
        buff = io.BytesIO()
        img.save(buff, format="PNG") # PNG to preserve quality for Photoroom
        sharpened_bytes = buff.getvalue()
        
        enhanced_bytes, enhance_failed = await enhance_photo(sharpened_bytes)
        final_bytes = enhanced_bytes
    else:
        # No Photoroom, save current sharpened state to JPEG
        buff = io.BytesIO()
        img.save(buff, format="JPEG", quality=95)
        final_bytes = buff.getvalue()

    return {
        "original_bytes": compressed_bytes,
        "edited_bytes": final_bytes,
        "is_subtle": subtle_only,
        "enhance_failed": enhance_failed,
        "vision_failed": False
    }
