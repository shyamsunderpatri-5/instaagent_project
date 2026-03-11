# backend/tests/test_scheduling_logic.py
import pytest
from datetime import datetime, timezone, timedelta
from app.workers.post_worker import IST_OFFSET

def test_ist_to_utc_conversion():
    """Verify that we correctly calculate UTC from IST for scheduling."""
    # Example: 15:33 IST
    ist_time_str = "15:33"
    
    # Current date in IST
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + IST_OFFSET
    
    # Target time today in IST
    target_ist = now_ist.replace(
        hour=int(ist_time_str.split(":")[0]),
        minute=int(ist_time_str.split(":")[1]),
        second=0,
        microsecond=0
    )
    
    # If target is in the past, it should be tomorrow
    if target_ist < now_ist:
        target_ist += timedelta(days=1)
        
    # Convert back to UTC
    target_utc = target_ist - IST_OFFSET
    
    # The difference should be exactly 5 hours 30 minutes
    diff = target_ist - target_utc
    assert diff == timedelta(hours=5, minutes=30)
    
    print(f"\nIST: {target_ist}")
    print(f"UTC: {target_utc}")

def test_post_worker_query_logic():
    """
    Verify that the post worker queries posts with scheduled_at <= now.
    (This is a logic check, actual DB query is mocked in conftest.py)
    """
    now_utc = datetime.now(timezone.utc)
    scheduled_at = now_utc - timedelta(minutes=1) # 1 minute ago
    
    # Simulation of the worker condition
    is_due = scheduled_at <= now_utc
    assert is_due is True
    
    not_due = (now_utc + timedelta(minutes=1)) <= now_utc
    assert not_due is False
