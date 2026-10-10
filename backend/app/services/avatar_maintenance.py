"""Re-encoding the avatars that were stored before the API resized them.

One implementation, two front doors: the admin screen's button and
tools/shrink_avatars.py. Both land here, so what the club sees in the
browser and what the script prints can never drift apart.

Photos are read through the storage client rather than fetched from their
public URL. Nothing here then makes an outbound request to an address that
came out of the database, and the bucket is the only place it can read.
"""

from __future__ import annotations

from typing import Any

from supabase import Client

from app.db_utils import rows
from app.models.maintenance import AvatarShrinkReport, AvatarShrinkRow
from app.services.image_service import avatar_jpeg, avatar_path, storage_path_from_url

AVATAR_BUCKET = "avatars"
AVATAR_CACHE_SECONDS = "31536000"


def _row(
    player: dict[str, Any],
    *,
    before: int = 0,
    after: int = 0,
    status: str,
    detail: str | None = None,
) -> AvatarShrinkRow:
    return AvatarShrinkRow(
        player_id=str(player.get("id", "")),
        nickname=str(player.get("nickname", "")),
        before_bytes=before,
        after_bytes=after,
        status=status,  # type: ignore[arg-type]
        detail=detail,
    )


def shrink_all(supabase: Client, *, apply: bool) -> AvatarShrinkReport:
    """Shrink every stored avatar that is not already at its final size.

    With `apply` false nothing is uploaded, updated or deleted and the
    report is a forecast. Running it again after a real run is a no-op:
    every photo is then stored under the name its own bytes hash to, which
    is what "already" means below.

    One member's photo failing is reported in their row and the rest of the
    club still gets done.
    """
    bucket = supabase.storage.from_(AVATAR_BUCKET)
    players = rows(supabase.table("players").select("id,nickname,avatar_url").execute())

    results: list[AvatarShrinkRow] = []
    for player in players:
        old_url = player.get("avatar_url")
        if not old_url:
            continue

        old_path = storage_path_from_url(str(old_url), AVATAR_BUCKET)
        if old_path is None:
            results.append(
                _row(player, status="failed", detail="photo is not in this project's bucket")
            )
            continue

        try:
            original = bucket.download(old_path)
        except Exception as exc:  # noqa: BLE001 - one missing object must not stop the rest
            results.append(_row(player, status="failed", detail=f"could not be read: {exc}"))
            continue

        try:
            shrunk = avatar_jpeg(original)
        except ValueError as exc:
            results.append(_row(player, status="failed", detail=str(exc)))
            continue

        new_path = avatar_path(str(player["id"]), shrunk)
        if new_path == old_path:
            results.append(
                _row(player, before=len(original), after=len(original), status="already")
            )
            continue

        if apply:
            try:
                bucket.upload(
                    new_path,
                    shrunk,
                    {
                        "content-type": "image/jpeg",
                        "cache-control": AVATAR_CACHE_SECONDS,
                        "upsert": "true",
                    },
                )
                public_url = bucket.get_public_url(new_path)
                supabase.table("players").update({"avatar_url": public_url}).eq(
                    "id", player["id"]
                ).execute()
            except Exception as exc:  # noqa: BLE001 - reported per member, not fatal
                results.append(_row(player, status="failed", detail=f"could not be saved: {exc}"))
                continue

            # Only once the member points at the new file. A failure here
            # leaves a few unreferenced KB behind, which is cheaper than
            # deleting a photo that is still in use.
            try:
                bucket.remove([old_path])
            except Exception:  # noqa: BLE001
                pass

        results.append(
            _row(player, before=len(original), after=len(shrunk), status="shrunk")
        )

    return AvatarShrinkReport(
        applied=apply,
        rows=results,
        before_total=sum(r.before_bytes for r in results),
        after_total=sum(r.after_bytes for r in results),
        shrunk=sum(1 for r in results if r.status == "shrunk"),
        already=sum(1 for r in results if r.status == "already"),
        failed=sum(1 for r in results if r.status == "failed"),
    )
