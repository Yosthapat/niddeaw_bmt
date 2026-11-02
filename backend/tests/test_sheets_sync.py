"""The weekly Google Sheets copy, end to end against a fake Sheets API.

The fake keeps the rules the real one enforces and a sync could trip on:
a write must fit the tab's grid (a new tab is 1000×26), a tab's only row
cannot be frozen, the last tab cannot be deleted, a range on a missing tab
is a bad request, and every call needs the token the sign-in handed out.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, unquote

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.routers.admin import sheets as sheets_router
from app.security import create_access_token
from app.services import sheets_sync
from app.services.google_sheets import ServiceAccount, SheetsApi, SheetsError, a1, spreadsheet_id
from app.services.shop_service import CLUB_TZ
from tests.conftest import FakeSupabase

SHEET = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"
EMAIL = "club-sync@niddeaw.iam.gserviceaccount.com"
TOKEN_URI = "https://oauth2.googleapis.com/token"

_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_PEM = _key.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()
PUBLIC_PEM = (
    _key.public_key()
    .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    .decode()
)
KEY_JSON = json.dumps(
    {
        "type": "service_account",
        "client_email": EMAIL,
        "private_key": PRIVATE_PEM,
        "private_key_id": "k1",
        "token_uri": TOKEN_URI,
    }
)


class Tab:
    def __init__(self, sheet_id: int, title: str) -> None:
        self.id = sheet_id
        self.title = title
        self.rows = 1000
        self.cols = 26
        self.frozen = 0
        self.values: list[list[Any]] = []


def _range(text: str) -> tuple[str, str]:
    found = re.fullmatch(r"'((?:[^']|'')*)'(?:!(.*))?", text)
    assert found, f"not a quoted A1 range: {text!r}"
    return found.group(1).replace("''", "'"), found.group(2) or ""


class FakeGoogle:
    """A spreadsheet that starts, like a new one, with a single empty tab."""

    def __init__(self) -> None:
        self.tabs: list[Tab] = [Tab(0, "ชีต1")]
        self.next_id = 100
        self.tokens_issued = 0
        self.token = ""
        self.deny: bool | str = False

    def tab(self, title: str) -> Tab:
        return next(t for t in self.tabs if t.title == title)

    def titles(self) -> list[str]:
        return [t.title for t in self.tabs]

    def _error(self, code: int, message: str) -> httpx.Response:
        return httpx.Response(code, json={"error": {"code": code, "message": message}})

    def handle(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == TOKEN_URI:
            form = parse_qs(request.content.decode())
            assert form["grant_type"] == ["urn:ietf:params:oauth:grant-type:jwt-bearer"]
            claims = jwt.decode(
                form["assertion"][0], PUBLIC_PEM, algorithms=["RS256"], audience=TOKEN_URI
            )
            assert (
                claims["iss"] == EMAIL
                and claims["scope"] == "https://www.googleapis.com/auth/spreadsheets"
            )
            self.tokens_issued += 1
            self.token = f"tok-{self.tokens_issued}"
            return httpx.Response(200, json={"access_token": self.token, "expires_in": 3599})
        assert request.headers["authorization"] == f"Bearer {self.token}"
        if self.deny == "api-off":
            return self._error(
                403, "Google Sheets API has not been used in project 123 before or it is disabled."
            )
        if self.deny:
            return self._error(403, "The caller does not have permission")
        prefix = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET}"
        assert url.startswith(prefix), url
        path = unquote(request.url.raw_path.decode().split("?")[0])[
            len(f"/v4/spreadsheets/{SHEET}") :
        ]
        body = json.loads(request.content) if request.content else {}

        if request.method == "GET" and path == "":
            return httpx.Response(
                200,
                json={
                    "sheets": [
                        {"properties": {"sheetId": t.id, "title": t.title}} for t in self.tabs
                    ]
                },
            )
        if path == ":batchUpdate":
            replies: list[dict[str, Any]] = []
            for r in body["requests"]:
                if "addSheet" in r:
                    props = r["addSheet"]["properties"]
                    if props["title"] in self.titles():
                        return self._error(400, "A sheet with that name already exists")
                    index = props.get("index", len(self.tabs))
                    if index > len(self.tabs):
                        return self._error(400, "index out of range")
                    tab = Tab(self.next_id, props["title"])
                    self.next_id += 1
                    self.tabs.insert(index, tab)
                    replies.append(
                        {
                            "addSheet": {
                                "properties": {
                                    "sheetId": tab.id,
                                    "title": tab.title,
                                    "index": index,
                                }
                            }
                        }
                    )
                elif "updateSheetProperties" in r:
                    props = r["updateSheetProperties"]["properties"]
                    tab = next(t for t in self.tabs if t.id == props["sheetId"])
                    grid = props["gridProperties"]
                    if grid["frozenRowCount"] >= grid["rowCount"]:
                        return self._error(400, "You can't freeze all visible rows on the sheet.")
                    tab.rows, tab.cols, tab.frozen = (
                        grid["rowCount"],
                        grid["columnCount"],
                        grid["frozenRowCount"],
                    )
                    tab.values = [row[: tab.cols] for row in tab.values[: tab.rows]]
                    replies.append({})
                elif "deleteSheet" in r:
                    if len(self.tabs) == 1:
                        return self._error(400, "You can't remove all the sheets in a document.")
                    self.tabs = [t for t in self.tabs if t.id != r["deleteSheet"]["sheetId"]]
                    replies.append({})
            return httpx.Response(200, json={"replies": replies})
        if path == "/values:batchClear":
            for text in body["ranges"]:
                self.tab(_range(text)[0]).values = []
            return httpx.Response(200, json={})
        if path == "/values:batchUpdate":
            assert body["valueInputOption"] == "RAW"
            for item in body["data"]:
                title, cells = _range(item["range"])
                assert cells == "A1"
                tab = self.tab(title)
                if (
                    len(item["values"]) > tab.rows
                    or max((len(v) for v in item["values"]), default=0) > tab.cols
                ):
                    return self._error(400, f"Range ('{title}'!A1) exceeds grid limits.")
                tab.values = [list(v) for v in item["values"]]
            return httpx.Response(200, json={})
        found = re.fullmatch(r"/values/(.+):append", path)
        if found and request.method == "POST":
            assert request.url.params["valueInputOption"] == "RAW"
            tab = self.tab(_range(found.group(1))[0])
            tab.values.extend(body["values"])
            tab.rows = max(tab.rows, len(tab.values))
            return httpx.Response(200, json={})
        found = re.fullmatch(r"/values/(.+)", path)
        if found and request.method == "GET":
            title = _range(found.group(1))[0]
            if title not in self.titles():
                return self._error(400, f"Unable to parse range: {found.group(1)}")
            return httpx.Response(200, json={"values": self.tab(title).values})
        raise AssertionError(f"unexpected call {request.method} {path}")


def make_api(google: FakeGoogle) -> SheetsApi:
    http = httpx.Client(transport=httpx.MockTransport(google.handle))
    return SheetsApi(ServiceAccount.from_json(KEY_JSON), SHEET, http)


def club(players: int = 3) -> FakeSupabase:
    return FakeSupabase(
        {
            "players": [
                {
                    "id": f"p{i}",
                    "nickname": f"เล่น{i}",
                    "elo_score": 1000 + i,
                    "is_active": True,
                    "quote": None,
                }
                for i in range(players)
            ],
            "shop_orders": [
                {"id": "o1", "guest_name": '=IMPORTXML("x")', "total": 520.5, "status": "pending"}
            ],
            "admin_activity_log": [{"id": "l1", "detail": {"items": ["เสื้อ M × 2"]}}],
            "admins": [{"id": "a1", "username": "Vaan", "password_hash": "$2b$12$secret"}],
        }
    )


NOW = datetime(2026, 11, 7, 3, 23, tzinfo=CLUB_TZ)


def test_a_first_sync_lays_out_the_whole_sheet() -> None:
    google = FakeGoogle()
    result = sheets_sync.sync(club(), make_api(google), NOW, "Vaan")  # type: ignore[arg-type]

    titles = google.titles()
    assert titles[0] == "ประวัติซิงก์"
    assert titles[1 : 1 + len(sheets_sync.TAB_TITLES)] == list(sheets_sync.TAB_TITLES.values())
    assert "สำรอง 2026-11-07" in titles
    players = google.tab("สมาชิก")
    assert players.values[0] == ["id", "nickname", "elo_score", "is_active", "quote"]
    # Numbers and true/false stay themselves, so the sheet can sum them.
    assert players.values[1] == ["p0", "เล่น0", 1000, True, ""]
    assert (players.rows, players.cols, players.frozen) == (4, 5, 1)
    orders = google.tab("ออเดอร์")
    assert orders.values[1][1] == '=IMPORTXML("x")'  # stored as text: RAW, never a formula
    assert orders.values[1][2] == 520.5
    assert google.tab("ประวัติแอดมิน").values[1][1] == '{"items": ["เสื้อ M × 2"]}'
    # An empty table still gets a tab that says so — and its single row is
    # not frozen into an error.
    assert google.tab("รอบเล่น").values == [["ยังไม่มีข้อมูล"]]
    assert google.tab("ประวัติซิงก์").values == [
        ["เวลา (ไทย)", "ซิงก์โดย", "จำนวนแถว", "แท็บสำรอง"],
        ["2026-11-07 03:23", "Vaan", 6, "สำรอง 2026-11-07"],
    ]
    assert result.rows == 6 and result.url == f"https://docs.google.com/spreadsheets/d/{SHEET}/edit"


def test_password_hashes_never_reach_the_sheet() -> None:
    google = FakeGoogle()
    sheets_sync.sync(club(), make_api(google), NOW, "Vaan")  # type: ignore[arg-type]
    dumped = json.dumps([t.values for t in google.tabs], ensure_ascii=False)
    assert "secret" not in dumped and "password_hash" not in dumped


def test_the_snapshot_stacks_every_table() -> None:
    google = FakeGoogle()
    sheets_sync.sync(club(), make_api(google), NOW, "Vaan")  # type: ignore[arg-type]
    snap = google.tab("สำรอง 2026-11-07").values
    headings = [row[0] for row in snap if row and str(row[0]).startswith("■")]
    assert len(headings) == len(sheets_sync.TAB_TITLES)
    assert "■ สมาชิก (players) — 3 แถว" in headings
    at = snap.index(["■ สมาชิก (players) — 3 แถว"])
    assert snap[at + 1][1] == "nickname" and snap[at + 2][1] == "เล่น0"


def test_a_smaller_table_leaves_no_old_rows_behind() -> None:
    google = FakeGoogle()
    api = make_api(google)
    sheets_sync.sync(club(players=5), api, NOW, "Vaan")  # type: ignore[arg-type]
    sheets_sync.sync(club(players=2), api, NOW + timedelta(days=7), "Vaan")  # type: ignore[arg-type]
    players = google.tab("สมาชิก")
    assert len(players.values) == 3 and players.rows == 3


def test_a_big_table_grows_past_a_new_tabs_thousand_rows() -> None:
    google = FakeGoogle()
    sheets_sync.sync(club(players=1500), make_api(google), NOW, "Vaan")  # type: ignore[arg-type]
    assert len(google.tab("สมาชิก").values) == 1501


def test_old_snapshots_are_kept_eight_weeks_and_never_overwritten() -> None:
    google = FakeGoogle()
    api = make_api(google)
    sheets_sync.sync(club(players=1), api, NOW, "Vaan")  # type: ignore[arg-type]
    first = [list(r) for r in google.tab("สำรอง 2026-11-07").values]
    for week in range(1, 8):
        sheets_sync.sync(club(players=1 + week), api, NOW + timedelta(days=7 * week), "อัตโนมัติ")  # type: ignore[arg-type]
    # Eight weeks in, the first week's copy is still exactly what it was.
    assert google.tab("สำรอง 2026-11-07").values == first
    result = sheets_sync.sync(club(), api, NOW + timedelta(days=56), "อัตโนมัติ")  # type: ignore[arg-type]
    snaps = [t for t in google.titles() if t.startswith("สำรอง ")]
    assert len(snaps) == 8 and "สำรอง 2026-11-07" not in snaps
    assert result.removed_snapshots == ["สำรอง 2026-11-07"]
    assert len(google.tab("ประวัติซิงก์").values) == 1 + 9


def test_syncing_twice_in_a_day_updates_that_days_copy() -> None:
    google = FakeGoogle()
    api = make_api(google)
    sheets_sync.sync(club(players=1), api, NOW, "Vaan")  # type: ignore[arg-type]
    sheets_sync.sync(club(players=4), api, NOW + timedelta(hours=2), "Vaan")  # type: ignore[arg-type]
    assert [t for t in google.titles() if t.startswith("สำรอง ")] == ["สำรอง 2026-11-07"]
    assert "■ สมาชิก (players) — 4 แถว" in [r[0] for r in google.tab("สำรอง 2026-11-07").values if r]


def test_the_sign_in_is_reused_within_the_hour() -> None:
    google = FakeGoogle()
    api = make_api(google)
    sheets_sync.sync(club(), api, NOW, "Vaan")  # type: ignore[arg-type]
    sheets_sync.sync(club(), api, NOW, "Vaan")  # type: ignore[arg-type]
    assert google.tokens_issued == 1


def test_an_unshared_sheet_says_whom_to_share_it_with() -> None:
    google = FakeGoogle()
    google.deny = True
    with pytest.raises(SheetsError) as caught:
        sheets_sync.sync(club(), make_api(google), NOW, "Vaan")  # type: ignore[arg-type]
    assert caught.value.kind == "setup" and EMAIL in str(caught.value)


def test_last_sync_before_and_after() -> None:
    google = FakeGoogle()
    api = make_api(google)
    with pytest.raises(SheetsError):
        sheets_sync.last_sync(api)  # no log tab yet: Google calls the range bad
    sheets_sync.sync(club(), api, NOW, "Vaan")  # type: ignore[arg-type]
    assert sheets_sync.last_sync(api) == ["2026-11-07 03:23", "Vaan", 6, "สำรอง 2026-11-07"]


@pytest.mark.parametrize(
    "pasted",
    [
        SHEET,
        f"https://docs.google.com/spreadsheets/d/{SHEET}/edit#gid=0",
        f" https://docs.google.com/spreadsheets/d/{SHEET}/edit?usp=sharing ",
    ],
)
def test_the_sheet_can_be_given_as_its_link(pasted: str) -> None:
    assert spreadsheet_id(pasted) == SHEET


def test_setup_mistakes_are_named() -> None:
    with pytest.raises(SheetsError) as bad_key:
        ServiceAccount.from_json('{"client_email": "x"}')
    assert bad_key.value.kind == "setup" and "GOOGLE_SERVICE_ACCOUNT_JSON" in str(bad_key.value)
    with pytest.raises(SheetsError) as bad_sheet:
        spreadsheet_id("my sheet")
    assert bad_sheet.value.kind == "setup"


def test_a1_quotes_titles() -> None:
    assert a1("สมาชิก", "A1") == "'สมาชิก'!A1"
    assert a1("it's", "A:D") == "'it''s'!A:D"


# ---------------------------------------------------------------- endpoints


def auth() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(admin_id='00000000-0000-0000-0000-0000000000a1', role='admin')}"
    }


class Settings:
    def __init__(self, secret: str | None = None) -> None:
        self.sheets_sync_secret = secret


@pytest.fixture
def linked(
    supabase_rows: dict[str, list[dict[str, Any]]], monkeypatch: pytest.MonkeyPatch
) -> Iterator[FakeGoogle]:
    google = FakeGoogle()
    api = make_api(google)
    app.dependency_overrides[sheets_router.load_sheets] = lambda: sheets_router.SheetsLink(
        api, True, True, EMAIL, None
    )
    monkeypatch.setattr(sheets_router, "get_settings", lambda: Settings("s3cret-weekly"))
    supabase_rows["players"] = [{"id": "p1", "nickname": "Tan"}]
    supabase_rows["admins"] = [{"username": "Vaan"}]
    yield google
    app.dependency_overrides.pop(sheets_router.load_sheets, None)


def test_status_when_nothing_is_set_up(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class Unset:
        google_service_account_json = None
        sheets_spreadsheet_id = None
        sheets_sync_secret = None

    monkeypatch.setattr(sheets_router, "get_settings", lambda: Unset())
    body = client.get("/api/admin/sheets", headers=auth()).json()
    assert body == {
        "has_key": False,
        "has_sheet": False,
        "account_email": None,
        "sheet_url": None,
        "weekly": False,
        "problem": None,
        "last": None,
    }
    response = client.post("/api/admin/sheets/sync", headers=auth())
    assert response.status_code == 409 and "ยังไม่ได้เชื่อม" in response.json()["detail"]


def test_status_shows_whom_to_share_with_once_the_key_is_in(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class KeyOnly:
        google_service_account_json = KEY_JSON
        sheets_spreadsheet_id = None
        sheets_sync_secret = None

    monkeypatch.setattr(sheets_router, "get_settings", lambda: KeyOnly())
    body = client.get("/api/admin/sheets", headers=auth()).json()
    assert body["has_key"] and not body["has_sheet"] and body["account_email"] == EMAIL


def test_an_admin_syncs_and_it_is_logged(client: TestClient, linked: FakeGoogle) -> None:
    assert client.post("/api/admin/sheets/sync").status_code == 401
    before = client.get("/api/admin/sheets", headers=auth()).json()
    assert before["last"] is None and before["problem"] is None and before["weekly"] is True
    done = client.post("/api/admin/sheets/sync", headers=auth())
    assert done.status_code == 200
    assert done.json()["rows"] == 2
    assert linked.tab("ประวัติซิงก์").values[-1][1] == "Vaan"
    after = client.get("/api/admin/sheets", headers=auth()).json()
    assert after["last"]["by"] == "Vaan" and after["last"]["rows"] == 2
    assert after["sheet_url"] == f"https://docs.google.com/spreadsheets/d/{SHEET}/edit"


def test_a_sheet_google_refuses_reads_as_a_setup_problem(
    client: TestClient, linked: FakeGoogle
) -> None:
    linked.deny = True
    assert EMAIL in client.get("/api/admin/sheets", headers=auth()).json()["problem"]
    response = client.post("/api/admin/sheets/sync", headers=auth())
    assert response.status_code == 502 and EMAIL in response.json()["detail"]


def test_the_weekly_sync_answers_only_to_its_secret(client: TestClient, linked: FakeGoogle) -> None:
    assert client.post("/api/internal/sheets-sync").status_code == 403
    assert (
        client.post("/api/internal/sheets-sync", headers={"X-Sync-Secret": "guess"}).status_code
        == 403
    )
    response = client.post("/api/internal/sheets-sync", headers={"X-Sync-Secret": "s3cret-weekly"})
    assert response.status_code == 200
    assert linked.tab("ประวัติซิงก์").values[-1][1] == sheets_router.WEEKLY


def test_the_weekly_sync_does_not_exist_without_a_secret(
    client: TestClient, linked: FakeGoogle, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sheets_router, "get_settings", lambda: Settings(None))
    assert (
        client.post("/api/internal/sheets-sync", headers={"X-Sync-Secret": ""}).status_code == 404
    )


def test_an_api_left_switched_off_is_told_apart_from_an_unshared_sheet() -> None:
    google = FakeGoogle()
    google.deny = "api-off"
    with pytest.raises(SheetsError) as caught:
        sheets_sync.sync(club(), make_api(google), NOW, "Vaan")  # type: ignore[arg-type]
    assert (
        caught.value.kind == "setup"
        and "Enable" in str(caught.value)
        and EMAIL not in str(caught.value)
    )
