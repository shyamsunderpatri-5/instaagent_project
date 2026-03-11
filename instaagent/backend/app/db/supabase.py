# backend/app/db/supabase.py
from supabase import create_client, Client
from app.config import settings
from functools import lru_cache


@lru_cache()
def get_supabase() -> Client:
    """Get cached Supabase client using service key (bypasses RLS for backend)."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


@lru_cache()
def get_supabase_anon() -> Client:
    """Get Supabase client using anon key (respects RLS — use for user-facing operations)."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
