"""Aggregates billings into daily revenue summaries, keyed by the
session's date (not the billing row's updated_at) — a session represents
one day of club play, so that's the natural grouping for "how much did we
make on this day."

Pure function, no I/O — the router fetches sessions/billings and passes
plain dicts in, matching the pattern in stats_service.py.
"""

from dataclasses import dataclass
from datetime import date as date_type
from typing import TypedDict

from app.services import billing_service


class SessionRow(TypedDict):
    id: str
    date: str


class BillingRow(TypedDict):
    session_id: str
    amount_calc: float
    amount_adjusted: float | None
    paid_status: str


@dataclass
class DailyRevenue:
    date: date_type
    total_amount: float = 0.0
    paid_amount: float = 0.0
    unpaid_amount: float = 0.0
    session_count: int = 0
    billing_count: int = 0


def build_daily_revenue(
    sessions: list[SessionRow], billings: list[BillingRow]
) -> list[DailyRevenue]:
    date_by_session: dict[str, date_type] = {
        s["id"]: date_type.fromisoformat(s["date"]) for s in sessions
    }
    summary: dict[date_type, DailyRevenue] = {}
    sessions_seen_by_date: dict[date_type, set[str]] = {}

    for b in billings:
        session_date = date_by_session.get(b["session_id"])
        if session_date is None:
            continue
        entry = summary.setdefault(session_date, DailyRevenue(date=session_date))
        amount = billing_service.effective_amount(b["amount_calc"], b["amount_adjusted"])
        entry.total_amount = round(entry.total_amount + amount, 2)
        if b["paid_status"] == "paid":
            entry.paid_amount = round(entry.paid_amount + amount, 2)
        else:
            entry.unpaid_amount = round(entry.unpaid_amount + amount, 2)
        entry.billing_count += 1
        sessions_seen_by_date.setdefault(session_date, set()).add(b["session_id"])

    for session_date, entry in summary.items():
        entry.session_count = len(sessions_seen_by_date[session_date])

    return sorted(summary.values(), key=lambda e: e.date, reverse=True)
