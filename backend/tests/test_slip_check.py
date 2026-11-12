"""Reading the QR on transfer slips, and flagging a slip used twice.

Slips here are drawn with the qrcode package in the Bank of Thailand's slip
format, then put through the same upload as members' slips."""

import io
import json
import os
import sys
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
import qrcode
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "uxlab"))
from minisupabase import MiniSupabase

from app.deps import get_supabase
from app.main import app
from app.security import create_access_token, create_line_token
from app.services import credit_card_service, slip_check

BALL, BANK = "U" + "a" * 32, "U" + "b" * 32
ADMIN_ID = str(uuid4())


def slip_payload(ref: str, bank: str = "004") -> str:
    inner = "0006000001" + f"01{len(bank):02d}{bank}" + f"02{len(ref):02d}{ref}"
    return f"00{len(inner):02d}{inner}5102TH9104ABCD"


def slip_image(payload: str | None, size: tuple[int, int] = (1170, 2532)) -> bytes:
    """A phone-screenshot-sized slip, with this payload in its QR (or none)."""
    im = Image.new("RGB", size, (246, 248, 250))
    if payload is not None:
        q = qrcode.QRCode(border=2, box_size=8)
        q.add_data(payload)
        q.make()
        code = q.make_image().convert("RGB").resize((240, 240), Image.NEAREST)
        im.paste(code, (size[0] - 330, size[1] - 520))
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=85)
    return out.getvalue()


def admin() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=ADMIN_ID, role='admin')}"}


def member(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_line_token(user_id, 'LINE name')}"}


def player(nickname: str, seq: int, **extra: Any) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "nickname": nickname,
        "member_seq": seq,
        "elo_score": 1000,
        "elo_level": "beer",
        "is_active": True,
        "created_at": "2026-01-01T00:00:00Z",
        **extra,
    }


@pytest.fixture
def db() -> Iterator[MiniSupabase]:
    fake = MiniSupabase(
        {
            "players": [player("Ball", 1, line_user_id=BALL), player("Bank", 2, line_user_id=BANK)],
            "admins": [{"id": ADMIN_ID, "username": "admin"}],
            "credit_packages": [
                {
                    "id": str(uuid4()),
                    "credits": 1000,
                    "price": 950,
                    "is_active": True,
                    "sort_order": 0,
                }
            ],
            "club_settings": [
                {
                    "id": 1,
                    "payment_method": "promptpay",
                    "promptpay_id": "0812345678",
                    "promptpay_type": "phone",
                    "bank_name": None,
                    "bank_account_number": None,
                    "bank_account_name": None,
                    "uploaded_qr_url": None,
                    "default_court_fee_per_person": 80,
                    "default_shuttlecock_price_per_game": 29,
                }
            ],
            "slip_checks": [],
        }
    )
    app.dependency_overrides[get_supabase] = lambda: fake
    credit_card_service.invalidate()
    yield fake
    app.dependency_overrides.pop(get_supabase, None)
    credit_card_service.invalidate()


@pytest.fixture
def client(db: MiniSupabase) -> TestClient:
    return TestClient(app)


def top_up(client: TestClient, db: MiniSupabase, who: str, image: bytes) -> str:
    pkg = str(db.tables["credit_packages"][0]["id"])
    tid = client.post(
        "/api/line/credit/topups", json={"package_id": pkg}, headers=member(who)
    ).json()["pending"]["id"]
    res = client.post(
        f"/api/line/credit/topups/{tid}/slip",
        files={"file": ("s.jpg", image, "image/jpeg")},
        headers=member(who),
    )
    assert res.status_code == 200, res.text
    return str(tid)


def checks(client: TestClient, kind: str, *ids: str) -> list[dict[str, Any]]:
    res = client.get(f"/api/admin/slip-checks?kind={kind}&ids={','.join(ids)}", headers=admin())
    assert res.status_code == 200, res.text
    return res.json()


def test_a_slip_qr_is_read_for_its_reference_and_bank() -> None:
    got = slip_check.read(slip_image(slip_payload("2026111112345ABCDE", "014")))
    assert got == slip_check.SlipQr(found=True, ref="2026111112345ABCDE", bank="014")
    # a PromptPay "pay me" QR is a QR, but not a slip's
    pay = slip_check.read(
        slip_image("00020101021129370016A000000677010111011300668123456785802TH6304ABCD")
    )
    assert pay.found and pay.ref is None
    assert slip_check.read(slip_image(None)) == slip_check.SlipQr(found=False)
    assert slip_check.read(b"not an image") == slip_check.SlipQr(found=False)


def test_a_slip_shown_twice_is_flagged_with_where_it_was_first(
    client: TestClient, db: MiniSupabase
) -> None:
    same = slip_image(slip_payload("REF0001AAAA"))
    first = top_up(client, db, BALL, same)
    assert checks(client, "topup", first)[0]["status"] == "ok"
    again = top_up(client, db, BANK, same)
    flagged = checks(client, "topup", first, again)
    # the earlier one is now also known to have a twin; the later says where it was first
    assert flagged[1]["status"] == "duplicate" and flagged[1]["bank"] == "004"
    before = flagged[1]["used_before"]
    assert (
        before["kind"] == "topup"
        and before["target_id"] == first
        and before["who"] == "Ball"
        and before["amount"] == 950
    )


def test_sending_the_same_slip_again_for_the_same_thing_is_not_a_duplicate(
    client: TestClient, db: MiniSupabase
) -> None:
    same = slip_image(slip_payload("REF0002BBBB"))
    tid = top_up(client, db, BALL, same)
    client.post(
        f"/api/line/credit/topups/{tid}/slip",
        files={"file": ("s.jpg", same, "image/jpeg")},
        headers=member(BALL),
    )
    assert checks(client, "topup", tid)[0]["status"] == "ok"
    assert len([r for r in db.tables["slip_checks"] if r["target_id"] == tid]) == 1


def test_no_qr_and_not_a_slip_qr_are_told_apart(client: TestClient, db: MiniSupabase) -> None:
    plain = top_up(client, db, BALL, slip_image(None))
    assert checks(client, "topup", plain)[0]["status"] == "no_qr"
    db.tables["credit_topups"].clear()
    other = top_up(client, db, BALL, slip_image("https://example.com/not-a-slip"))
    assert checks(client, "topup", other)[0]["status"] == "not_slip"
    assert checks(client, "topup", str(uuid4()))[0]["status"] == "unchecked"


def test_a_slip_that_cannot_be_read_still_goes_through(
    client: TestClient, db: MiniSupabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(_: bytes) -> slip_check.SlipQr:
        raise RuntimeError("reader crashed")

    monkeypatch.setattr(slip_check, "read", broken)
    tid = top_up(client, db, BALL, slip_image(slip_payload("REF0003CCCC")))
    assert any(t["id"] == tid and t.get("slip_url") for t in db.tables["credit_topups"])


def test_slips_sent_before_are_read_in_batches(client: TestClient, db: MiniSupabase) -> None:
    # four old top-ups whose slips are in storage but were never read; the
    # first, second and fourth are the same slip
    bucket = db.storage.from_("shop")
    ball = next(p["id"] for p in db.tables["players"] if p["nickname"] == "Ball")
    ids = []
    for n, payload in enumerate(
        [slip_payload("OLD1111111"), slip_payload("OLD1111111"), None, slip_payload("OLD1111111")]
    ):
        path = f"credit-slip-old{n}.jpg"
        bucket.upload(path, slip_image(payload))
        tid = str(uuid4())
        ids.append(tid)
        db.tables.setdefault("credit_topups", []).append(
            {
                "id": tid,
                "player_id": ball,
                "credits": 1000,
                "price": 950,
                "status": "approved",
                "slip_url": bucket.get_public_url(path),
                "slip_sent_at": f"2026-11-0{n + 1}T10:00:00Z",
                "created_at": f"2026-11-0{n + 1}T10:00:00Z",
            }
        )
    total = 0
    for _ in range(5):
        res = client.post("/api/admin/slip-checks/backfill", headers=admin()).json()
        total += res["done"]
        if res["remaining"] == 0:
            break
    assert total == 4 and res["remaining"] == 0
    found = {c["target_id"]: c for c in checks(client, "topup", *ids)}
    assert {k: c["status"] for k, c in found.items()} == {
        ids[0]: "duplicate",
        ids[1]: "duplicate",
        ids[2]: "no_qr",
        ids[3]: "duplicate",
    }
    # each points at the earliest other payment by when it was paid, not by
    # when the backfill happened to read it
    assert found[ids[3]]["used_before"]["when"].startswith("2026-11-01")
    assert found[ids[0]]["used_before"]["when"].startswith("2026-11-02")
    assert found[ids[0]]["used_count"] == 2
    # nothing left to read: a second run does nothing
    assert client.post("/api/admin/slip-checks/backfill", headers=admin()).json() == {
        "done": 0,
        "remaining": 0,
    }


def test_a_night_bill_and_a_shop_order_are_checked_against_each_other(
    client: TestClient, db: MiniSupabase
) -> None:
    """The court-and-shuttle bill paid in LINE and the shop are checked the
    same way as top-ups, and against each other: Ball pays tonight's bill,
    then Bank buys a shirt with a picture of Ball's slip."""
    ball = next(p["id"] for p in db.tables["players"] if p["nickname"] == "Ball")
    bank = next(p["id"] for p in db.tables["players"] if p["nickname"] == "Bank")
    sid, bill_id, shirt = str(uuid4()), str(uuid4()), str(uuid4())
    db.tables["sessions"] = [
        {"id": sid, "date": "2026-11-11", "location": "KB court", "status": "open",
         "court_fee_per_person": 80, "shuttlecock_price_per_game": 29,
         "created_at": "2026-11-11T18:00:00Z"}
    ]  # fmt: skip
    db.tables["billings"] = [
        {"id": bill_id, "session_id": sid, "player_id": ball, "game_count": 3,
         "amount_calc": 167.0, "amount_adjusted": None, "paid_status": "unpaid",
         "credit_used": 0, "updated_at": "2026-11-11T22:00:00Z"}
    ]  # fmt: skip
    db.tables["products"] = [
        {"id": shirt, "name": "เสื้อก๊วน", "description": None, "price": 390, "sale_type": "stock",
         "sizes": ["M"], "size_prices": {}, "preorder_closes_on": None,
         "preorder_delivers_on": None, "image_urls": [], "is_active": True, "sort_order": 0,
         "created_at": "2026-10-28T00:00:00Z"}
    ]  # fmt: skip
    db.tables["product_stock"] = [{"product_id": shirt, "size": "M", "qty": 5}]
    db.tables.setdefault("shop_orders", [])
    db.tables.setdefault("shop_order_items", [])
    slip = slip_image(slip_payload("016315220000BILL01", bank="014"))

    sent = client.post(
        f"/api/line/bills/{bill_id}/slip",
        files={"file": ("s.jpg", slip, "image/jpeg")},
        headers=member(BALL),
    )
    assert sent.status_code == 200, sent.text
    [alone] = checks(client, "bill", bill_id)
    assert (alone["status"], alone["bank"]) == ("ok", "014")

    order = client.post(
        "/api/shop/orders",
        data={
            "player_id": bank,
            "items": json.dumps([{"product_id": shirt, "size": "M", "qty": 1}]),
        },
        files={"file": ("s.jpg", slip, "image/jpeg")},
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]

    [bill] = checks(client, "bill", bill_id)
    [shop] = checks(client, "order", order_id)
    assert bill["status"] == shop["status"] == "duplicate"
    assert (bill["used_before"]["kind"], bill["used_before"]["who"]) == ("order", "Bank")
    assert (shop["used_before"]["kind"], shop["used_before"]["who"]) == ("bill", "Ball")
    assert shop["used_before"]["amount"] == 167


def test_slip_checks_are_for_admins(client: TestClient) -> None:
    assert client.get(f"/api/admin/slip-checks?kind=topup&ids={uuid4()}").status_code == 401
    assert client.post("/api/admin/slip-checks/backfill", headers=member(BALL)).status_code == 401
    assert (
        client.get(f"/api/admin/slip-checks?kind=nope&ids={uuid4()}", headers=admin()).status_code
        == 422
    )
