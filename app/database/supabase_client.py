import logging
from functools import lru_cache

from supabase import Client, create_client

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_supabase_client() -> Client:
    """Create and cache a centralized Supabase client."""

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError(
            "Supabase credentials are not configured. Set SUPABASE_URL and "
            "SUPABASE_KEY in the environment or .env file."
        )

    logger.info("Initializing Supabase client")
    return create_client(settings.supabase_url, settings.supabase_key)
