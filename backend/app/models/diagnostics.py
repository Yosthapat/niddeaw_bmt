"""What the login throttle sees when a caller arrives."""

from __future__ import annotations

from pydantic import BaseModel


class ClientIdentity(BaseModel):
    """Answers one question: do two different people get two different keys?

    The admin login is throttled per caller, and the caller is identified
    by the rightmost X-Forwarded-For hop — the one our own edge observed
    and the only one a client cannot write for itself. That is right when
    exactly one proxy sits in front of the app, which is how Render is
    meant to serve it. Behind two, every caller keys to the inner proxy's
    address instead and the whole club shares one budget: five wrong
    passwords from anyone would lock everyone out for fifteen minutes.

    Which of those is true is a fact about the deployment, not about this
    code, so it has to be read off the real thing. Open this from a phone
    on mobile data and from a laptop on wifi: two different `throttle_key`
    values mean the throttle is per-caller as intended.
    """

    forwarded_for: str | None
    hops: list[str]
    peer: str | None
    throttle_key: str
    recent_failures: int
    retry_after_seconds: int
