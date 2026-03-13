# backend/app/workers/aggregator_worker.py
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from app.workers.celery_app import celery_app
from app.services.aggregator_service import aggregator_service
from app.services.telegram_service import send_message
from app.db.supabase import get_supabase

logger = logging.getLogger(__name__)

@celery_app.task(
    name="sync_aggregator_posts",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5,
    retry_jitter=True
)
def sync_aggregator_posts(aggregator_account_id: str):
    """Celery task to sync posts for a specific account with automatic retries."""
    logger.info("Syncing aggregator posts for account %s", aggregator_account_id)
    
    # 1. Run sync
    try:
        new_posts_count = asyncio.run(aggregator_service.fetch_and_save_posts(aggregator_account_id))
    except Exception as e:
        logger.error("Sync failed for %s: %s", aggregator_account_id, e)
        raise

    # 2. Check for alerts
    if new_posts_count > 0:
        try:
            asyncio.run(_maybe_alert_user(aggregator_account_id))
        except Exception as e:
            logger.error("Alert check failed for %s: %s", aggregator_account_id, e)
    
    return new_posts_count

async def _maybe_alert_user(account_id: str):
    """Check for high-engagement posts and send Telegram alert."""
    supabase = get_supabase()
    
    # 1. Get account and user info
    resp = supabase.table("aggregator_accounts") \
        .select("*, users(telegram_id, language)") \
        .eq("id", account_id) \
        .single() \
        .execute()
    
    if not resp.data: return
    acc = resp.data
    user = acc.get("users")
    
    if not acc.get("alert_enabled") or not user or not user.get("telegram_id"):
        return

    # 2. Find high engagement posts from this account in the last 15 minutes (to avoid notification spam)
    # Target competitor posts where engagement_rate > threshold
    if acc["account_type"] != "competitor":
        return

    threshold = acc.get("alert_threshold_er", 3.0)
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    
    posts_resp = supabase.table("aggregated_posts") \
        .select("ig_post_id, caption, engagement_rate, media_url") \
        .eq("aggregator_account_id", account_id) \
        .gt("engagement_rate", threshold) \
        .gt("created_at", cutoff) \
        .order("engagement_rate", desc=True) \
        .limit(1) \
        .execute()
    
    if not posts_resp.data:
        return
    
    post = posts_resp.data[0]
    
    # Minimalist notification text
    lang = user.get("language", "en")
    username = acc["instagram_username"]
    er = post["engagement_rate"]
    
    if lang == "hi":
        msg = f"🚀 *धमाकेदार पोस्ट अलर्ट!*\n\nकंपटीटर *@{username}* की एक पोस्ट पर {er}% एंगेजमेंट मिला है!\n\nये रहा कैप्शन:\n_{post['caption'][:100]}..._\n\nजाकर देखें और सीखें!"
    else:
        msg = f"🚀 *Trending Competitor Alert!*\n\n*@{username}* just posted a high-impact post with {er}% engagement!\n\nCaption excerpt:\n_{post['caption'][:100]}..._\n\nCheck it out for inspiration!"

    try:
        await send_message(user["telegram_id"], msg)
        logger.info("Sent alert for account %s to user %s", username, user["telegram_id"])
    except Exception as e:
        logger.error("Failed to send telegram alert: %s", str(e))

@celery_app.task(name="sync_all_aggregator_accounts")
def sync_all_aggregator_accounts():
    """Celery task to sync all active aggregator accounts with plan filtering and staggering."""
    logger.info("Starting batch sync for all active aggregator accounts")
    supabase = get_supabase()
    
    # High: Filter users separately for reliability (SDK join-filter can be unstable)
    users_resp = supabase.table("users") \
        .select("id") \
        .eq("plan", "aggregator") \
        .eq("is_active", True) \
        .execute()
    
    user_ids = [u["id"] for u in (users_resp.data or [])]
    if not user_ids:
        logger.info("No active aggregator users found for sync")
        return "No active aggregator users"

    # Now get accounts for these specific users
    resp = supabase.table("aggregator_accounts") \
        .select("id") \
        .in_("user_id", user_ids) \
        .execute()
    
    accounts = resp.data or []
    for i, acc in enumerate(accounts):
        # Medium: Stagger by 2 seconds to avoid hitting Instagram API rate limits simultaneously
        sync_aggregator_posts.apply_async(
            args=[acc["id"]], 
            countdown=i * 2
        )
    
    return f"Triggered staggered sync for {len(accounts)} accounts"
