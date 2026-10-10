"""Runs the real backend against an in-memory database, seeded with a club
night in progress, so the UI can be driven and looked at.

    python tools/uxlab/lab.py          # serves http://127.0.0.1:5399

Nothing here ships to production: it is a harness for tools/uxlab/shoot.py
and for driving the app by hand. See tools/uxlab/README.md.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend"))

PORT = int(os.environ.get("UXLAB_PORT", "5399"))
STATIC_PORT = int(os.environ.get("UXLAB_STATIC_PORT", "5324"))
PASSWORD = "uxlab"

os.environ.setdefault("SUPABASE_URL", "http://supabase.invalid")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "uxlab-not-a-real-key")
os.environ.setdefault("JWT_SECRET", "uxlab-not-a-real-secret")
os.environ.setdefault(
    "CORS_ORIGINS",
    f"http://localhost:{STATIC_PORT},http://127.0.0.1:{STATIC_PORT},http://localhost:5173",
)

from minisupabase import MiniSupabase  # noqa: E402

import app.middleware.activity_log as activity_log_mw  # noqa: E402
import app.supabase_client as supabase_client  # noqa: E402
from app.deps import get_supabase  # noqa: E402
from app.main import app  # noqa: E402
from app.security import hash_password  # noqa: E402

ADMIN_ID = str(uuid.uuid4())
NAMES = ["บอล", "เจมส์", "ฟ้า", "ต้น", "อุ้ม", "มิว", "แทน", "กิ๊ก"]
TIERS = ["beer", "beer", "soju", "soju", "highball", "milk", "beer", "soju"]


def _seed_oversized_avatars(db: "MiniSupabase", players: list) -> None:
    """Two 1600px photos in the bucket, the way the club's own look today."""
    import io

    from PIL import Image

    for n, player in enumerate(players):
        image = Image.new("RGB", (1600, 1600), (180 - n * 40, 40 + n * 60, 120))
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=92)
        path = f"{player['id']}.jpg"
        db.storage.from_("avatars").upload(path, buf.getvalue())
        player["avatar_url"] = db.storage.from_("avatars").get_public_url(path)


def _iso(minutes_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def seed() -> MiniSupabase:
    """A night mid-flight: everyone in, one match finished, one on court, one
    waiting, one person billed. Empty screens cannot be judged."""
    db = MiniSupabase()
    db.tables["admins"] = [
        {
            "id": ADMIN_ID, "username": "admin", "password_hash": hash_password(PASSWORD),
            "role": "admin", "created_at": _iso(60 * 24 * 90),
        }
    ]
    players = [
        {
            "id": str(uuid.uuid4()), "nickname": name, "avatar_url": None,
            "elo_score": 1000 + i * 40, "elo_level": TIERS[i], "line_id": None,
            "is_active": True, "member_seq": i + 1, "dominant_hand": None,
            "tiktok": None, "instagram": None, "quote": None,
            "games": 0, "wins": 0, "draws": 0, "losses": 0, "created_at": _iso(60 * 24 * 60),
        }
        for i, name in enumerate(NAMES)
    ]
    db.tables["players"] = players
    pid = [p["id"] for p in players]

    session_id = str(uuid.uuid4())
    db.tables["sessions"] = [
        {
            "id": session_id, "date": datetime.now().date().isoformat(),
            "location": "KB badminton court โยธินพัฒนา", "court_fee_per_person": 80,
            "shuttlecock_price_per_game": 29, "status": "open",
            "created_by": ADMIN_ID, "created_at": _iso(120),
        }
    ]
    db.tables["checkins"] = [
        {"id": str(uuid.uuid4()), "session_id": session_id, "player_id": p,
         "checkin_time": _iso(115), "checkout_time": None}
        for p in pid
    ]

    def match(team1: list[str], team2: list[str], status: str, minutes: int,
              court: str | None, winner: str | None = None) -> dict[str, Any]:
        return {
            "id": str(uuid.uuid4()), "session_id": session_id, "type": "double",
            "team1_player_ids": team1, "team2_player_ids": team2, "sets": None,
            "winner": winner, "status": status, "court": court,
            "elo_delta_team1": 2 if winner else None,
            "elo_delta_team2": -2 if winner else None,
            "created_at": _iso(minutes), "updated_at": _iso(minutes - 25),
        }

    db.tables["matches"] = [
        match([pid[0], pid[2]], [pid[1], pid[3]], "completed", 95, "1", "team1"),
        match([pid[4], pid[6]], [pid[5], pid[7]], "completed", 60, "2", "team2"),
        match([pid[0], pid[1]], [pid[2], pid[3]], "in_progress", 20, "1"),
        match([pid[4], pid[5]], [pid[6], pid[7]], "queued", 5, "2"),
    ]
    for p in players[:8]:
        p["games"], p["wins"], p["losses"] = 1, 1 if players.index(p) % 2 == 0 else 0, 0

    db.tables["club_settings"] = [
        {"id": 1, "promptpay_id": "0812345678", "promptpay_type": "phone",
         "default_court_fee_per_person": 80, "default_shuttlecock_price_per_game": 29,
         "payment_method": "promptpay", "bank_name": None, "bank_account_number": None,
         "bank_account_name": None, "uploaded_qr_url": None}
    ]
    db.tables["billings"] = [
        {"id": str(uuid.uuid4()), "session_id": session_id, "player_id": pid[7],
         "game_count": 1, "amount_calc": 109.0, "amount_adjusted": None,
         "paid_status": "unpaid", "promptpay_ref": None, "updated_at": _iso(10)}
    ]
    db.tables["expenses"] = [
        {"id": str(uuid.uuid4()), "expense_date": datetime.now().date().isoformat(),
         "category": "shuttlecock", "custom_category": None, "amount": 580.0,
         "paid_by": ADMIN_ID, "note": "ลูกแบด 1 โหล", "receipt_url": None,
         "is_paid": False, "paid_at": None, "created_by": ADMIN_ID, "created_at": _iso(50)}
    ]
    db.tables["other_income"] = [
        {"id": str(uuid.uuid4()), "income_date": datetime.now().date().isoformat(),
         "source": "sponsor", "source_name": "ร้านลูกแบดนิดเดียว", "amount": 1000.0,
         "note": None, "slip_url": None, "created_by": ADMIN_ID, "created_at": _iso(40)}
    ]
    _seed_oversized_avatars(db, players[:2])

    for table in ("locked_pairs", "pairing_history", "admin_activity_log"):
        db.tables.setdefault(table, [])
    return db


DB = seed()
app.dependency_overrides[get_supabase] = lambda: DB
# The activity-log middleware reaches for the client directly rather than
# through the dependency, so both names have to point at the stand-in.
supabase_client.get_supabase_client = lambda: DB  # type: ignore[assignment]
activity_log_mw.get_supabase_client = lambda: DB  # type: ignore[assignment]


@app.get("/__uxlab/state")
def _state() -> dict[str, object]:
    """What the server believes, so a check can assert on stored data rather
    than only on what was drawn.

    `storage_files` carries each stored object's size, which is how a check
    on the avatar-shrinking pass can see that the bucket actually got
    smaller rather than trusting the screen's own arithmetic.
    """
    return {
        "tables": {name: rows for name, rows in DB.tables.items()},
        "storage_files": dict(DB.storage_files),
        # The tables were at the top level before this; kept there so an
        # older check still reads.
        **{name: rows for name, rows in DB.tables.items()},
    }


if __name__ == "__main__":
    import uvicorn

    print(f"uxlab: admin / {PASSWORD} on http://127.0.0.1:{PORT}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
