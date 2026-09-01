"""Aggregates expenses into monthly summaries, keyed by expense_date's
year-month. Pure function, no I/O — same pattern as revenue_service.py.
"""

from dataclasses import dataclass, field
from typing import TypedDict


class ExpenseRow(TypedDict):
    expense_date: str
    category: str
    amount: float


@dataclass
class MonthlySummary:
    month: str
    total_amount: float = 0.0
    by_category: dict[str, float] = field(default_factory=dict)
    expense_count: int = 0


def build_monthly_summary(expenses: list[ExpenseRow]) -> list[MonthlySummary]:
    summary: dict[str, MonthlySummary] = {}

    for e in expenses:
        month = e["expense_date"][:7]  # "YYYY-MM-DD" -> "YYYY-MM"
        entry = summary.setdefault(month, MonthlySummary(month=month))
        entry.total_amount = round(entry.total_amount + e["amount"], 2)
        entry.by_category[e["category"]] = round(
            entry.by_category.get(e["category"], 0.0) + e["amount"], 2
        )
        entry.expense_count += 1

    return sorted(summary.values(), key=lambda s: s.month, reverse=True)
