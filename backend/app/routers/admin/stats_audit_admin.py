"""Checking every profile's record against the matches, from inside the app.

The same audit as tools/recount_stats.py, which needs a terminal and the
service-role key — neither of which is at the court on a Friday night. The
numbers on a profile are counters (migration 0011), the matches are the
truth, and when they disagree the person who notices is the admin looking
at the screen. This lets them look, and repair.
"""

from fastapi import APIRouter

from app.deps import AdminDep, SupabaseDep
from app.models.maintenance import StatsReport
from app.services import stats_audit

router = APIRouter(prefix="/api/admin/stats-audit", tags=["admin-stats-audit"])


@router.get("", response_model=StatsReport)
def check(supabase: SupabaseDep, admin: AdminDep) -> StatsReport:
    """Who disagrees with their own match history. Writes nothing."""
    return stats_audit.audit(supabase, apply=False)


@router.post("/repair", response_model=StatsReport)
def repair(supabase: SupabaseDep, admin: AdminDep) -> StatsReport:
    """Writes each player the record their matches support.

    An overwrite, not an adjustment, so running it twice changes nothing
    the second time. ELO is never written: a rating depends on the order
    its matches were played in and on the ratings at the time, so it cannot
    be recomputed from the same rows.
    """
    return stats_audit.audit(supabase, apply=True)
