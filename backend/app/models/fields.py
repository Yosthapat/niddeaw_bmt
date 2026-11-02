"""Bounds every admin form shares, so a typo can't reach the database.

A negative court fee bills the whole club a credit; a blank location
leaves a night nobody can pick out of the list; a 3,000-character LINE id
breaks every card it is drawn on. The forms check these first and say why
in Thai — these are the guard for anything that gets past them (an old
cached build, a script, a fat finger on a number pad).
"""

from typing import Annotated, ClassVar, Self

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, model_validator

MAX_BAHT = 1_000_000
"""Far above any one night's fee or one expense, far below a typo's extra
zeros reaching a bill."""

def _to_satang(value: float) -> float:
    """Money is stored as numeric(10, 2), so it is rounded to the satang
    here, where the rule can still be checked against what will be kept."""
    return round(value, 2)


def _some_satang(value: float) -> float:
    """0.004 is more than nothing but is stored as 0.00, which the
    database's `amount > 0` then refuses."""
    if value <= 0:
        raise ValueError("must be at least 0.01")
    return value


Baht = Annotated[float, Field(ge=0, le=MAX_BAHT, allow_inf_nan=False), AfterValidator(_to_satang)]
"""Zero is allowed: a free night or a donated tube is a real entry."""

PositiveBaht = Annotated[
    float, Field(gt=0, le=MAX_BAHT, allow_inf_nan=False), AfterValidator(_to_satang), AfterValidator(_some_satang)
]
"""An expense or income of nothing records nothing."""

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
"""A label a person has to read back: a location, a sponsor."""

Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]

Handle = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
"""A LINE id, TikTok or Instagram handle."""

EloScore = Annotated[int, Field(ge=0, le=4000)]
"""The top tier starts at 2100; anything past 4000 is a typo. The floor is
applied by the router (SCORE_FLOOR), which clamps rather than refuses."""


class EditForm(BaseModel):
    """An edit's body: every field optional, and one left out is kept.

    `null` is not "leave it out", though. Sent for a column that can't be
    empty — a night's location, a member's nickname — it would reach the
    database as nothing, and the request would end in a 500 instead of
    saying what was wrong. Each edit model lists those columns in
    NOT_NULL, and a null for one of them is refused here as a 422.
    """

    NOT_NULL: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _no_null_for_required(self) -> Self:
        nulls = sorted(name for name in self.NOT_NULL & self.model_fields_set if getattr(self, name) is None)
        if nulls:
            raise ValueError(f"cannot be empty: {', '.join(nulls)}")
        return self
