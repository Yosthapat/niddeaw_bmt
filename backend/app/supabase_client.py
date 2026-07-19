from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Backend-only Supabase client using the service-role key.

    Never import this module from anything that ships to the browser —
    the frontend must only ever talk to this backend's HTTP API.
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
