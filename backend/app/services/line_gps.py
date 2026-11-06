"""Checking in by where the phone is: tonight's pin and the distance to it.

An admin pins the court from their phone at the start of the night. A
member's phone reports where it is and how sure it is (accuracy, metres).
Indoors a phone is often 20–60 m out, so the circle is given a little
slack, up to SLACK_CAP_M, for a phone that says it is unsure; a phone that
is very unsure (over MAX_ACCURACY_M) checks nobody in and is asked to try
again or scan the QR instead.
"""

import math
from typing import Any

from supabase import Client

from app.db_utils import rows
from app.services.line_checkin import is_current

EARTH_RADIUS_M = 6_371_000
MAX_ACCURACY_M = 300
SLACK_CAP_M = 50


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres (haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def inside(distance: float, radius: int, accuracy: float) -> bool:
    return distance <= radius + min(accuracy, SLACK_CAP_M)


def nearest_night(supabase: Client, lat: float, lng: float) -> tuple[dict[str, Any], float] | None:
    """The open, pinned night nearest to this phone, and how far it is."""
    open_nights = rows(supabase.table("sessions").select("*").eq("status", "open").execute())
    best: tuple[dict[str, Any], float] | None = None
    for night in open_nights:
        if not is_current(night) or night.get("checkin_lat") is None:
            continue
        d = distance_m(lat, lng, float(night["checkin_lat"]), float(night["checkin_lng"]))
        if best is None or d < best[1]:
            best = (night, d)
    return best
