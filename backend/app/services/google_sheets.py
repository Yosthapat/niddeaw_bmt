"""Just enough of the Google Sheets API to keep the club's sheet in step.

Signs in as a Google Cloud service account: the backend signs a short JWT
with the account's private key (RS256, via python-jose, already a
dependency) and trades it for an hour-long access token. No Google client
library — the five calls the sync needs are plain HTTPS.

The service account cannot own files of its own, so the admin creates the
spreadsheet in their own Drive and shares it with the account's email as
an editor. Everything here works inside that one spreadsheet.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
from jose import jwt

SCOPE = "https://www.googleapis.com/auth/spreadsheets"
API = "https://sheets.googleapis.com/v4/spreadsheets"


class SheetsError(Exception):
    """Something the admin can act on, said in Thai. ``kind`` says whose it
    is to fix: "setup" (the key or the sharing) or "request" (this call)."""

    def __init__(self, message: str, kind: str = "request") -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class ServiceAccount:
    email: str
    private_key: str
    key_id: str
    token_uri: str

    @classmethod
    def from_json(cls, raw: str) -> ServiceAccount:
        try:
            info = json.loads(raw)
            return cls(
                email=str(info["client_email"]),
                private_key=str(info["private_key"]),
                key_id=str(info.get("private_key_id", "")),
                token_uri=str(info.get("token_uri") or "https://oauth2.googleapis.com/token"),
            )
        except (ValueError, KeyError, TypeError) as e:
            raise SheetsError(
                "GOOGLE_SERVICE_ACCOUNT_JSON อ่านไม่ได้ — ต้องวางเนื้อหาไฟล์ .json ของ service account ทั้งไฟล์",
                "setup",
            ) from e

    def assertion(self, now: int) -> str:
        """The signed request for a token, valid for the hour Google allows."""
        claims = {
            "iss": self.email,
            "scope": SCOPE,
            "aud": self.token_uri,
            "iat": now,
            "exp": now + 3600,
        }
        headers = {"kid": self.key_id} if self.key_id else None
        return jwt.encode(claims, self.private_key, algorithm="RS256", headers=headers)


_SHEET_ID = re.compile(r"/spreadsheets/d/([A-Za-z0-9_-]+)")


def spreadsheet_id(value: str) -> str:
    """The id from a pasted sheet link, or the id itself."""
    value = value.strip()
    found = _SHEET_ID.search(value)
    if found:
        return found.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{20,}", value):
        return value
    raise SheetsError("SHEETS_SPREADSHEET_ID ไม่ถูกต้อง — ใส่ลิงก์ของ Google Sheet หรือรหัสในลิงก์", "setup")


def a1(title: str, cells: str = "") -> str:
    """A range on a tab, its title quoted the way A1 notation wants."""
    quoted = "'" + title.replace("'", "''") + "'"
    return f"{quoted}!{cells}" if cells else quoted


class SheetsApi:
    def __init__(
        self, account: ServiceAccount, sheet_id: str, http: httpx.Client | None = None
    ) -> None:
        self.account = account
        self.sheet_id = sheet_id
        self.http = http or httpx.Client(timeout=60)
        self._token: str | None = None
        self._token_until = 0.0

    @property
    def url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/edit"

    def _bearer(self) -> str:
        now = time.time()
        if self._token is None or now > self._token_until - 60:
            response = self.http.post(
                self.account.token_uri,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": self.account.assertion(int(now)),
                },
            )
            if response.status_code != 200:
                raise SheetsError(
                    "Google ไม่ให้เข้าสู่ระบบด้วย service account นี้ — ตรวจว่าคีย์ยังใช้ได้"
                    f" ({response.status_code})",
                    "setup",
                )
            body = response.json()
            self._token = str(body["access_token"])
            self._token_until = now + float(body.get("expires_in", 3600))
        return self._token

    def _call(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self.http.request(
            method,
            f"{API}/{self.sheet_id}{path}",
            headers={"Authorization": f"Bearer {self._bearer()}"},
            **kwargs,
        )
        if response.status_code == 403 and (
            "SERVICE_DISABLED" in response.text or "has not been used" in response.text
        ):
            raise SheetsError(
                "ยังไม่ได้เปิด Google Sheets API ในโปรเจกต์ Google Cloud — กด Enable ตามขั้น 2.3 ในคู่มือ",
                "setup",
            )
        if response.status_code in (403, 404):
            raise SheetsError(
                f"เปิด Google Sheet ไม่ได้ — แชร์ชีตให้ {self.account.email} เป็น “ผู้แก้ไข” แล้วหรือยัง"
                f" ({response.status_code})",
                "setup",
            )
        if response.status_code >= 400:
            raise SheetsError(
                f"Google Sheets ตอบกลับผิดพลาด ({response.status_code}): {response.text[:300]}"
            )
        result: dict[str, Any] = response.json() if response.content else {}
        return result

    def tabs(self) -> dict[str, int]:
        """Tab title → sheetId."""
        body = self._call("GET", "", params={"fields": "sheets.properties(sheetId,title)"})
        return {
            s["properties"]["title"]: int(s["properties"]["sheetId"])
            for s in body.get("sheets", [])
        }

    def batch_update(self, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not requests:
            return []
        body = self._call("POST", ":batchUpdate", json={"requests": requests})
        replies: list[dict[str, Any]] = body.get("replies", [])
        return replies

    def clear(self, ranges: list[str]) -> None:
        if ranges:
            self._call("POST", "/values:batchClear", json={"ranges": ranges})

    def write(self, data: list[tuple[str, list[list[Any]]]]) -> None:
        # RAW: what is written is stored as it is. A guest who types
        # "=IMPORTXML(…)" as their name gets that text in a cell, never a
        # formula that runs.
        if data:
            self._call(
                "POST",
                "/values:batchUpdate",
                json={
                    "valueInputOption": "RAW",
                    "data": [{"range": r, "values": v} for r, v in data],
                },
            )

    def append(self, range_: str, values: list[list[Any]]) -> None:
        self._call(
            "POST",
            f"/values/{quote(range_, safe='')}:append",
            params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
            json={"values": values},
        )

    def read(self, range_: str) -> list[list[Any]]:
        body = self._call("GET", f"/values/{quote(range_, safe='')}")
        values: list[list[Any]] = body.get("values", [])
        return values
