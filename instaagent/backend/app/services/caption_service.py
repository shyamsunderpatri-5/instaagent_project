# backend/app/services/caption_service.py
# Core AI Service — Generates Hindi + English captions via Claude API
# FIXED: Uses AsyncAnthropic so async functions don't block the event loop

import anthropic
import json
import re
from app.config import settings
from app.utils.sanitization import sanitize_input
from app.utils.decorators import retry_on_exception


def _get_client() -> anthropic.AsyncAnthropic:
    """Return a fresh Anthropic client using the current settings (not a stale module-level instance)."""
    return anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


LANGUAGE_NAMES = {
    "hi": "Hindi (Devanagari script)",
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
    "mr": "Marathi",
    "en": "English only",
}

CATEGORY_HINTS = {
    "jewellery": "Focus on craftsmanship, purity, occasion-wear appeal",
    "clothing": "Focus on fabric, style, occasion, comfort",
    "food": "Focus on taste, freshness, ingredients, health benefits",
    "handmade": "Focus on uniqueness, artisan skill, local craft",
    "furniture": "Focus on quality, durability, home decor appeal",
    "cosmetics": "Focus on natural ingredients, skin benefits, glow",
    "electronics": "Focus on features, value, reliability",
}


async def generate_caption(
    product_name: str,
    product_type: str,
    language: str = "hi",
    additional_info: str = "",
    festival: str = None,
    business_name: str = "",
    is_enhanced: bool = False,
) -> dict:
    """
    Generate Instagram caption + hashtags using Claude API.
    Simulation fallback: returns static mock JSON if key is invalid or simulation is ON.
    """
    if settings.AI_SIMULATION or not settings.ANTHROPIC_API_KEY:
        print(f"🛠️ SIMULATION: Mocking caption for {product_name}")
        return {
            "caption_hindi": f"✨ हमारा नया {product_name}! बहुत ही सुंदर और प्रीमियम क्वालिटी। आज ही ऑर्डर करें! {additional_info}",
            "caption_english": f"✨ Our new {product_name}! Beautiful craftsmanship and premium quality. Order yours today! {additional_info}",
            "hashtags": ["#instaagent", "#smallbusiness", f"#{product_type}", "#premium", "#india"],
            "cta": "DM to Order",
            "best_time_to_post": "Evening 7 PM",
            "caption_short": f"Check out our {product_name}!"
        }

    try:
        product_name = sanitize_input(product_name)
        additional_info = sanitize_input(additional_info)

        lang_name = LANGUAGE_NAMES.get(language, "Hindi")
        category_hint = CATEGORY_HINTS.get(product_type, "Focus on quality and value")
        festival_hint = f"Upcoming festival: {festival}. Make the caption festive and celebratory." if festival else ""
        business_hint = f"Business name: {business_name}." if business_name else ""
        reality_check = (
            "Reality Check: This photo has been enhanced for better visibility. "
            "Assuming this is the real product, mention that 'natural lighting may vary' "
            "subtly in the caption to keep it authentic."
        ) if is_enhanced else ""

        system = """You are an expert Instagram content creator and SEO specialist for Indian small businesses.
    You deeply understand Indian buying psychology, trending aesthetics, and algorithm-friendly post structures. 
    Generate captions that drive sales, saves, and shares.
    CRITICAL: Respond ONLY with valid JSON. No markdown, no explanation, just raw JSON."""

        prompt = f"""
    Product Name: {product_name}
    Category: {product_type}
    {business_hint}
    Primary Language: {lang_name}
    Extra Details: {additional_info or "None provided"}
    {festival_hint}
    {reality_check}
    Category Strategy: {category_hint}

    Generate a high-conversion Instagram post. Use a mix of storytelling and sales-driven hooks.
    For hashtags, include a mix of: 1) Broad reach tags, 2) Specific niche tags (Indian context), 3) Location-based tags, and 4) Trending SEO keywords.

    Return ONLY this JSON structure:
    {{
      "caption_hindi": "Captivating and emotional Hindi caption (Devanagari). Use vibrant emojis. Highlight 2 key benefits. End with a strong Call-to-Action.",
      "caption_english": "SEO-friendly English caption. Premium tone. Use curiosity-driven opening. Clear value proposition. End with CTA.",
      "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8", "#tag9", "#tag10", "#tag11", "#tag12", "#tag13", "#tag14", "#tag15", "#tag16", "#tag17", "#tag18", "#tag19", "#tag20"],
      "cta": "Short Hindi CTA like 'DM karo / Order karo'",
      "best_time_to_post": "Morning 9am / Evening 7pm / Night 9pm",
      "caption_short": "One punchy line for Stories in {lang_name}"
    }}"""

        response = await _get_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1200,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as e:
        print(f"⚠️ Anthropic caption failed: {e}. Returning mock.")
        return {
            "caption_hindi": f"✨ {product_name} - प्रीमियम क्वालिटी। ऑर्डर करने के लिए मैसेज करें।",
            "caption_english": f"✨ {product_name} - Premium quality. DM to order now.",
            "hashtags": ["#instaagent", "#shopping"],
            "cta": "DM to Order",
            "best_time_to_post": "Now",
            "caption_short": product_name
        }


async def generate_comment_reply(
    comment_text: str,
    product_name: str,
    language: str = "hi",
) -> str:
    """
    Generate a reply to an Instagram comment.
    Simulation fallback: returns a polite static reply.
    """
    if settings.AI_SIMULATION or not settings.ANTHROPIC_API_KEY:
        return "Thank you so much! Please check your DM for more details. 🙏"

    try:
        system = """You are a friendly Indian business owner replying to Instagram comments.
    Be warm, genuine, and move toward a sale without being pushy.
    Reply in the same language as the comment. Keep it under 2 sentences.
    Do NOT use markdown. Just plain text."""

        prompt = f"""
    Instagram comment on post about: {product_name}
    Comment: "{comment_text}"
    Preferred language: {LANGUAGE_NAMES.get(language, "Hindi")}

    Write a warm, brief reply that thanks them and gently encourages a purchase/DM."""

        response = await _get_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"⚠️ Anthropic reply failed: {e}")
        return "Thank you! DM us for more info."


async def analyze_product_photo(image_base64: str) -> dict:
    """
    Use Claude Vision to analyze a product photo.
    Simulation fallback: returns generic product analysis.
    """
    if settings.AI_SIMULATION or not settings.ANTHROPIC_API_KEY:
        print("🛠️ SIMULATION: Mocking Vision analysis")
        return {
            "product_type": "other",
            "colors": ["dynamic"],
            "materials": "High quality",
            "suggested_name": "New Collection Item",
            "quality_score": 9,
            "improvements": "None"
        }

    try:
        response = await _get_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Analyze this product photo for an Indian small business Instagram post. Return ONLY valid JSON.",
                        },
                    ],
                }
            ],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as e:
        print(f"⚠️ Anthropic vision failed: {e}")
        return {"product_type": "other"}

@retry_on_exception(retries=3)
async def generate_reels_script(product_name: str, additional_info: str):
    """Generates a high-conversion Reels script with visual cues."""
    product_name = sanitize_input(product_name)
    additional_info = sanitize_input(additional_info)
    
    prompt = f"""
    Create a 30-60 second Instagram Reels script for a product.
    Product: {product_name}
    Details: {additional_info}

    Format the output as JSON with these keys:
    - hook: Strong opening line
    - scenes: List of objects with 'visual' and 'voiceover' keys
    - call_to_action: Closing line
    - music_vibe: Suggested audio style
    """
    
    response = await _get_client().messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text
    return text


@retry_on_exception(retries=2)
async def get_seo_hashtags(
    product_name: str,
    product_type: str,
    language: str = "hi",
) -> list:
    """
    Generate 20 high-reach SEO hashtags for the specific product and platform.
    """
    product_name = sanitize_input(product_name)
    system = "You are an Indian Instagram SEO expert. Return ONLY a JSON list of 20 hashtags."
    prompt = f"""Product: {product_name}, Category: {product_type}, Language: {LANGUAGE_NAMES.get(language, 'Hindi')}. 
    Generate 20 high-reach hashtags that will get maximum visibility in India. 
    Include:
    - 5 Trending general tags (e.g. #trendingindia, #viralreels if applicable)
    - 5 Category-specific tags
    - 5 Shopping/Small business tags (e.g. #vocalforlocal, #smallbusinessindia)
    - 5 Niche descriptive tags for the specific item.
    """

    response = await _get_client().messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    # Match any hashtags in the response if JSON fails or as fallback
    tags = re.findall(r"#\w+", raw)
    return tags[:20]
