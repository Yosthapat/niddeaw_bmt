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

from fastapi import Response

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

# LINE switched on, with a stand-in for LINE's verify endpoint below: a
# browser test hands the page a fake LIFF whose ID token is
# "fake:<U + 32 hex>:<display name>".
os.environ.setdefault("LINE_LOGIN_CHANNEL_ID", "1234567890")
os.environ.setdefault("LINE_LIFF_ID", "1234567890-uxlab")

from minisupabase import MiniSupabase  # noqa: E402

import app.middleware.activity_log as activity_log_mw  # noqa: E402
import app.supabase_client as supabase_client  # noqa: E402
from app.deps import get_supabase  # noqa: E402
from app.main import app  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services import line_auth  # noqa: E402

ADMIN_ID = str(uuid.uuid4())
# Names shaped like the club's real ones — English, capitalised, and
# including the apostrophe someone actually has. The app now refuses a
# nickname that is not, so a lab seeded with Thai names would be a lab
# whose own members could not be re-saved through its own screens.
NAMES = ["Ball", "James", "Faa", "Ton", "Oum", "Mew", "Tan", "P'Tee"]
TIERS = ["beer", "beer", "soju", "soju", "highball", "milk", "beer", "soju"]


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

    db.tables["quest_settings"] = [
        {"id": 1, "start_date": (datetime.now().date() - timedelta(days=14)).isoformat(),
         "monthly_target": 20, "synced_key": None}
    ]
    db.tables["player_badges"] = []
    db.tables["club_settings"] = [
        {"id": 1, "promptpay_id": "0812345678", "promptpay_type": "phone",
         "default_court_fee_per_person": 80, "default_shuttlecock_price_per_game": 29,
         "payment_method": "promptpay", "bank_name": None, "bank_account_number": None,
         "bank_account_name": None, "uploaded_qr_url": None}
    ]
    db.tables["billings"] = [
        {"id": str(uuid.uuid4()), "session_id": session_id, "player_id": pid[7],
         "game_count": 1, "amount_calc": 109.0, "amount_adjusted": None,
         "paid_status": "unpaid", "promptpay_ref": None, "updated_at": _iso(10), "credit_used": 0}
    ]
    db.tables["expenses"] = [
        {"id": str(uuid.uuid4()), "expense_date": datetime.now().date().isoformat(),
         "category": "shuttlecock", "custom_category": None, "amount": 580.0,
         "paid_by": ADMIN_ID, "note": "ลูกแบด 1 โหล",
         "receipt_url": "https://fake.supabase.co/storage/v1/object/public/receipts/exp-1.jpg",
         "is_paid": False, "paid_at": None, "created_by": ADMIN_ID, "created_at": _iso(50)}
    ]
    db.tables["other_income"] = [
        {"id": str(uuid.uuid4()), "income_date": datetime.now().date().isoformat(),
         "source": "sponsor", "source_name": "ร้านลูกแบดนิดเดียว", "amount": 1000.0,
         "note": None, "slip_url": None, "created_by": ADMIN_ID, "created_at": _iso(40)}
    ]
    db.tables["sponsors"] = [
        {"id": str(uuid.uuid4()), "name": name, "href": f"https://www.instagram.com/{ig}",
         "logo_url": f"/sponsors/{slug}-mono.png", "logo_width": w, "logo_height": h,
         "sort_order": i, "is_visible": True, "created_at": _iso(400 - i)}
        for i, (name, ig, slug, w, h) in enumerate([
            ("Wasteland", "wastelandbkk", "wasteland", 424, 104),
            ("Match Mellow", "match.mellowww", "match-mellow", 323, 205),
            ("Sawadee Natural Herbal Balm", "sawadee_naturalherbalbalm", "sawadee", 417, 350),
            ("Umore Made", "umore.made", "umore-made", 449, 169),
            ("The Players Club", "theplayersclubthailand", "players-club", 354, 388),
        ], start=1)
    ]
    shirt, cap, towel = (str(uuid.uuid4()) for _ in range(3))
    today = datetime.now().date()
    db.tables["products"] = [
        {"id": shirt, "name": "เสื้อก๊วน นิดเดียว 2026", "description": "ผ้าไมโคร ใส่ตีแบดสบาย\nสกรีนแมวมงกุฎด้านหลัง",
         "price": 390.0, "sale_type": "preorder", "sizes": ["S", "M", "L", "XL", "2XL"],
         "size_prices": {"XL": 410.0, "2XL": 430.0},
         "preorder_closes_on": (today + timedelta(days=9)).isoformat(),
         "preorder_delivers_on": (today + timedelta(days=30)).isoformat(),
         "image_urls": ["/hero/cat-color.webp", "/ads/friday-night.webp"], "is_active": True, "sort_order": 0,
         "created_at": _iso(60 * 24 * 3)},
        {"id": cap, "name": "หมวกแก๊ป BMT", "description": None, "price": 250.0, "size_prices": {},
         "sale_type": "stock", "sizes": [], "preorder_closes_on": None,
         "preorder_delivers_on": None, "image_urls": [], "is_active": True, "sort_order": 1,
         "created_at": _iso(60 * 24 * 2)},
        {"id": towel, "name": "ผ้าเช็ดหน้า นิดเดียว", "description": "ผ้าคอตตอน 30×30 ซม.",
         "price": 120.0, "sale_type": "stock", "sizes": ["ฟ้า", "ชมพู"], "size_prices": {},
         "preorder_closes_on": None, "preorder_delivers_on": None, "image_urls": [],
         "is_active": True, "sort_order": 2, "created_at": _iso(60 * 24)},
    ]
    db.tables["product_stock"] = [
        {"product_id": cap, "size": "", "qty": 3},
        {"product_id": towel, "size": "ฟ้า", "qty": 0},
        {"product_id": towel, "size": "ชมพู", "qty": 5},
    ]

    orders: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []

    def order(no: int, who: int, lines: list[tuple[str, str, str, str, int, float]], status: str,
              minutes: int) -> None:
        oid = str(uuid.uuid4())
        total = sum(price * qty for *_, qty, price in lines)
        orders.append({"id": oid, "order_no": no, "player_id": pid[who], "total": total,
                       "slip_url": "/hero/cat-color.webp", "status": status,
                       "note": "ยอดในสลิปไม่ตรง" if status == "rejected" else None,
                       "created_at": _iso(minutes), "updated_at": _iso(minutes)})
        for product, name, kind, size, qty, price in lines:
            items.append({"id": str(uuid.uuid4()), "order_id": oid, "product_id": product,
                          "product_name": name, "sale_type": kind, "size": size, "qty": qty,
                          "unit_price": price, "line_total": price * qty, "created_at": _iso(minutes)})

    shirt_name = "เสื้อก๊วน นิดเดียว 2026"
    order(1, 0, [(shirt, shirt_name, "preorder", "M", 2, 390.0), (cap, "หมวกแก๊ป BMT", "stock", "", 1, 250.0)],
          "pending", 30)
    order(2, 1, [(shirt, shirt_name, "preorder", "XL", 1, 410.0)], "confirmed", 300)
    order(3, 0, [(cap, "หมวกแก๊ป BMT", "stock", "", 1, 250.0)], "rejected", 900)
    db.tables["credit_packages"] = [
        {"id": str(uuid.uuid4()), "credits": 1000, "price": 950.0, "is_active": True, "sort_order": 0,
         "created_at": _iso(60 * 24 * 5)},
        {"id": str(uuid.uuid4()), "credits": 5000, "price": 4500.0, "is_active": True, "sort_order": 1,
         "created_at": _iso(60 * 24 * 5)},
    ]
    db.tables["shop_orders"] = orders
    db.tables["shop_order_items"] = items
    for table in ("locked_pairs", "pairing_history", "admin_activity_log"):
        db.tables.setdefault(table, [])
    return db


def quest_history(db: MiniSupabase) -> None:
    """UXLAB_QUESTS=1: ten weekly nights before tonight, a dozen games each,
    so the badge shelf, member cards and the home feed have medals to show.
    Ball wins most of his games (gold medals); P'Tee rarely plays."""
    import random

    rnd = random.Random(7)
    pid = [p["id"] for p in db.tables["players"]]
    today = datetime.now().date()
    db.tables["quest_settings"][0]["start_date"] = (today - timedelta(days=80)).isoformat()
    for week in range(10, 0, -1):
        d = today - timedelta(days=7 * week)
        sid = str(uuid.uuid4())
        start = datetime(d.year, d.month, d.day, 11, tzinfo=timezone.utc)
        db.tables["sessions"].append({
            "id": sid, "date": d.isoformat(), "location": "KB badminton court โยธินพัฒนา",
            "court_fee_per_person": 80, "shuttlecock_price_per_game": 29, "status": "closed",
            "created_by": ADMIN_ID, "created_at": start.isoformat(),
        })
        here = pid[:7] if week % 3 else pid
        for i, p in enumerate(here):
            db.tables["checkins"].append({
                "id": str(uuid.uuid4()), "session_id": sid, "player_id": p,
                "checkin_time": (start + timedelta(minutes=2 + i * 3)).isoformat(),
                "checkout_time": (start + timedelta(hours=3, minutes=i * 4)).isoformat(),
            })
        for g in range(12):
            four = rnd.sample(here, 4)
            if g % 2 == 0 and pid[0] not in four:
                four[0] = pid[0]
            t1, t2 = four[:2], four[2:]
            winner = "team1" if (pid[0] in t1 and rnd.random() < 0.85) else rnd.choice(["team1", "team2", "team2", "draw"])
            if pid[0] in t2:
                winner = "team2" if rnd.random() < 0.85 else "team1"
            when = start + timedelta(minutes=10 + g * 14)
            delta = 0 if winner == "draw" else 2
            db.tables["matches"].append({
                "id": str(uuid.uuid4()), "session_id": sid, "type": "double",
                "team1_player_ids": t1, "team2_player_ids": t2, "sets": None, "winner": winner,
                "status": "completed", "court": "1",
                "elo_delta_team1": delta if winner == "team1" else -delta,
                "elo_delta_team2": delta if winner == "team2" else -delta,
                "created_at": when.isoformat(), "updated_at": (when + timedelta(minutes=12)).isoformat(),
            })
    db.tables["matches"].sort(key=lambda m: m["created_at"])


def credit_cards(db: MiniSupabase) -> None:
    """UXLAB_CARDS=1: James bought a 5,000 pack in LINE (black card), Faa a
    1,000 pack (pink), Ton has credit an admin added at the court (no card)."""
    for t in ("credit_topups", "credit_ledger", "player_credits"):
        db.tables.setdefault(t, [])
    names = {p["nickname"]: p["id"] for p in db.tables["players"]}
    for n, (who, credits, line) in enumerate((("James", 5000, True), ("Faa", 1000, True), ("Ton", 2000, False))):
        pid = names[who]
        top = str(uuid.uuid4())
        if line:
            db.tables["credit_topups"].append({
                "id": top, "player_id": pid, "credits": credits, "price": credits * 0.9, "slip_url": None,
                "slip_sent_at": _iso(60), "status": "approved", "note": None, "decided_at": _iso(50),
                "created_at": _iso(61),
            })
        db.tables["credit_ledger"].append({
            "id": str(uuid.uuid4()), "player_id": pid, "delta": credits, "balance_after": credits,
            "kind": "topup", "cash": credits * 0.9, "ref_id": top if line else None, "note": "uxlab",
            "admin_id": ADMIN_ID, "created_at": _iso(50 - n),
        })
        db.tables["player_credits"].append({"player_id": pid, "balance": credits, "updated_at": _iso(50)})


def slip_lab(db: MiniSupabase) -> None:
    """UXLAB_SLIPS=1: slips sent before slip checks existed, waiting for the
    admin's backfill. Faa and James sent the same slip for their top-ups
    (the duplicate), Ton's is a cropped one with no QR, and shop order #1
    reused Faa's slip."""
    import io

    import qrcode
    from PIL import Image

    def picture(ref: str | None) -> bytes:
        im = Image.new("RGB", (1170, 2532), (246, 248, 250))
        if ref is not None:
            inner = "0006000001" + "0103004" + f"02{len(ref):02d}{ref}"
            q = qrcode.QRCode(border=2, box_size=8)
            q.add_data(f"00{len(inner):02d}{inner}5102TH9104ABCD")
            q.make()
            im.paste(q.make_image().convert("RGB").resize((240, 240), Image.NEAREST), (840, 2012))
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=85)
        return out.getvalue()

    def stored(name: str, data: bytes) -> str:
        db.storage_bytes[f"shop/slip-{name}.jpg"] = data
        return f"{db.public_base}/storage/v1/object/public/shop/slip-{name}.jpg"

    db.tables.setdefault("credit_topups", [])
    db.tables.setdefault("slip_checks", [])
    names = {p["nickname"]: p["id"] for p in db.tables["players"]}
    same = picture("016101234567ATF07")
    for n, (who, data) in enumerate((("Faa", same), ("James", same), ("Ton", picture(None)))):
        db.tables["credit_topups"].append({
            "id": str(uuid.uuid4()), "player_id": names[who], "credits": 1000, "price": 950.0,
            "slip_url": stored(f"topup-{n}", data), "slip_sent_at": _iso(20 - n * 5), "status": "pending",
            "note": None, "decided_at": None, "created_at": _iso(21 - n * 5),
        })
    db.tables["shop_orders"][0]["slip_url"] = stored("order-1", same)
    db.tables["billings"][0].update(
        slip_url=stored("bill-1", picture("016101234999ATF11")), slip_sent_at=_iso(8)
    )


DB = seed()
if os.environ.get("UXLAB_QUESTS"):
    quest_history(DB)
if os.environ.get("UXLAB_CARDS"):
    credit_cards(DB)
DB.public_base = f"http://127.0.0.1:{PORT}"
if os.environ.get("UXLAB_SLIPS"):
    slip_lab(DB)
app.dependency_overrides[get_supabase] = lambda: DB
# The activity-log middleware reaches for the client directly rather than
# through the dependency, so both names have to point at the stand-in.
supabase_client.get_supabase_client = lambda: DB  # type: ignore[assignment]
activity_log_mw.get_supabase_client = lambda: DB  # type: ignore[assignment]


def _fake_verify(id_token: str, http: object = None) -> line_auth.LineProfile:
    parts = id_token.split(":", 2)
    if len(parts) != 3 or parts[0] != "fake":
        raise line_auth.LineAuthError("not a uxlab token")
    return line_auth.LineProfile(user_id=parts[1], name=parts[2], picture=None)


line_auth.verify_id_token = _fake_verify  # type: ignore[assignment]


@app.get("/__uxlab/state")
def _state() -> dict[str, object]:
    """What the server believes, so a check can assert on stored data rather
    than only on what was drawn."""
    return {name: rows for name, rows in DB.tables.items()}


@app.get("/storage/v1/object/public/{bucket}/{path}")
def _stored(bucket: str, path: str) -> Response:
    """Serves what the API uploaded, at the URL it was told the file has."""
    data = DB.storage_bytes.get(f"{bucket}/{path}")
    if data is None:
        return Response(status_code=404)
    kind = {"png": "image/png", "mp4": "video/mp4", "webm": "video/webm"}.get(path.rsplit(".", 1)[-1], "image/jpeg")
    return Response(content=data, media_type=kind)


if __name__ == "__main__":
    import uvicorn

    print(f"uxlab: admin / {PASSWORD} on http://127.0.0.1:{PORT}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
