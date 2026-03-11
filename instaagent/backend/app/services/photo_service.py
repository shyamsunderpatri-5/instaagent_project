# backend/app/services/photo_service.py
# Image Processing — Remove.bg + Photoroom + Pillow compression

import httpx
from PIL import Image, ImageFilter, ImageEnhance
import io
import base64
from app.config import settings


def compress_image(image_bytes: bytes, max_size_kb: int = 500) -> bytes:
    """Compress image before sending to APIs — reduces cost and speeds up processing."""
    img = Image.open(io.BytesIO(image_bytes))

    # Convert to RGB (handles PNG with alpha, WEBP, etc.)
    if img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img)
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
    img = Image.open(io.BytesIO(image_bytes))
    
    # 1. Sharpen
    img = img.filter(ImageFilter.SHARPEN)
    if not subtle:
        img = img.filter(ImageFilter.DETAIL)  # Extra detail pop only if not subtle
    
    # 2. Enhance Color & Contrast
    enhancer = ImageEnhance.Color(img)
    # subtle mode: no color shift or minimal (1.02)
    img = enhancer.enhance(1.02 if subtle else 1.1) 
    
    enhancer = ImageEnhance.Contrast(img)
    # subtle mode: max 10% (1.1) per requirement
    img = enhancer.enhance(1.05 if subtle else 1.1) 
    
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=95)
    return output.getvalue()


async def remove_background(image_bytes: bytes, bg_color: str = "ffffff") -> bytes:
    """
    Call Remove.bg API to remove background.
    Simulation fallback: returns sharpened original image if key is invalid or simulation is ON.
    """
    if settings.AI_SIMULATION or not settings.REMOVEBG_API_KEY:
        print("🛠️ SIMULATION: Mocking background removal (sharpening instead)")
        return sharpen_image(image_bytes, subtle=True)

    try:
        compressed = compress_image(image_bytes)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.remove.bg/v1.0/removebg",
                headers={"X-Api-Key": settings.REMOVEBG_API_KEY},
                files={"image_file": ("photo.jpg", compressed, "image/jpeg")},
                data={"size": "auto", "bg_color": bg_color},
            )
            response.raise_for_status()
            return response.content
    except Exception as e:
        print(f"⚠️ Remove.bg failed: {e}. Falling back to simulation logic.")
        return sharpen_image(image_bytes, subtle=True)


async def enhance_photo(image_bytes: bytes) -> bytes:
    """
    Call Photoroom API v2.
    Simulation fallback: returns input if key is invalid or simulation is ON.
    """
    if settings.AI_SIMULATION or not settings.PHOTOROOM_API_KEY or "sandbox" in settings.PHOTOROOM_API_KEY:
        print("🛠️ SIMULATION: Mocking Photoroom enhancement")
        return image_bytes

    try:
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
                return response.content
            
            print(f"⚠️ Photoroom API error {response.status_code}: {response.text}")
            return image_bytes
    except Exception as e:
        print(f"⚠️ Photoroom failed: {e}. Returning original.")
        return image_bytes


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
    print(f"📸 Pipeline: compressed {len(image_bytes)//1024}KB → {len(compressed)//1024}KB", flush=True)

    if skip_editing:
        print(f"📸 Pipeline: skip_editing=True — preserving original", flush=True)
        return {
            "original_bytes": compressed,
            "edited_bytes": compressed,
            "is_subtle": True,
            "is_skipped": True,
        }

    # Step 2: Sharpen + colour lift — always subtle to keep product looking real
    sharpened = sharpen_image(compressed, subtle=True)
    print(f"📸 Pipeline: sharpened (subtle=True)", flush=True)

    # Step 3: Photoroom enhancement (optional — only if a real API key is configured)
    if not subtle_only:
        enhanced = await enhance_photo(sharpened)
        final_image = enhanced
        print(f"📸 Pipeline: Photoroom enhance attempted", flush=True)
    else:
        final_image = sharpened
        print(f"📸 Pipeline: skipping Photoroom (subtle_only mode)", flush=True)

    return {
        "original_bytes": compressed,
        "edited_bytes": final_image,
        "is_subtle": subtle_only,
    }
