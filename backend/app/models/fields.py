"""Bounds every admin form shares, so a typo can't reach the database.

A negative court fee bills the whole club a credit; a blank location
leaves a night nobody can pick out of the list; a 3,000-character LINE id
breaks every card it is drawn on. The forms check these first and say why
in Thai — these are the guard for anything that gets past them (an old
cached build, a script, a fat finger on a number pad).
"""

from typing import Annotated

from pydantic import Field, StringConstraints

MAX_BAHT = 1_000_000
"""Far above any one night's fee or one expense, far below a typo's extra
zeros reaching a bill."""

Baht = Annotated[float, Field(ge=0, le=MAX_BAHT, allow_inf_nan=False)]
"""Zero is allowed: a free night or a donated tube is a real entry."""

PositiveBaht = Annotated[float, Field(gt=0, le=MAX_BAHT, allow_inf_nan=False)]
"""An expense or income of nothing records nothing."""

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
"""A label a person has to read back: a location, a sponsor."""

Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]

Handle = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
"""A LINE id, TikTok or Instagram handle."""

EloScore = Annotated[int, Field(ge=0, le=4000)]
"""The top tier starts at 2100; anything past 4000 is a typo. The floor is
applied by the router (SCORE_FLOOR), which clamps rather than refuses."""
