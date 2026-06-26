import os
from functools import lru_cache
from supabase import create_client, Client


@lru_cache()
def get_supabase() -> Client | None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


async def test_connection() -> bool:
    client = get_supabase()
    if not client:
        return False
    try:
        client.table("_dummy").select("*").limit(1).execute()
        return True
    except Exception:
        return False
