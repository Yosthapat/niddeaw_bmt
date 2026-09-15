"""Per-caller throttle for the admin login endpoint.

The panel is on the public internet and `POST /api/admin/auth/login` had no
limit of any kind, so a script could work through a password list at
whatever rate the box would answer. Nothing else stood in the way either:
the API is served from Render directly rather than behind Cloudflare, so
there is no edge rule to fall back on.

State is a module-level dict — deliberately, for a single-instance free-tier
service. It resets on deploy and on the daily cold start, which costs an
attacker nothing they couldn't get by waiting, and saves adding a Redis to
a club app. If the backend is ever scaled past one instance this stops
being a real limit and needs shared state.
"""

from collections import deque
from time import monotonic

# Five wrong passwords is already far more than a person who knows theirs
# needs, and well under what a list attack requires.
MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60

# caller key -> timestamps of their recent failures, oldest first
_failures: dict[str, deque[float]] = {}


def client_key(forwarded_for: str | None, peer: str | None) -> str:
    """Identifies the caller for throttling.

    Takes the **rightmost** X-Forwarded-For entry, not the leftmost. Each
    proxy appends the address it received the connection from, so the last
    entry is the one our own edge observed and the only one the caller
    cannot write themselves — a client that sends its own X-Forwarded-For
    just adds a value to the left of it. Reading the leftmost would let an
    attacker rotate a header field instead of an IP and walk straight
    through this.

    Assumes exactly one proxy in front of the app, which is how Render
    serves it. Behind two, every caller would key to the inner proxy's
    address and share one budget.
    """
    if forwarded_for:
        hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
        if hops:
            return hops[-1]
    return peer or "unknown"


def _recent(key: str, now: float) -> deque[float]:
    attempts = _failures.get(key)
    if attempts is None:
        return deque()
    while attempts and now - attempts[0] >= WINDOW_SECONDS:
        attempts.popleft()
    if not attempts:
        _failures.pop(key, None)
    return attempts


def retry_after_seconds(key: str) -> int:
    """0 when the caller may try again, else how long until they may.

    Counts down as the window slides, so the answer is what to put in
    Retry-After rather than a flat "come back in fifteen minutes".
    """
    now = monotonic()
    attempts = _recent(key, now)
    if len(attempts) < MAX_FAILURES:
        return 0
    return max(1, int(WINDOW_SECONDS - (now - attempts[0])) + 1)


def record_failure(key: str) -> None:
    now = monotonic()
    attempts = _recent(key, now)
    attempts.append(now)
    _failures[key] = attempts


def clear(key: str) -> None:
    """Called on a successful login: whoever it was knows the password, so
    the failures before it were their own typing, not an attack."""
    _failures.pop(key, None)


def reset_all() -> None:
    """Test seam — module-level state would otherwise leak between tests."""
    _failures.clear()
