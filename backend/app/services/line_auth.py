"""Checking that an ID token really came from LINE, for this club's channel.

The /line page runs inside LINE (LIFF) and gets an ID token for the person
using it. The page itself can't be trusted to say who that is: anyone can
call our API with any name. LINE's verify endpoint can — it checks the
token's signature, expiry and that it was issued for our LINE Login channel,
and hands back the person's LINE user id (`sub`), display name and picture.

https://developers.line.biz/en/reference/line-login/#verify-id-token
"""

from dataclasses import dataclass

import httpx

from app.config import get_settings

VERIFY_URL = "https://api.line.me/oauth2/v2.1/verify"


class LineAuthError(Exception):
    """The token was refused, or LINE could not be asked."""


@dataclass(frozen=True)
class LineProfile:
    user_id: str
    name: str
    picture: str | None


def configured() -> bool:
    settings = get_settings()
    return bool(settings.line_login_channel_id and settings.line_liff_id)


def verify_id_token(id_token: str, http: httpx.Client | None = None) -> LineProfile:
    channel_id = get_settings().line_login_channel_id
    if not channel_id:
        raise LineAuthError("LINE Login is not set up")
    client = http or httpx.Client(timeout=10)
    try:
        response = client.post(VERIFY_URL, data={"id_token": id_token, "client_id": channel_id})
    except httpx.HTTPError as exc:
        raise LineAuthError("could not reach LINE") from exc
    finally:
        if http is None:
            client.close()
    if response.status_code != 200:
        raise LineAuthError(f"LINE refused the token ({response.status_code})")
    body = response.json()
    sub = body.get("sub")
    if not isinstance(sub, str) or not sub.startswith("U") or len(sub) != 33:
        raise LineAuthError("LINE gave no user id")
    name = str(body.get("name") or "").strip()[:100] or "LINE"
    picture = body.get("picture")
    return LineProfile(
        user_id=sub,
        name=name,
        picture=picture if isinstance(picture, str) and picture.startswith("https://") else None,
    )
