from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.billing import Billing, BillingAdjust, BillingMarkPaid
from app.services import billing_service, promptpay_service

router = APIRouter(prefix="/api/admin/billing", tags=["admin-billing"])


class QrResponse(BaseModel):
    data_uri: str


@router.get("", response_model=list[Billing])
def list_billing(session_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> list[Billing]:
    result = supabase.table("billings").select("*").eq("session_id", str(session_id)).execute()
    return [Billing.model_validate(row) for row in rows(result)]


@router.post("/close-session/{session_id}", response_model=list[Billing])
def close_session_and_bill(
    session_id: UUID, supabase: SupabaseDep, admin: AdminDep
) -> list[Billing]:
    """Force-closes any still-open checkins (checkout = now), then upserts a
    billing row per player for this session based on actual checked-in time."""
    session_result = (
        supabase.table("sessions").select("*").eq("id", str(session_id)).limit(1).execute()
    )
    session_rows = rows(session_result)
    if not session_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    rate_per_hour = session_rows[0]["rate_per_hour"]

    now_iso = datetime.now(timezone.utc).isoformat()
    supabase.table("checkins").update({"checkout_time": now_iso}).eq(
        "session_id", str(session_id)
    ).is_("checkout_time", "null").execute()

    checkins_result = (
        supabase.table("checkins").select("*").eq("session_id", str(session_id)).execute()
    )

    billing_rows_to_upsert = []
    for checkin in rows(checkins_result):
        checkin_time = datetime.fromisoformat(str(checkin["checkin_time"]))
        checkout_time = datetime.fromisoformat(str(checkin["checkout_time"]))
        hours_played = billing_service.compute_hours_played(checkin_time, checkout_time)
        amount_calc = billing_service.compute_amount_calc(hours_played, rate_per_hour)
        billing_rows_to_upsert.append(
            {
                "session_id": str(session_id),
                "player_id": checkin["player_id"],
                "hours_played": hours_played,
                "amount_calc": amount_calc,
                "paid_status": "unpaid",
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
