"""
database.py — Supabase client factory.
Provides both the anon client (for regular queries) and the service-role
client (for admin operations like storage uploads).
"""

from functools import lru_cache
from supabase import create_client, Client
from loguru import logger
from app.config import get_settings


@lru_cache()
def get_supabase() -> Client:
    """Return a cached Supabase anon client."""
    settings = get_settings()
    logger.debug("Initialising Supabase anon client → {}", settings.supabase_url)
    return create_client(settings.supabase_url, settings.supabase_key)


@lru_cache()
def get_supabase_admin() -> Client:
    """Return a cached Supabase service-role client (bypasses RLS)."""
    settings = get_settings()
    logger.debug("Initialising Supabase service-role client")
    return create_client(
        settings.supabase_url, settings.supabase_service_role_key
    )
