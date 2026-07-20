from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.billing import Billing, BillingAdjust, BillingMarkPaid, DailyRevenue
from app.services import billing_service, promptpay_service, revenue_service

router = APIRouter(prefix="/api/admin/billing", tags=["admin-billing"])


class QrResponse(BaseModel):
    data_uri: str


@router.get("", response_model=list[Billing])
def list_billing(session_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> list[Billing]:
    result = supabase.table("billings").select("*").eq("session_id", str(session_id)).execute()
    return [Billing.model_validate(row) for row in rows(result)]


@router.get("/revenue", response_model=list[DailyRevenue])
def get_daily_revenue(supabase: SupabaseDep, admin: AdminDep) -> list[DailyRevenue]:
    """Revenue summary grouped by session date, most recent day first."""
    sessions_result = supabase.table("sessions").select("id, date").execute()
    billings_result = (
        supabase.table("billings")
        .select("session_id, amount_calc, amount_adjusted, paid_status")
        .execute()
    )
    daily = revenue_service.build_daily_revenue(rows(sessions_result), rows(billings_result))  # type: ignore[arg-type]
    return [DailyRevenue.model_validate(vars(entry)) for entry in daily]


@router.post("/close-session/{session_id}", response_model=list[Billing])
def close_session_and_bill(
    session_id: UUID, supabase: SupabaseDep, admin: AdminDep
) -> list[Billing]:
    """Force-closes any still-open checkins (checkout = now, kept for
    attendance/matchmaking history only), then upserts a billing row per
    attendee: a flat court fee plus a flat shuttlecock cost per completed
    game they actually played in this session."""
    session_result = (
        supabase.table("sessions").select("*").eq("id", str(session_id)).limit(1).execute()
    )
    session_rows = rows(session_result)
    if not session_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    court_fee_per_person = session_rows[0]["court_fee_per_person"]
    shuttlecock_price_per_game = session_rows[0]["shuttlecock_price_per_game"]

    now_iso = datetime.now(timezone.utc).isoformat()
    supabase.table("checkins").update({"checkout_time": now_iso}).eq(
        "session_id", str(session_id)
    ).is_("checkout_time", "null").execute()

    checkins_result = (
        supabase.table("checkins").select("player_id").eq("session_id", str(session_id)).execute()
    )
    attendee_ids = {checkin["player_id"] for checkin in rows(checkins_result)}

    matches_result = (
        supabase.table("matches")
        .select("team1_player_ids, team2_player_ids")
        .eq("session_id", str(session_id))
        .eq("status", "completed")
        .execute()
    )
    matches = rows(matches_result)

    billing_rows_to_upsert = []
    for player_id in attendee_ids:
        game_count = billing_service.count_games_played(player_id, matches)
        amount_calc = billing_service.compute_amount_calc(
            game_count, court_fee_per_person, shuttlecock_price_per_game
        )
        billing_rows_to_upsert.append(
            {
                "session_id": str(session_id),
                "player_id": player_id,
                "game_count": game_count,
                "amount_calc": amount_calc,
                # paid_status/amount_adjusted deliberately omitted: on conflict this
                # leaves them untouched, so re-closing (or a player already billed
                # individually via /player/{session_id}/{player_id}) doesn't reset
                # a payment that was already marked paid.
                "updated_at": now_iso,
            }
        )

    if billing_rows_to_upsert:
        supabase.table("billings").upsert(
            billing_rows_to_upsert, on_conflict="session_id,player_id"
        ).execute()

    supabase.table("sessions").update({"status": "closed"}).eq("id", str(session_id)).execute()

    result = supabase.table("billings").select("*").eq("session_id", str(session_id)).execute()
    return [Billing.model_validate(row) for row in rows(result)]


@router.post("/player/{session_id}/{player_id}", response_model=Billing)
def bill_player(
    session_id: UUID, player_id: UUID, supabase: SupabaseDep, admin: AdminDep
) -> Billing:
    """Bills a single attendee immediately, independent of session status —
    e.g. they checked out early and shouldn't have to wait for everyone
    else to finish. Doesn't touch the session's status or other players."""
    session_result = (
        supabase.table("sessions").select("*").eq("id", str(session_id)).limit(1).execute()
    )
    session_rows = rows(session_result)
    if not session_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    court_fee_per_person = session_rows[0]["court_fee_per_person"]
    shuttlecock_price_per_game = session_rows[0]["shuttlecock_price_per_game"]

    matches_result = (
        supabase.table("matches")
        .select("team1_player_ids, team2_player_ids")
        .eq("session_id", str(session_id))
        .eq("status", "completed")
        .execute()
    )
    game_count = billing_service.count_games_played(str(player_id), rows(matches_result))
    amount_calc = billing_service.compute_amount_calc(
        game_count, court_fee_per_person, shuttlecock_price_per_game
    )

    result = (
        supabase.table("billings")
        .upsert(
            {
                "session_id": str(session_id),
                "player_id": str(player_id),
                "game_count": game_count,
                "amount_calc": amount_calc,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="session_id,player_id",
        )
        .execute()
    )
    return Billing.model_validate(rows(result)[0])


@router.patch("/{billing_id}/adjust", response_model=Billing)
def adjust_amount(
    billing_id: UUID, payload: BillingAdjust, supabase: SupabaseDep, admin: AdminDep
) -> Billing:
    result = (
        supabase.table("billings")
        .update(
            {
                "amount_adjusted": payload.amount_adjusted,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", str(billing_id))
        .execute()
    )
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing row not found")
    return Billing.model_validate(result_rows[0])


@router.patch("/{billing_id}/paid-status", response_model=Billing)
def set_paid_status(
    billing_id: UUID, payload: BillingMarkPaid, supabase: SupabaseDep, admin: AdminDep
) -> Billing:
    result = (
        supabase.table("billings")
        .update(
            {
                "paid_status": payload.paid_status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", str(billing_id))
        .execute()
    )
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing row not found")
    return Billing.model_validate(result_rows[0])


@router.get("/{billing_id}/qr", response_model=QrResponse)
def get_promptpay_qr(billing_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> QrResponse:
    billing_result = (
        supabase.table("billings").select("*").eq("id", str(billing_id)).limit(1).execute()
    )
    billing_rows = rows(billing_result)
    if not billing_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing row not found")
    billing = Billing.model_validate(billing_rows[0])

    settings_result = supabase.table("club_settings").select("*").eq("id", 1).limit(1).execute()
    settings_rows = rows(settings_result)
    if not settings_rows or not settings_rows[0]["promptpay_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PromptPay ID not configured — set it in Admin > Settings first",
        )
    club_settings = settings_rows[0]

    payload = promptpay_service.build_promptpay_payload(
        club_settings["promptpay_id"],
        club_settings["promptpay_type"],
        billing.effective_amount,
    )
    return QrResponse(data_uri=promptpay_service.generate_qr_data_uri(payload))
