# backend/app/middleware/usage.py
import time
import logging
from fastapi import Request
from app.db.supabase import get_supabase
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

async def log_aggregator_usage(user_id: str, action: str, api_service: str = "aggregator", cost: int = 0):
    """
    Log aggregator usage to the usage_logs table.
    This helps in tracking monthly quotas and costs for enterprise accounts.
    """
    supabase = get_supabase()
    month_year = datetime.now(timezone.utc).strftime("%Y-%m")
    
    log_data = {
        "user_id": user_id,
        "action": action,
        "api_service": api_service,
        "cost_paise": cost,
        "month_year": month_year,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        supabase.table("usage_logs").insert(log_data).execute()
    except Exception as e:
        logger.error("Failed to log aggregator usage: %s", str(e))

class AggregatorUsageMiddleware:
    """
    Optional middleware to intercept specifically labeled requests 
    for aggregator usage tracking. 
    (Placeholder for future granular per-request tracking if needed)
    """
    pass
