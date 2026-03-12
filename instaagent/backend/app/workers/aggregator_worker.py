# backend/app/workers/aggregator_worker.py
import asyncio
import logging
from celery_app import celery_app
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
    """Celery task to sync all active aggregator accounts."""
    logger.info("Syncing all active aggregator accounts")
    supabase = get_supabase()
    
    # Fetch all aggregator accounts
    resp = supabase.table("aggregator_accounts").select("id").execute()
    if resp.data:
        for acc in resp.data:
            # Trigger individual task for each account to allow parallel processing
            sync_aggregator_posts.delay(acc["id"])
    
    return f"Triggered sync for {len(resp.data) if resp.data else 0} accounts"
