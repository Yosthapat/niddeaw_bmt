"""Shrinks the avatars already in the bucket to the size the site draws.

New uploads are resized by the API itself (app/services/image_service.py).
This is the one-off for the photos uploaded before that, which are stored
at up to 1600px and re-sent to every visitor of the members, ranking and
live pages.

It reads each player's current avatar, re-encodes it through exactly the
same function the API uses, stores it under its content-addressed name
with the year-long cache, points the player at it and deletes the old
file. Running it twice is harmless: the second run finds every avatar
already at its final name and does nothing.

    # see what it would do, change nothing
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
        python tools/shrink_avatars.py

    # do it
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
        python tools/shrink_avatars.py --apply

Needs the backend's own environment (backend/.venv) for Pillow and the
supabase client.
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backend"))

from app.services.image_service import (  # noqa: E402
    avatar_jpeg,
    avatar_path,
    storage_path_from_url,
)

BUCKET = "avatars"
CACHE_SECONDS = "31536000"


def human(num_bytes: int) -> str:
    return f"{num_bytes / 1024:.0f} KB" if num_bytes < 1024 * 1024 else f"{num_bytes / 1048576:.1f} MB"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually write; without it nothing is uploaded, updated or deleted",
    )
    args = parser.parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

    from supabase import create_client

    supabase = create_client(url, key)
    bucket = supabase.storage.from_(BUCKET)

    players = supabase.table("players").select("id,nickname,avatar_url").execute().data or []
    with_photo = [p for p in players if p.get("avatar_url")]
    print(f"{len(with_photo)} of {len(players)} members have a photo\n")

    before_total = after_total = 0
    changed = skipped = failed = 0

    for player in with_photo:
        name = player["nickname"]
        old_url = player["avatar_url"]
        try:
            with urllib.request.urlopen(old_url, timeout=30) as response:  # noqa: S310
                original = response.read()
        except Exception as exc:  # noqa: BLE001 - one bad URL must not stop the rest
            print(f"  !  {name:12} could not be downloaded: {exc}")
            failed += 1
            continue

        try:
            shrunk = avatar_jpeg(original)
        except ValueError as exc:
            print(f"  !  {name:12} is not readable as an image: {exc}")
            failed += 1
            continue

        new_path = avatar_path(str(player["id"]), shrunk)
        old_path = storage_path_from_url(old_url, BUCKET)

        before_total += len(original)
        after_total += len(shrunk)

        if old_path == new_path:
            print(f"  =  {name:12} already {human(len(original))}, nothing to do")
            skipped += 1
            continue

        saved = len(original) - len(shrunk)
        print(
            f"  {'->' if args.apply else '..'} {name:12} "
            f"{human(len(original))} -> {human(len(shrunk))}  (saves {human(saved)})"
        )
        changed += 1
        if not args.apply:
            continue

        bucket.upload(
            new_path,
            shrunk,
            {"content-type": "image/jpeg", "cache-control": CACHE_SECONDS, "upsert": "true"},
        )
        public_url = bucket.get_public_url(new_path)
        supabase.table("players").update({"avatar_url": public_url}).eq(
            "id", player["id"]
        ).execute()
        if old_path:
            try:
                bucket.remove([old_path])
            except Exception as exc:  # noqa: BLE001 - the new photo is already live
                print(f"     (old file {old_path} left behind: {exc})")

    print(
        f"\n{changed} to shrink, {skipped} already done, {failed} failed\n"
        f"every page view of the members list: {human(before_total)} -> {human(after_total)}"
    )
    if not args.apply and changed:
        print("\nnothing was written — re-run with --apply")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
