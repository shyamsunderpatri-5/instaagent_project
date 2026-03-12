# backend/app/services/aggregator_service.py
import logging
import httpx
import json
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
from app.config import settings
from app.db.supabase import get_supabase
from app.utils.crypto import decrypt_token, encrypt_token
from app.services.instagram_service import GRAPH_BASE, GRAPH_VERSION
from app.services.caption_service import _get_client
from app.utils.sanitization import sanitize_input

logger = logging.getLogger(__name__)

class AggregatorService:
    def __init__(self):
        self.supabase = get_supabase()

    async def fetch_and_save_posts(self, aggregator_account_id: UUID) -> int:
        """Fetch latest posts for an account and save to DB."""
        # 1. Get account details
        acc_resp = self.supabase.table("aggregator_accounts").select("*").eq("id", str(aggregator_account_id)).execute()
        if not acc_resp.data:
            logger.error(f"Aggregator account {aggregator_account_id} not found")
            return 0
        
        account = acc_resp.data[0]
        username = account["instagram_username"]
        account_type = account["account_type"]
        user_id = account["user_id"]

        # 2. Fetch posts based on account type
        posts = []
        if account_type == "owned":
            # Use user's token (either from account or from users table)
            token = account.get("access_token")
            if token:
                token = decrypt_token(token)
            else:
                user_resp = self.supabase.table("users").select("instagram_token").eq("id", user_id).execute()
                token = decrypt_token(user_resp.data[0].get("instagram_token")) if user_resp.data else None
            
            if token:
                posts = await self._fetch_owned_posts(username, token)
        else:
            # Competitor: Use Business Discovery
            user_resp = self.supabase.table("users").select("instagram_id, instagram_token").eq("id", user_id).execute()
            if user_resp.data:
                ig_id = user_resp.data[0].get("instagram_id")
                token = decrypt_token(user_resp.data[0].get("instagram_token"))
                if ig_id and token:
                    posts = await self._fetch_competitor_posts(ig_id, username, token)

        # 3. Save to DB
        saved_count = 0
        for p in posts:
            post_data = {
                "aggregator_account_id": str(aggregator_account_id),
                "ig_post_id": p["id"],
                "caption": p.get("caption"),
                "media_url": p.get("media_url"),
                "media_type": p.get("media_type"),
                "likes": p.get("like_count", 0),
                "comments": p.get("comments_count", 0),
                "hashtags": self._extract_hashtags(p.get("caption", "")),
                "posted_at": p.get("timestamp"),
            }
            try:
                # Upsert based on ig_post_id and aggregator_account_id
                self.supabase.table("aggregated_posts").upsert(post_data, on_conflict="aggregator_account_id, ig_post_id").execute()
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving post {p['id']}: {e}")

        # 4. Update last_synced_at
        self.supabase.table("aggregator_accounts").update({"last_synced_at": datetime.now(timezone.utc).isoformat()}).eq("id", str(aggregator_account_id)).execute()
        
        return saved_count

    async def generate_ai_insights(self, account_ids: List[UUID], user_id: UUID) -> Dict[str, Any]:
        """Use Claude to analyze posts across multiple accounts and generate trends/ideas."""
        # 1. Fetch recent posts from these accounts in a single query (Fix N+1)
        resp = self.supabase.table("aggregated_posts")\
            .select("caption, likes, comments, hashtags, posted_at")\
            .in_("aggregator_account_id", [str(aid) for aid in account_ids])\
            .order("posted_at", desc=True)\
            .limit(30)\
            .execute()
        post_data = resp.data or []

        if not post_data:
            return {"error": "No post data found for analysis"}

        # 2. Prepare prompt for Claude (Sanitized)
        post_summary = "\n".join([
            f"Post: {sanitize_input(p.get('caption', ''))[:100]}... | Likes: {p['likes']} | Comments: {p['comments']}"
            for p in post_data
        ])

        system = """You are an elite Instagram growth strategist and trend analyst.
Analyze the provided post data from competitors and owned accounts.
Identify patterns, high-performing content types, and trending topics in the Indian small business niche.
Respond ONLY with valid JSON."""

        prompt = f"""
Analyze these recent Instagram posts:
{post_summary}

Generate:
1. post_ideas: 5 creative post ideas based on what's working.
2. trend_summaries: 3 key trends observed (e.g., specific aesthetics, hooks, or topics).
3. best_posting_times: Recommended times based on engagement patterns.
4. caption_suggestions: 3 short, punchy caption hooks.

Return ONLY this JSON structure:
{{
  "post_ideas": ["..."],
  "trend_summaries": ["..."],
  "best_posting_times": ["..."],
  "caption_suggestions": ["..."]
}}"""

        client = _get_client()
        response = await client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        # Log usage
        tokens_in = response.usage.input_tokens if hasattr(response, "usage") else 0
        tokens_out = response.usage.output_tokens if hasattr(response, "usage") else 0
        # rough cost calculation: $3/$15 per million tokens for Sonnet
        cost_paise = round((tokens_in * (3/1000000) + tokens_out * (15/1000000)) * 83 * 100, 2)

        usage_log = {
            "user_id": str(user_id),
            "action": "aggregator_ai_analysis",
            "api_service": "anthropic_claude",
            "month_year": datetime.now().strftime("%Y-%m"),
            "cost_paise": cost_paise,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out
        }
        self.supabase.table("usage_logs").insert(usage_log).execute()

        raw = response.content[0].text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    async def _fetch_owned_posts(self, username: str, token: str) -> List[Dict[str, Any]]:
        """Fetch posts for an owned account using Basic Display API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{GRAPH_BASE}/me/media",
                params={
                    "fields": "id,caption,media_type,media_url,permalink,timestamp,username,like_count,comments_count",
                    "access_token": token,
                    "limit": 25
                }
            )
            resp.raise_for_status()
            return resp.json().get("data", [])

    async def _fetch_competitor_posts(self, ig_business_id: str, competitor_username: str, token: str) -> List[Dict[str, Any]]:
        """Fetch posts for a competitor using Business Discovery API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            query = f"business_discovery.username({competitor_username}){{media{{id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count}}}}"
            resp = await client.get(
                f"{GRAPH_BASE}/{ig_business_id}",
                params={
                    "fields": query,
                    "access_token": token
                }
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("business_discovery", {}).get("media", {}).get("data", [])

    def _extract_hashtags(self, caption: str) -> List[str]:
        if not caption:
            return []
        return re.findall(r"#\w+", caption)

aggregator_service = AggregatorService()
