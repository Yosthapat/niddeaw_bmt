"""Billing math: hours-played derivation and effective-amount resolution.

Pure functions — no Supabase I/O — so the rounding/grace-period rule can be
unit-tested directly.
"""

import math
from datetime import datetime

GRACE_MINUTES = 5
BILLING_BLOCK_MINUTES = 30


def compute_billed_minutes(checkin_time: datetime, checkout_time: datetime) -> int:
    raw_minutes = (checkout_time - checkin_time).total_seconds() / 60
    grace_adjusted = max(raw_minutes - GRACE_MINUTES, 0)
    blocks = math.ceil(grace_adjusted / BILLING_BLOCK_MINUTES)
    return blocks * BILLING_BLOCK_MINUTES


def compute_hours_played(checkin_time: datetime, checkout_time: datetime) -> float:
    return compute_billed_minutes(checkin_time, checkout_time) / 60


def compute_amount_calc(hours_played: float, rate_per_hour: float) -> float:
    return round(hours_played * rate_per_hour, 2)


def effective_amount(amount_calc: float, amount_adjusted: float | None) -> float:
    return amount_adjusted if amount_adjusted is not None else amount_calc
