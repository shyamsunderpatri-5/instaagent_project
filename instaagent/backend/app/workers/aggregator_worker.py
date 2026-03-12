# backend/app/workers/aggregator_worker.py
import asyncio
import logging
from app.workers.celery_app import celery_app
from app.services.aggregator_service import aggregator_service
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
    logger.info(f"🔄 Syncing aggregator posts for account {aggregator_account_id}")
    
    # Run async logic in sync context
    return asyncio.run(aggregator_service.fetch_and_save_posts(aggregator_account_id))

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
