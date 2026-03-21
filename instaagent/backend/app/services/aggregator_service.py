# backend/app/services/aggregator_service.py
import logging
import httpx
import json
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
from app.config import settings
from app.db.supabase import get_supabase
from app.utils.crypto import decrypt_token, encrypt_token
from app.services.instagram_service import GRAPH_BASE, GRAPH_VERSION
from app.services.caption_service import _get_client
from app.utils.sanitization import sanitize_input
from app.db.redis_client import get_redis
import hashlib

logger = logging.getLogger(__name__)

class AggregatorService:
    def __init__(self):
        pass

    def _get_supabase(self):
        return get_supabase()

    async def fetch_and_save_posts(self, aggregator_account_id: UUID) -> int:
        """Fetch latest posts for an account and save to DB."""
        supabase = self._get_supabase()
        # 1. Get account details — include user_id filter for safety
        acc_resp = supabase.table("aggregator_accounts") \
            .select("*") \
            .eq("id", str(aggregator_account_id)) \
            .execute()
            
        if not acc_resp.data:
            logger.error("Aggregator account %s not found", aggregator_account_id)
            return 0
        
        account = acc_resp.data[0]
        username = account["instagram_username"]
        account_type = account["account_type"]
        user_id = str(account["user_id"])

        # 2. Fetch posts and metrics based on account type
        posts = []
        sync_error = None
        followers = 0
        following = 0
        
        try:
            if account_type == "owned":
                # Use user's token (either from account or from users table)
                token = account.get("access_token")
                if token:
                    token = decrypt_token(token)
                else:
                    user_resp = supabase.table("users").select("instagram_token").eq("id", user_id).execute()
                    token = decrypt_token(user_resp.data[0].get("instagram_token")) if user_resp.data else None
                
                if token:
                    posts_data = await self._fetch_owned_posts(username, token)
                    posts = posts_data.get("posts", [])
                    followers = posts_data.get("followers", 0)
                    following = posts_data.get("following", 0)
                else:
                    sync_error = "No active Instagram token found for owned account"
            else:
                # Competitor: Use Business Discovery
                user_resp = supabase.table("users").select("instagram_id, instagram_token").eq("id", user_id).execute()
                if user_resp.data:
                    ig_id = user_resp.data[0].get("instagram_id")
                    token = decrypt_token(user_resp.data[0].get("instagram_token"))
                    if ig_id and token:
                        comp_data = await self._fetch_competitor_posts(ig_id, username, token)
                        posts = comp_data.get("posts", [])
                        followers = comp_data.get("followers", 0)
                        following = comp_data.get("following", 0)
                    else:
                        sync_error = "Missing Business Profile ID or Token for competitor sync"
                else:
                    sync_error = "User not found or missing credentials"
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status in (400, 401, 403):
                # Non-retryable: token expired or account restricted
                sync_error = f"Instagram API {status}: Token invalid or account restricted/private"
                logger.warning("Non-retryable IG error %s for %s", status, username)
            else:
                # Let transient errors (429, 5xx) propagate for Celery retry
                raise
        except Exception as e:
            logger.error("Unexpected error syncing %s: %s", username, str(e))
            sync_error = f"Internal Sync Error: {str(e)[:100]}"

        # 3. Save to DB
        saved_count = 0
        for p in posts:
            likes = p.get("like_count", 0)
            comments = p.get("comments_count", 0)
            # Engagement Rate = ((likes + comments) / followers) * 100 if followers > 0
            er = round(((likes + comments) / followers) * 100, 2) if followers > 0 else 0.0
            
            post_data = {
                "aggregator_account_id": str(aggregator_account_id),
                "user_id": user_id,
                "ig_post_id": p["id"],
                "caption": p.get("caption"),
                "media_url": p.get("media_url"),
                "media_type": p.get("media_type"),
                "likes": likes,
                "comments": comments,
                "engagement_rate": er,
                "hashtags": self._extract_hashtags(p.get("caption", "")),
                "posted_at": p.get("timestamp"),
            }
            try:
                # Always include user_id in the upsert data for security
                post_data["user_id"] = user_id
                supabase.table("aggregated_posts").upsert(
                    post_data, 
                    on_conflict="aggregator_account_id, ig_post_id"
                ).execute()
                saved_count += 1
            except Exception as e:
                logger.error("Error saving post %s for user %s: %s", p['id'], user_id, e)

        # 4. Update status and metrics
        update_data = {
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
            "sync_error": sync_error,
            "followers_count": followers,
            "following_count": following
        }
        try:
            supabase.table("aggregator_accounts").update(update_data).eq("id", str(aggregator_account_id)).execute()
        except Exception as e:
            logger.error("Failed to update status and metrics for account %s (likely missing schema columns): %s", aggregator_account_id, e)
            try:
                # Absolute minimal fallback to just register that a sync happened
                fallback_data = {
                    "last_synced_at": datetime.now(timezone.utc).isoformat()
                }
                supabase.table("aggregator_accounts").update(fallback_data).eq("id", str(aggregator_account_id)).execute()
            except Exception as inner_e:
                logger.error("Fallback status update failed for %s: %s", aggregator_account_id, inner_e)
        
        return saved_count

    async def generate_ai_insights(self, account_ids: List[UUID], user_id: UUID) -> Dict[str, Any]:
        """Use Claude to analyze posts across multiple accounts and generate trends/ideas."""
        supabase = self._get_supabase()
        user_id_str = str(user_id)
        
        # 1. Verify ownership (Critical Hardening)
        ownership_check = supabase.table("aggregator_accounts") \
            .select("id") \
            .in_("id", [str(aid) for aid in account_ids]) \
            .eq("user_id", user_id_str) \
            .execute()
        
        owned_ids = {row["id"] for row in (ownership_check.data or [])}
        valid_ids = [aid for aid in account_ids if str(aid) in owned_ids]
        
        if not valid_ids:
            logger.warning("Access denied to aggregator accounts for user %s", user_id_str)
            return {"error": "No valid accounts found or access denied"}

        # B1.4: Redis Caching for AI Insights (4-hour TTL)
        r = get_redis()
        cache_key = None
        if r:
            ids_str = ",".join(sorted([str(aid) for aid in valid_ids]))
            ids_hash = hashlib.md5(ids_str.encode()).hexdigest()
            cache_key = f"aggregator:insights:{user_id_str}:{ids_hash}"
            cached = r.get(cache_key)
            if cached:
                logger.info("B1.4: Returning cached AI insights for %s", user_id_str)
                return json.loads(cached)

        # 2. Fetch recent posts from these accounts in a single query (Fix N+1)
        resp = supabase.table("aggregated_posts")\
            .select("caption, likes, comments, hashtags, posted_at, media_type, engagement_rate")\
            .in_("aggregator_account_id", [str(aid) for aid in valid_ids])\
            .eq("user_id", user_id_str) \
            .order("posted_at", desc=True)\
            .limit(30)\
            .execute()
        post_data = resp.data or []

        if not post_data:
            return {"error": "No post data found for analysis"}

        # 2.5 Fetch account metrics for context
        acc_metrics = supabase.table("aggregator_accounts") \
            .select("instagram_username, followers_count") \
            .in_("id", [str(aid) for aid in valid_ids]) \
            .execute()
        acc_map = {row["instagram_username"]: row["followers_count"] for row in (acc_metrics.data or [])}

        # 3. Prepare prompt for Claude (Enhanced with ER and Media Type)
        def _get_hour(ts):
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return dt.strftime("%A at %H:00")
            except:
                return "Unknown"

        post_summary = "\n".join([
            f"Post: {sanitize_input(p.get('caption', ''))[:80]}... | Type: {p.get('media_type', 'IMAGE')} | ER: {p.get('engagement_rate', 0)}% | Time: {_get_hour(p.get('posted_at', ''))}"
            for p in post_data
        ])

        system = """You are an elite Instagram growth strategist for Indian small businesses.
Analyze the provided post data including engagement rates (ER) and media types.
ER is the most important metric. Identify what resonates with the Indian audience.
Respond ONLY with valid JSON."""

        prompt = f"""
Analyze these Instagram posts from competition and owned accounts:
{post_summary}

Context:
Total accounts analyzed: {len(valid_ids)}
Follower counts: {acc_map}

Generate:
1. post_ideas: 5 creative post ideas (Hindi + English mix).
2. trend_summaries: 3 key trends observed.
3. best_posting_times: 3 recommended windows based on patterns.
4. caption_suggestions: 3 punchy hooks for Indian buyers.
5. content_sentiment: General mood (e.g., 'Aspirational & Premium' or 'Value-driven & Urgent').
6. top_format: The media_type with highest impact.
7. weak_spots: 2 things these accounts are missing.

Return ONLY this JSON structure (Raw JSON string):
{{
  "post_ideas": ["..."],
  "trend_summaries": ["..."],
  "best_posting_times": ["..."],
  "caption_suggestions": ["..."],
  "content_sentiment": "...",
  "top_format": "...",
  "weak_spots": ["..."]
}}"""

        client = _get_client()
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
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
            "user_id": user_id_str,
            "action": "aggregator_ai_analysis",
            "api_service": "anthropic_claude",
            "month_year": datetime.now(timezone.utc).strftime("%Y-%m"),
            "cost_paise": cost_paise,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out
        }
        supabase.table("usage_logs").insert(usage_log).execute()

        raw = response.content[0].text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            parsed_res = json.loads(raw)
            # B1.3: Inject defaults for required Pydantic keys to prevent 422 errors
            parsed_res.setdefault("post_ideas", [])
            parsed_res.setdefault("trend_summaries", [])
            parsed_res.setdefault("best_posting_times", [])
            parsed_res.setdefault("caption_suggestions", [])
            parsed_res.setdefault("weak_spots", [])
            
            if r and cache_key:
                r.setex(cache_key, 14400, json.dumps(parsed_res))
            return parsed_res
        except json.JSONDecodeError as e:
            logger.error("AI Insights JSON parse error: %s", e)
            return {"error": "Deep analysis failed. Please try again."}

    async def _fetch_owned_posts(self, username: str, token: str) -> Dict[str, Any]:
        """Fetch posts and metrics for an owned account."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch user metrics
            me_resp = await client.get(
                f"{GRAPH_BASE}/me",
                params={"fields": "followers_count,follows_count", "access_token": token}
            )
            me_data = me_resp.json() if me_resp.status_code == 200 else {}
            
            # Fetch media
            resp = await client.get(
                f"{GRAPH_BASE}/me/media",
                params={
                    "fields": "id,caption,media_type,media_url,permalink,timestamp,username,like_count,comments_count",
                    "access_token": token,
                    "limit": 25
                }
            )
            resp.raise_for_status()
            return {
                "posts": resp.json().get("data", []),
                "followers": me_data.get("followers_count", 0),
                "following": me_data.get("follows_count", 0)
            }

    async def _fetch_competitor_posts(self, ig_business_id: str, competitor_username: str, token: str) -> Dict[str, Any]:
        """Fetch posts and metrics for a competitor using Business Discovery API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            query = f"business_discovery.username({competitor_username}){{followers_count,follows_count,media{{id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count}}}}"
            resp = await client.get(
                f"{GRAPH_BASE}/{ig_business_id}",
                params={
                    "fields": query,
                    "access_token": token
                }
            )
            resp.raise_for_status()
            data = resp.json().get("business_discovery", {})
            return {
                "posts": data.get("media", {}).get("data", []),
                "followers": data.get("followers_count", 0),
                "following": data.get("follows_count", 0)
            }

    async def save_to_my_posts(self, aggregated_post_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """Copy an aggregated post to the user's main posts table."""
        supabase = self._get_supabase()
        user_id_str = str(user_id)
        
        # 1. Fetch aggregated post
        resp = supabase.table("aggregated_posts") \
            .select("*, aggregator_accounts(instagram_username)") \
            .eq("id", str(aggregated_post_id)) \
            .eq("user_id", user_id_str) \
            .single() \
            .execute()
        
        if not resp.data:
            return {"error": "Aggregated post not found"}
            
        post = resp.data
        
        # 2. Create main post entry
        new_post_id = str(uuid.uuid4())
        main_post = {
            "id": new_post_id,
            "user_id": user_id_str,
            "product_name": f"Inspiration: {post['aggregator_accounts']['instagram_username']}",
            "original_photo_url": post["media_url"],
            "caption_english": post["caption"],
            "caption_hindi": post["caption"], # Placeholder
            "hashtags": post["hashtags"],
            "status": "ready",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        res = supabase.table("posts").insert(main_post).execute()
        return res.data[0]

    async def get_trending_hashtags(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Admin only: Get top trending hashtags across all aggregated content."""
        supabase = self._get_supabase()
        # Note: In a production scale, this would be a materialized view or aggregated in Redis/Elasticsearch.
        # For our MVP scale, we pull recent posts and count in-memory or via RPC.
        # Let's use an RPC for performance if one exists, otherwise manual aggregation.
        try:
            rpc_res = supabase.rpc("get_trending_hashtags", {"hashtag_limit": limit}).execute()
            return rpc_res.data
        except Exception as e:
            logger.warning("RPC fallback (trending hashtags): %s", e)
            # Fallback to manual aggregation (less efficient)
            resp = supabase.table("aggregated_posts").select("hashtags").limit(1000).execute()
            all_tags = []
            for row in (resp.data or []):
                if row.get("hashtags"):
                    all_tags.extend(row["hashtags"])
            
            from collections import Counter
            counts = Counter(all_tags).most_common(limit)
            return [{"tag": tag, "count": count} for tag, count in counts]

    def _extract_hashtags(self, caption: str) -> List[str]:
        if not caption:
            return []
        return re.findall(r"#[\w\u0900-\u097F\u0C00-\u0C7F\u0B80-\u0BFF\u0C80-\u0CFF]+", caption)

    async def get_content_format_stats(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get engagement stats grouped by media type."""
        user_id_str = str(user_id)
        r = get_redis()
        cache_key = f"aggregator:analytics:formats:{user_id_str}"
        if r:
            cached = r.get(cache_key)
            if cached: return json.loads(cached)

        supabase = self._get_supabase()
        # RPC approach for efficiency
        try:
            res = supabase.rpc("aggregator_content_format_stats", {"p_user_id": str(user_id)}).execute()
            return res.data or []
        except Exception as e:
            logger.warning("RPC fallback (content format): %s", e)
            # Python fallback (B2.2: adding likes/comments to fallback)
            resp = supabase.table("aggregated_posts") \
                .select("media_type, engagement_rate, likes, comments") \
                .eq("user_id", user_id_str) \
                .execute()
            
            data = resp.data or []
            formats = {}
            for row in data:
                mt = row["media_type"] or "UNKNOWN"
                if mt not in formats:
                    formats[mt] = {"media_type": mt, "total_er": 0, "total_likes": 0, "total_comments": 0, "post_count": 0}
                formats[mt]["total_er"] += row["engagement_rate"]
                formats[mt]["total_likes"] += row["likes"]
                formats[mt]["total_comments"] += row["comments"]
                formats[mt]["post_count"] += 1
            
            res = [
                {
                    "media_type": f["media_type"],
                    "avg_engagement": round(f["total_er"] / f["post_count"], 2),
                    "avg_likes": round(f["total_likes"] / f["post_count"], 1),
                    "avg_comments": round(f["total_comments"] / f["post_count"], 1),
                    "post_count": f["post_count"]
                }
                for f in formats.values()
            ]
            if r: r.setex(cache_key, 3600, json.dumps(res))
            return res

    async def get_posting_frequency(self, user_id: UUID) -> Dict[str, Any]:
        """Get posting frequency by day of week (Owned vs Competitor)."""
        user_id_str = str(user_id)
        r = get_redis()
        cache_key = f"aggregator:analytics:frequency:{user_id_str}"
        if r:
            cached = r.get(cache_key)
            if cached: return json.loads(cached)

        supabase = self._get_supabase()
        resp = supabase.table("aggregated_posts") \
            .select("posted_at, aggregator_accounts(account_type)") \
            .eq("user_id", str(user_id)) \
            .execute()
        
        data = resp.data or []
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        heatmap = {d: {"day": d, "owned_count": 0, "competitor_count": 0} for d in days}
        
        comp_acc_count = supabase.table("aggregator_accounts") \
            .select("id", count="exact") \
            .eq("user_id", user_id_str) \
            .eq("account_type", "competitor") \
            .execute().count or 0
        
        no_competitors = comp_acc_count == 0

        for row in data:
            try:
                dt = datetime.fromisoformat(row["posted_at"].replace("Z", "+00:00"))
                day_name = dt.strftime("%A")
                is_owned = row["aggregator_accounts"]["account_type"] == "owned"
                if day_name in heatmap:
                    if is_owned:
                        heatmap[day_name]["owned_count"] += 1
                    else:
                        heatmap[day_name]["competitor_count"] += 1
            except:
                continue
        
        # Calculate weekly averages based on actual date range
        total_owned = sum(h["owned_count"] for h in heatmap.values())
        total_comp = sum(h["competitor_count"] for h in heatmap.values())

        weeks = 4 # Default
        if data:
            try:
                dates = [datetime.fromisoformat(p["posted_at"].replace("Z", "+00:00")) for p in data]
                min_date = min(dates)
                max_date = max(dates)
                days_diff = (max_date - min_date).days
                weeks = max(1, days_diff / 7)
            except:
                pass

        final_res = {
            "heatmap": [
                {
                    **h,
                    "competitor_avg_count": 0 if no_competitors else round(h["competitor_count"] / comp_acc_count, 1)
                } for h in heatmap.values()
            ],
            "avg_per_week_owned": round(total_owned / weeks, 1),
            "avg_per_week_competitor": 0 if no_competitors else round((total_comp / comp_acc_count) / weeks, 1),
            "no_competitors": no_competitors
        }
        if r: r.setex(cache_key, 3600, json.dumps(final_res))
        return final_res

    async def get_comparison_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get high-level comparison stats for all tracked accounts."""
        user_id_str = str(user_id)
        r = get_redis()
        cache_key = f"aggregator:analytics:comparison:{user_id_str}"
        if r:
            cached = r.get(cache_key)
            if cached: return json.loads(cached)

        supabase = self._get_supabase()
        accs = supabase.table("aggregator_accounts") \
            .select("id, instagram_username, account_type, followers_count") \
            .eq("user_id", str(user_id)) \
            .execute().data or []
        
        # Fetch posts for all accounts in one batch query to avoid N+1
        acc_ids = [str(acc["id"]) for acc in accs]
        all_posts_resp = supabase.table("aggregated_posts") \
            .select("aggregator_account_id, engagement_rate, hashtags, posted_at") \
            .in_("aggregator_account_id", acc_ids) \
            .order("posted_at", desc=True) \
            .execute()
        
        from collections import defaultdict, Counter
        posts_by_acc = defaultdict(list)
        for p in (all_posts_resp.data or []):
            if len(posts_by_acc[p["aggregator_account_id"]]) < 50:
                posts_by_acc[p["aggregator_account_id"]].append(p)

        results = []
        for acc in accs:
            posts = posts_by_acc[str(acc["id"])]
            avg_er = round(sum(p["engagement_rate"] for p in posts) / len(posts), 2) if posts else 0
            
            # Calculate actual weekly volume
            weeks = 4
            if posts:
                try:
                    dates = [datetime.fromisoformat(p["posted_at"].replace("Z", "+00:00")) for p in posts]
                    days_diff = (max(dates) - min(dates)).days
                    weeks = max(1, days_diff / 7)
                except: pass

            all_tags = []
            for p in posts:
                if p.get("hashtags"): all_tags.extend(p["hashtags"])
            top_tags = [tag for tag, _ in Counter(all_tags).most_common(5)]
            
            results.append({
                "username": acc["instagram_username"],
                "account_type": acc["account_type"],
                "followers": acc["followers_count"],
                "avg_engagement": avg_er,
                "posts_per_week": round(len(posts) / weeks, 1),
                "top_hashtags": top_tags
            })
        
        final_res = {
            "owned": next((r for r in results if r["account_type"] == "owned"), None),
            "competitors": [r for r in results if r["account_type"] == "competitor"]
        }
        if r: r.setex(cache_key, 3600, json.dumps(final_res))
        return final_res

    async def get_user_hashtag_performance(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get hashtag performance for a specific user's tracked network."""
        user_id_str = str(user_id)
        r = get_redis()
        cache_key = f"aggregator:analytics:hashtags:{user_id_str}"
        if r:
            cached = r.get(cache_key)
            if cached: return json.loads(cached)

        supabase = self._get_supabase()
        resp = supabase.table("aggregated_posts") \
            .select("hashtags, engagement_rate") \
            .eq("user_id", str(user_id)) \
            .execute().data or []
        
        tag_stats = {}
        for row in resp:
            for tag in row.get("hashtags", []):
                if tag not in tag_stats:
                    tag_stats[tag] = {"tag": tag, "total_er": 0, "count": 0}
                tag_stats[tag]["total_er"] += row["engagement_rate"]
                tag_stats[tag]["count"] += 1
        
        sorted_tags = sorted(
            tag_stats.values(), 
            key=lambda x: (x["total_er"] / x["count"]), 
            reverse=True
        )[:20]
        
        final_res = [
            {
                "tag": s["tag"],
                "avg_engagement": round(s["total_er"] / s["count"], 2),
                "count": s["count"]
            } for s in sorted_tags
        ]
        if r: r.setex(cache_key, 3600, json.dumps(final_res))
        return final_res

aggregator_service = AggregatorService()
