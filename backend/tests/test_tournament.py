"""NIDDEAW CUP phase 1 (docs/tournament-spec.md): the two admin rights kept
apart, signing up from LINE, paying the tournament's own account, the
waiting line, refunds, and the tournament's money staying out of the
club's."""

import io
import os
import re
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "uxlab"))
from minisupabase import MiniSupabase

from app.deps import get_supabase
from app.main import app
from app.security import create_access_token, create_line_token, hash_password
from app.services import tournament_service as ts

VAN, MO, AEYA, HELPER = (str(uuid4()) for _ in range(4))
PASSWORD_HASH = hash_password("pw")  # once: bcrypt is slow on purpose
CLUB_TABLES = ("billings", "credit_ledger", "credit_topups", "other_income", "expenses")


def token(admin_id: str, club: bool, tour: bool) -> dict[str, str]:
    jwt = create_access_token(
        admin_id=admin_id, role="admin", club_access=club, tournament_access=tour
    )
    return {"Authorization": f"Bearer {jwt}"}


BOTH = token(VAN, True, True)
CLUB_ONLY = token(AEYA, True, False)
TOUR_ONLY = token(HELPER, False, True)


def line_id(i: int) -> str:
    return "U" + f"{i:032x}"


def member(i: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_line_token(line_id(i), 'LINE')}"}


def png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (40, 60), "white").save(out, format="PNG")
    return out.getvalue()


@pytest.fixture
def db() -> Iterator[MiniSupabase]:
    # 40 players: 0–35 have played enough, 36+ have not. Ratings cover the
    # levels: 0–9 Beer (1000), 10–19 Highball (1200), 20–29 Wine (1400),
    # 30–39 Soju (1600).
    players = [
        {
            "id": str(uuid4()),
            "nickname": f"P{i:02d}",
            "member_seq": i + 1,
            "elo_score": 1000 + 200 * (i // 10),
            "elo_level": ["beer", "highball", "wine", "soju"][i // 10],
            "is_active": True,
            "games": 3 if i < 36 else 1,
            "line_user_id": line_id(i),
            "created_at": "2026-01-01T00:00:00Z",
        }
        for i in range(40)
    ]
    fake = MiniSupabase(
        {
            "admins": [
                {"id": VAN, "username": "admin_van", "password_hash": PASSWORD_HASH, "role": "admin",
                 "club_access": True, "tournament_access": True},
                {"id": MO, "username": "admin_mo", "password_hash": PASSWORD_HASH, "role": "admin",
                 "club_access": True, "tournament_access": True},
                {"id": AEYA, "username": "admin_aeya", "password_hash": PASSWORD_HASH, "role": "admin",
                 "club_access": True, "tournament_access": False},
                {"id": HELPER, "username": "helper", "password_hash": PASSWORD_HASH, "role": "admin",
                 "club_access": False, "tournament_access": True},
            ],
            "players": players,
            "admin_activity_log": [],
            "slip_checks": [],
            **{t: [] for t in CLUB_TABLES},
        }
    )  # fmt: skip
    app.dependency_overrides[get_supabase] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_supabase, None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def pid(db: MiniSupabase, i: int) -> str:
    return str(db.tables["players"][i]["id"])


def open_tournament(client: TestClient) -> dict[str, Any]:
    closes = (datetime.now(UTC) + timedelta(days=14)).isoformat()
    made = client.post(
        "/api/admin/tournament/tournaments",
        json={
            "name": "NIDDEAW CUP 1",
            "starts_on": "2026-12-20",
            "venue": "KB",
            "closes_at": closes,
        },
        headers=BOTH,
    )
    assert made.status_code == 201, made.text
    t = made.json()
    opened = client.patch(
        f"/api/admin/tournament/tournaments/{t['id']}",
        json={
            "promptpay_id": "0812345678",
            "promptpay_type": "phone",
            "account_name": "NIDDEAW CUP",
            "status": "open",
        },
        headers=BOTH,
    )
    assert opened.status_code == 200, opened.text
    return dict(opened.json())


def level_id(t: dict[str, Any], name: str) -> str:
    return next(str(lv["id"]) for lv in t["levels"] if lv["name"] == name)


DETAILS = {"first_name": "สมชาย", "last_name": "ใจดี", "phone": "0812345678"}
PARTNER = {"first_name": "สมหญิง", "last_name": "รักแบด", "phone": "0898765432"}


def sign_up(
    client: TestClient, db: MiniSupabase, t: dict[str, Any], a: int, b: int, level: str, name: str
) -> Any:
    return client.post(
        "/api/line/tournament/team",
        json={
            **DETAILS,
            "partner_id": pid(db, b),
            "level_id": level_id(t, level),
            "team_name": name,
        },
        headers=member(a),
    )


def pay(client: TestClient, i: int) -> Any:
    return client.post(
        "/api/line/tournament/slip",
        files={"file": ("slip.png", png(), "image/png")},
        headers=member(i),
    )


def entrant_of(db: MiniSupabase, i: int) -> dict[str, Any]:
    return next(
        e for e in db.tables["tournament_entrants"] if e["player_id"] == pid(db, i) and e["active"]
    )


# --- the two rights ----------------------------------------------------------


def _admin_routes(prefix_in: bool) -> list[tuple[str, str]]:
    """Every admin (method, path), read from the OpenAPI schema — this
    FastAPI keeps included routers nested, so app.routes finds nothing
    (see test_api_auth.admin_routes)."""
    shared = {"/api/admin/auth/login", "/api/admin/auth/me", "/api/admin/auth/whoami"}
    out: list[tuple[str, str]] = []
    for path, operations in app.openapi()["paths"].items():
        if (
            not path.startswith("/api/admin/")
            or path in shared
            or path.startswith("/api/admin/sheets/internal")
        ):
            continue
        if path.startswith("/api/admin/tournament") != prefix_in:
            continue
        out.extend((m.upper(), path) for m in operations if m.lower() not in {"head", "options"})
    return sorted(out)


def _call(client: TestClient, method: str, path: str, headers: dict[str, str]) -> int:
    concrete = re.sub(r"\{[^}]+\}", str(uuid4()), path)
    return int(client.request(method, concrete, headers=headers).status_code)


def test_a_tournament_only_admin_opens_no_club_route(db: MiniSupabase, client: TestClient) -> None:
    routes = _admin_routes(prefix_in=False)
    assert len(routes) > 50
    opened = [f"{m} {p}" for m, p in routes if _call(client, m, p, TOUR_ONLY) != 403]
    assert opened == []


def test_a_club_only_admin_opens_no_tournament_route(db: MiniSupabase, client: TestClient) -> None:
    routes = _admin_routes(prefix_in=True)
    assert len(routes) > 15
    opened = [f"{m} {p}" for m, p in routes if _call(client, m, p, CLUB_ONLY) != 403]
    assert opened == []


def test_login_puts_the_rights_in_the_token(db: MiniSupabase, client: TestClient) -> None:
    for username, club, tour in [
        ("admin_van", True, True),
        ("admin_aeya", True, False),
        ("helper", False, True),
    ]:
        got = client.post("/api/admin/auth/login", json={"username": username, "password": "pw"})
        assert got.status_code == 200
        headers = {"Authorization": f"Bearer {got.json()['access_token']}"}
        me = client.get("/api/admin/auth/me", headers=headers).json()
        assert (me["username"], me["club_access"], me["tournament_access"]) == (
            username,
            club,
            tour,
        )


def test_a_token_from_before_the_rights_is_the_club_only(
    db: MiniSupabase, client: TestClient
) -> None:
    from jose import jwt

    from app.config import get_settings

    old = jwt.encode(
        {"sub": VAN, "role": "admin", "exp": datetime.now(UTC) + timedelta(hours=1)},
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {old}"}
    assert client.get("/api/admin/tournament/tournaments", headers=headers).status_code == 403
    assert client.get("/api/admin/expenses", headers=headers).status_code != 403


def test_each_side_reads_only_its_own_activity(db: MiniSupabase, client: TestClient) -> None:
    db.tables["admin_activity_log"] = [
        {"id": str(uuid4()), "admin_id": VAN, "action": "เพิ่มรายจ่าย", "method": "POST",
         "path": "/api/admin/expenses", "detail": None, "area": "club", "created_at": "2026-11-15T10:00:00+00:00"},
        {"id": str(uuid4()), "admin_id": VAN, "action": "สร้างทัวร์นาเมนต์", "method": "POST",
         "path": "/api/admin/tournament/tournaments", "detail": None, "area": "tournament",
         "created_at": "2026-11-15T11:00:00+00:00"},
    ]  # fmt: skip
    club = client.get("/api/admin/activity-log", headers=BOTH).json()
    tour = client.get("/api/admin/tournament/activity", headers=BOTH).json()
    assert [e["path"] for e in club] == ["/api/admin/expenses"]
    assert [e["path"] for e in tour] == ["/api/admin/tournament/tournaments"]


def test_only_tournament_admins_are_listed_for_paid_by(
    db: MiniSupabase, client: TestClient
) -> None:
    names = [a["username"] for a in client.get("/api/admin/tournament/admins", headers=BOTH).json()]
    assert names == ["admin_mo", "admin_van", "helper"]


# --- the event -----------------------------------------------------------------


def test_a_new_tournament_has_the_club_s_four_levels(db: MiniSupabase, client: TestClient) -> None:
    t = open_tournament(client)
    assert [(lv["name"], lv["min_elo"], lv["max_elo"], lv["max_teams"]) for lv in t["levels"]] == [
        ("Milk–Beer", None, 1100, 16),
        ("Highball", 1100, 1300, 16),
        ("Wine", 1300, 1500, 16),
        ("Soju ขึ้นไป", 1500, None, 16),
    ]
    assert [lv["rules"] for lv in t["levels"]] == ["ห้ามเสิร์ฟยิง"] * 3 + [""]
    assert (t["entry_fee"], t["shuttle_fee"], t["coupons_per_set"], t["extra_set_price"], t["coupon_refund_price"]) == (
        1600, 450, 6, 450, 70,
    )  # fmt: skip


def test_a_trial_tournament_can_be_deleted_until_it_is_played(
    db: MiniSupabase, client: TestClient
) -> None:
    t = open_tournament(client)
    assert sign_up(client, db, t, 20, 21, "Wine", "ลองเล่น").status_code == 200
    mine = entrant_of(db, 20)
    db.tables["slip_checks"] += [
        {"id": str(uuid4()), "kind": "tournament", "target_id": mine["id"], "qr_hash": "a"},
        {"id": str(uuid4()), "kind": "bill", "target_id": str(uuid4()), "qr_hash": "b"},
    ]
    # a club-only admin can't
    no = client.delete(
        f"/api/admin/tournament/tournaments/{t['id']}", headers=token(AEYA, True, False)
    )
    assert no.status_code == 403

    got = client.delete(f"/api/admin/tournament/tournaments/{t['id']}", headers=BOTH)
    assert got.status_code == 204, got.text
    assert not [x for x in db.tables["tournaments"] if x["id"] == t["id"]]
    # the trial's slip goes too, so the real payment isn't read as a repeat
    assert [c["kind"] for c in db.tables["slip_checks"]] == ["bill"]

    # one being played is the record of a real day
    real = open_tournament(client)
    for row in db.tables["tournaments"]:
        if row["id"] == real["id"]:
            row["status"] = "running"
    kept = client.delete(f"/api/admin/tournament/tournaments/{real['id']}", headers=BOTH)
    assert kept.status_code == 409


def test_it_won_t_open_without_its_own_account(db: MiniSupabase, client: TestClient) -> None:
    closes = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    t = client.post(
        "/api/admin/tournament/tournaments",
        json={"name": "Cup", "starts_on": "2026-12-20", "closes_at": closes},
        headers=BOTH,
    ).json()
    got = client.patch(
        f"/api/admin/tournament/tournaments/{t['id']}", json={"status": "open"}, headers=BOTH
    )
    assert got.status_code == 400
    assert "PromptPay" in got.json()["detail"]


def test_a_level_takes_16_24_or_32_teams_only(db: MiniSupabase, client: TestClient) -> None:
    t = open_tournament(client)
    url = f"/api/admin/tournament/tournaments/{t['id']}/levels/{level_id(t, 'Wine')}"
    assert client.patch(url, json={"max_teams": 20}, headers=BOTH).status_code == 422
    got = client.patch(url, json={"max_teams": 24, "cut_24": True}, headers=BOTH)
    assert got.status_code == 200
    wine = next(lv for lv in got.json()["levels"] if lv["name"] == "Wine")
    assert (wine["max_teams"], wine["cut_24"]) == (24, True)


# --- signing up --------------------------------------------------------------


def test_a_pair_signs_up_pays_and_is_confirmed(db: MiniSupabase, client: TestClient) -> None:
    t = open_tournament(client)
    got = sign_up(client, db, t, 20, 21, "Wine", "ตบเบาๆ")
    assert got.status_code == 200, got.text
    assert got.json()["team"]["status"] == "invited"

    # the partner sees the invite and accepts with their own details
    seen = client.get("/api/line/tournament", headers=member(21)).json()
    assert (seen["my_role"], seen["team"]["name"]) == ("partner", "ตบเบาๆ")
    # nobody sees the other's real name or phone
    captain_view = [e for e in seen["team"]["entrants"] if e["role"] == "captain"][0]
    assert captain_view["first_name"] is None and captain_view["phone"] is None
    assert (
        client.post("/api/line/tournament/accept", json=PARTNER, headers=member(21)).status_code
        == 200
    )

    # each pays half of 1,600 + 450 into the tournament's account
    info = client.get("/api/line/tournament/pay", headers=member(20)).json()
    assert (info["amount"], info["bank_account_name"]) == (1025.0, "NIDDEAW CUP")
    assert pay(client, 20).json()["team"]["status"] == "awaiting_payment"
    assert pay(client, 21).json()["team"]["status"] == "slip_review"

    for i in (20, 21):
        e = entrant_of(db, i)
        assert (
            client.post(
                f"/api/admin/tournament/entrants/{e['id']}/approve", headers=BOTH
            ).status_code
            == 200
        )
    team = client.get("/api/line/tournament", headers=member(20)).json()["team"]
    assert team["status"] == "confirmed"

    money = client.get(f"/api/admin/tournament/tournaments/{t['id']}/money", headers=BOTH).json()
    assert sorted((m["category"], m["amount"]) for m in money) == [
        ("entry_fee", 1025.0),
        ("entry_fee", 1025.0),
    ]
    # and none of it reached the club's money
    assert all(db.tables[name] == [] for name in CLUB_TABLES)


def test_the_public_page_shows_nicknames_only(db: MiniSupabase, client: TestClient) -> None:
    t = open_tournament(client)
    sign_up(client, db, t, 20, 21, "Wine", "ตบเบาๆ")
    client.post("/api/line/tournament/accept", json=PARTNER, headers=member(21))
    pay(client, 20)
    pay(client, 21)
    public = client.get("/api/tournament").json()
    wine = next(lv for lv in public["levels"] if lv["name"] == "Wine")
    assert wine["seats_taken"] == 1
    assert [p["nickname"] for p in wine["teams"][0]["players"]] == ["P20", "P21"]
    text = client.get("/api/tournament").text
    for private in ("สมชาย", "ใจดี", "0812345678", "สมหญิง", "0898765432"):
        assert private not in text.replace('"promptpay_id"', "")


def test_admins_see_the_details_and_can_export_them(db: MiniSupabase, client: TestClient) -> None:
    t = open_tournament(client)
    sign_up(client, db, t, 20, 21, "Wine", "ตบเบาๆ")
    client.post("/api/line/tournament/accept", json=PARTNER, headers=member(21))
    teams = client.get(f"/api/admin/tournament/tournaments/{t['id']}/teams", headers=BOTH).json()
    assert [(e["first_name"], e["phone"]) for e in teams[0]["entrants"]] == [
        ("สมชาย", "0812345678"),
        ("สมหญิง", "0898765432"),
    ]
    csv = client.get(f"/api/admin/tournament/tournaments/{t['id']}/teams.csv", headers=BOTH)
    assert csv.status_code == 200 and "สมหญิง" in csv.text and "รอโอน" in csv.text


def test_three_club_games_are_needed_by_both(db: MiniSupabase, client: TestClient) -> None:
    t = open_tournament(client)
    got = sign_up(client, db, t, 30, 36, "Soju ขึ้นไป", "มือใหม่")
    assert got.status_code == 400
    assert "P36" in got.json()["detail"] and "อีก 2 เกม" in got.json()["detail"]
    me = client.get("/api/line/tournament", headers=member(37)).json()["me"]
    assert me["games_needed"] == 2


def test_a_pair_plays_the_stronger_one_s_level_or_above(
    db: MiniSupabase, client: TestClient
) -> None:
    t = open_tournament(client)
    # Beer + Wine: not Milk–Beer, not Highball
    assert sign_up(client, db, t, 0, 20, "Milk–Beer", "ลงต่ำ").status_code == 400
    assert sign_up(client, db, t, 0, 20, "Highball", "ลงต่ำ").status_code == 400
    # ...but Wine, or up to Soju
    assert sign_up(client, db, t, 0, 20, "Soju ขึ้นไป", "ขึ้นสูง").status_code == 200


def test_one_team_per_player_and_names_may_repeat(db: MiniSupabase, client: TestClient) -> None:
    t = open_tournament(client)
    assert sign_up(client, db, t, 20, 21, "Wine", "BADMINTON 3D").status_code == 200
    assert sign_up(client, db, t, 22, 21, "Wine", "ทีมหมา").status_code == 409  # 21 is taken
    # a club's several teams may share its name (the draw keeps them apart)
    assert sign_up(client, db, t, 22, 23, "Wine", "badminton 3d").status_code == 200


def test_players_cannot_withdraw_from_line(db: MiniSupabase, client: TestClient) -> None:
    """Only a tournament admin withdraws a team."""
    t = open_tournament(client)
    sign_up(client, db, t, 20, 21, "Wine", "ทีมแมว")
    client.post("/api/line/tournament/accept", json=PARTNER, headers=member(21))
    assert client.post("/api/line/tournament/withdraw", headers=member(20)).status_code in (
        404,
        405,
    )
    assert (
        client.get("/api/line/tournament", headers=member(20)).json()["team"]["status"]
        == "awaiting_payment"
    )


def test_declining_frees_both_players(db: MiniSupabase, client: TestClient) -> None:
    t = open_tournament(client)
    sign_up(client, db, t, 20, 21, "Wine", "ทีมแมว")
    assert client.post("/api/line/tournament/decline", headers=member(21)).json()["team"] is None
    assert sign_up(client, db, t, 21, 22, "Wine", "ทีมแมว").status_code == 200


def test_an_unanswered_invite_runs_out(
    db: MiniSupabase, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    t = open_tournament(client)
    sign_up(client, db, t, 20, 21, "Wine", "ทีมแมว")
    later = datetime.now(UTC) + timedelta(hours=ts.INVITE_HOURS + 1)
    monkeypatch.setattr(ts, "now", lambda: later)
    assert client.get("/api/line/tournament", headers=member(20)).json()["team"] is None
    assert db.tables["tournament_teams"][0]["status"] == "cancelled"


def test_fees_lock_once_a_slip_is_in(db: MiniSupabase, client: TestClient) -> None:
    t = open_tournament(client)
    url = f"/api/admin/tournament/tournaments/{t['id']}"
    assert client.patch(url, json={"entry_fee": 1800}, headers=BOTH).status_code == 200
    assert client.patch(url, json={"entry_fee": 1600}, headers=BOTH).status_code == 200
    sign_up(client, db, t, 20, 21, "Wine", "ทีมแมว")
    client.post("/api/line/tournament/accept", json=PARTNER, headers=member(21))
    pay(client, 20)
    assert client.patch(url, json={"entry_fee": 1800}, headers=BOTH).status_code == 409
    # the coupon prices stay open to change
    assert client.patch(url, json={"extra_set_price": 500}, headers=BOTH).status_code == 200


# --- refused slips, the waiting line, refunds ----------------------------------


def _fill(
    client: TestClient,
    db: MiniSupabase,
    t: dict[str, Any],
    level: str,
    pairs: list[tuple[int, int]],
) -> None:
    """Sign pairs up at the desk, paid in cash: each takes a place at once."""
    for n, (a, b) in enumerate(pairs):
        got = client.post(
            f"/api/admin/tournament/tournaments/{t['id']}/teams",
            json={
                "level_id": level_id(t, level),
                "team_name": f"โต๊ะ {n}",
                "captain": {**DETAILS, "player_id": pid(db, a)},
                "partner": {**PARTNER, "player_id": pid(db, b)},
                "paid_via": "cash",
            },
            headers=TOUR_ONLY,
        )
        assert got.status_code == 201, got.text


def test_a_full_level_puts_the_next_pair_in_line_then_moves_it_up(
    db: MiniSupabase, client: TestClient
) -> None:
    t = open_tournament(client)
    # 16 cash pairs into Soju ขึ้นไป: anyone may play up, so all 36 eligible players can
    pairs = [(i, i + 1) for i in range(0, 32, 2)]
    _fill(client, db, t, "Soju ขึ้นไป", pairs)
    teams = client.get(f"/api/admin/tournament/tournaments/{t['id']}/teams", headers=BOTH).json()
    assert [x["status"] for x in teams] == ["confirmed"] * 16

    assert sign_up(client, db, t, 32, 33, "Soju ขึ้นไป", "ตัวสำรอง").status_code == 200
    client.post("/api/line/tournament/accept", json=PARTNER, headers=member(33))
    pay(client, 32)
    assert pay(client, 33).json()["team"]["status"] == "waitlist"

    first = teams[0]
    got = client.post(f"/api/admin/tournament/teams/{first['id']}/withdraw", json={}, headers=BOTH)
    assert got.status_code == 200
    assert (
        client.get("/api/line/tournament", headers=member(32)).json()["team"]["status"]
        == "slip_review"
    )
    # the withdrawn pair paid cash: both are owed it back
    withdrawn = next(x for x in got.json() if x["id"] == first["id"])
    assert withdrawn["refund_owed"] == 2050


def test_a_refused_slip_not_resent_gives_the_place_up(
    db: MiniSupabase, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    t = open_tournament(client)
    sign_up(client, db, t, 20, 21, "Wine", "ทีมแมว")
    client.post("/api/line/tournament/accept", json=PARTNER, headers=member(21))
    pay(client, 20)
    pay(client, 21)
    e = entrant_of(db, 21)
    assert (
        client.post(f"/api/admin/tournament/entrants/{e['id']}/reject", headers=BOTH).status_code
        == 200
    )
    team = client.get("/api/line/tournament", headers=member(21)).json()["team"]
    assert team["status"] == "slip_review" and team["expires_at"] is not None

    later = datetime.now(UTC) + timedelta(hours=ts.RESEND_HOURS + 1)
    monkeypatch.setattr(ts, "now", lambda: later)
    assert client.get("/api/line/tournament", headers=member(21)).json()["team"] is None


def test_a_held_place_does_not_run_out_with_the_payment_deadline(
    db: MiniSupabase, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    t = open_tournament(client)
    sign_up(client, db, t, 20, 21, "Wine", "ทีมแมว")
    client.post("/api/line/tournament/accept", json=PARTNER, headers=member(21))
    pay(client, 20)
    team = pay(client, 21).json()["team"]
    assert (team["status"], team["expires_at"]) == ("slip_review", None)
    later = datetime.now(UTC) + timedelta(hours=ts.PAY_HOURS + 1)
    monkeypatch.setattr(ts, "now", lambda: later)
    assert (
        client.get("/api/line/tournament", headers=member(20)).json()["team"]["status"]
        == "slip_review"
    )


def test_a_resent_slip_keeps_the_place(
    db: MiniSupabase, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    t = open_tournament(client)
    sign_up(client, db, t, 20, 21, "Wine", "ทีมแมว")
    client.post("/api/line/tournament/accept", json=PARTNER, headers=member(21))
    pay(client, 20)
    pay(client, 21)
    client.post(f"/api/admin/tournament/entrants/{entrant_of(db, 21)['id']}/reject", headers=BOTH)
    assert pay(client, 21).json()["team"]["expires_at"] is None
    later = datetime.now(UTC) + timedelta(hours=ts.RESEND_HOURS + 1)
    monkeypatch.setattr(ts, "now", lambda: later)
    assert (
        client.get("/api/line/tournament", headers=member(21)).json()["team"]["status"]
        == "slip_review"
    )


def test_a_refund_is_the_tournament_s_expense(db: MiniSupabase, client: TestClient) -> None:
    t = open_tournament(client)
    sign_up(client, db, t, 20, 21, "Wine", "ทีมแมว")
    client.post("/api/line/tournament/accept", json=PARTNER, headers=member(21))
    pay(client, 20)
    pay(client, 21)
    for i in (20, 21):
        client.post(
            f"/api/admin/tournament/entrants/{entrant_of(db, i)['id']}/approve", headers=BOTH
        )
    e20, e21 = entrant_of(db, 20), entrant_of(db, 21)
    team_id = e20["team_id"]
    withdrawn = client.post(
        f"/api/admin/tournament/teams/{team_id}/withdraw", json={}, headers=BOTH
    )
    assert withdrawn.status_code == 200

    summary = client.get(
        f"/api/admin/tournament/tournaments/{t['id']}/summary", headers=BOTH
    ).json()
    assert (summary["refunds_owed"], summary["refunds_owed_amount"]) == (2, 2050.0)
    got = client.post(
        f"/api/admin/tournament/entrants/{e20['id']}/refund",
        files={"file": ("refund.png", png(), "image/png")},
        headers=BOTH,
    )
    assert got.status_code == 200, got.text
    assert (
        client.post(f"/api/admin/tournament/entrants/{e20['id']}/refund", headers=BOTH).status_code
        == 409
    )
    client.post(f"/api/admin/tournament/entrants/{e21['id']}/refund", headers=BOTH)
    summary = client.get(
        f"/api/admin/tournament/tournaments/{t['id']}/summary", headers=BOTH
    ).json()
    assert (summary["income"], summary["expense"], summary["balance"]) == (2050.0, 2050.0, 0.0)
    assert summary["refunds_owed"] == 0
    assert all(db.tables[name] == [] for name in CLUB_TABLES)


def test_withdrawn_keeping_the_fees_owes_nothing(db: MiniSupabase, client: TestClient) -> None:
    t = open_tournament(client)
    _fill(client, db, t, "Wine", [(20, 21)])
    team = client.get(f"/api/admin/tournament/tournaments/{t['id']}/teams", headers=BOTH).json()[0]
    got = client.post(
        f"/api/admin/tournament/teams/{team['id']}/withdraw", json={"no_refund": True}, headers=BOTH
    ).json()
    assert got[0]["refund_owed"] == 0


def test_manual_money_and_its_categories(db: MiniSupabase, client: TestClient) -> None:
    t = open_tournament(client)
    url = f"/api/admin/tournament/tournaments/{t['id']}/money"
    court = {
        "direction": "expense",
        "category": "court",
        "amount": 8000,
        "entry_date": "2026-12-20",
    }
    assert client.post(url, json=court, headers=BOTH).status_code == 201
    sponsor = {
        "direction": "income",
        "category": "sponsor",
        "amount": 5000,
        "entry_date": "2026-12-01",
    }
    assert client.post(url, json=sponsor, headers=BOTH).status_code == 201
    # fees are written from the entries, never typed
    fee = {
        "direction": "income",
        "category": "entry_fee",
        "amount": 1025,
        "entry_date": "2026-12-01",
    }
    assert client.post(url, json=fee, headers=BOTH).status_code == 422
    # an expense can't be filed as income
    wrong = {"direction": "income", "category": "court", "amount": 10, "entry_date": "2026-12-01"}
    assert client.post(url, json=wrong, headers=BOTH).status_code == 400
    summary = client.get(
        f"/api/admin/tournament/tournaments/{t['id']}/summary", headers=BOTH
    ).json()
    assert (summary["income"], summary["expense"], summary["balance"]) == (5000.0, 8000.0, -3000.0)
    assert db.tables["expenses"] == [] and db.tables["other_income"] == []


def test_shrinking_a_level_sends_the_last_in_to_the_front_of_the_line(
    db: MiniSupabase, client: TestClient
) -> None:
    t = open_tournament(client)
    url = f"/api/admin/tournament/tournaments/{t['id']}/levels/{level_id(t, 'Soju ขึ้นไป')}"
    client.patch(url, json={"max_teams": 24}, headers=BOTH)
    _fill(client, db, t, "Soju ขึ้นไป", [(i, i + 1) for i in range(0, 36, 2)])  # 18 pairs
    client.patch(url, json={"max_teams": 16}, headers=BOTH)
    teams = client.get(f"/api/admin/tournament/tournaments/{t['id']}/teams", headers=BOTH).json()
    assert [x["status"] for x in teams] == ["confirmed"] * 16 + ["waitlist"] * 2


def test_signing_up_is_closed_after_the_deadline(db: MiniSupabase, client: TestClient) -> None:
    t = open_tournament(client)
    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    opens = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    client.patch(
        f"/api/admin/tournament/tournaments/{t['id']}",
        json={"opens_at": opens, "closes_at": past},
        headers=BOTH,
    )
    assert sign_up(client, db, t, 20, 21, "Wine", "ช้าไป").status_code == 409
    assert client.get("/api/tournament").json()["taking_entries"] is False


def test_no_tournament_reads_as_none(db: MiniSupabase, client: TestClient) -> None:
    assert client.get("/api/tournament").json() is None
    assert client.get("/api/line/tournament", headers=member(1)).json()["tournament"] is None
