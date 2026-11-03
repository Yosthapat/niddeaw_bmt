"""Photos for LINE sign-ups.

An application carries its photo as an avatar the backend already stored:
the member's own (uploaded from the /line form) or their LINE picture,
fetched here. Either way it is the same avatar-sized JPEG an admin upload
makes, in the same bucket, so accepting the application just points the
new player at it.
"""

import contextlib
from urllib.parse import urlparse

import httpx
from supabase import Client

from app.services.image_service import avatar_jpeg, avatar_path, storage_path_from_url

AVATAR_BUCKET = "avatars"
AVATAR_CACHE_SECONDS = "31536000"
MAX_PHOTO_BYTES = 2 * 1024 * 1024


def is_line_picture(url: str | None) -> bool:
    """Only LINE's own image CDN: the URL came from LINE's verified token,
    but the server is about to fetch it, so it fetches nothing else."""
    if not url:
        return False
    parts = urlparse(url)
    host = parts.hostname or ""
    return parts.scheme == "https" and (host == "line-scdn.net" or host.endswith(".line-scdn.net"))


def fetch_line_picture(url: str) -> bytes | None:
    """Their LINE picture, or None if it can't be had (no picture, LINE
    slow, not an image). A sign-up never fails over its photo."""
    if not is_line_picture(url):
        return None
    try:
        with httpx.Client(timeout=8, follow_redirects=False) as http:
            response = http.get(url)
    except httpx.HTTPError:
        return None
    if response.status_code != 200 or len(response.content) > MAX_PHOTO_BYTES:
        return None
    return response.content


def store_photo(supabase: Client, owner: str, data: bytes) -> str:
    """Store an applicant's photo as an avatar; returns its public URL.
    Raises ValueError for something that isn't an image."""
    jpeg = avatar_jpeg(data)
    path = avatar_path(f"join-{owner}", jpeg)
    bucket = supabase.storage.from_(AVATAR_BUCKET)
    bucket.upload(
        path,
        jpeg,
        {"content-type": "image/jpeg", "cache-control": AVATAR_CACHE_SECONDS, "upsert": "true"},
    )
    return str(bucket.get_public_url(path))


def remove_photo(supabase: Client, url: str | None) -> None:
    """Best effort: a photo nobody will use any more."""
    if not url:
        return
    path = storage_path_from_url(url, AVATAR_BUCKET)
    if not path:
        return
    # A few KB left behind, never a failed request.
    with contextlib.suppress(Exception):
        supabase.storage.from_(AVATAR_BUCKET).remove([path])
