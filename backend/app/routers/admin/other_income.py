from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.other_income import OtherIncome, OtherIncomeCreate, OtherIncomeUpdate

router = APIRouter(prefix="/api/admin/income", tags=["admin-income"])


@router.get("", response_model=list[OtherIncome])
def list_income(supabase: SupabaseDep, admin: AdminDep) -> list[OtherIncome]:
    """Non-billing revenue (sponsor payments, investment injections, etc.),
    most recent first — full history, no month filter, since these are
    expected to be sparse compared to billings."""
    result = supabase.table("other_income").select("*").order("income_date", desc=True).execute()
    return [OtherIncome.model_validate(row) for row in rows(result)]


@router.post("", response_model=OtherIncome, status_code=status.HTTP_201_CREATED)
def create_income(payload: OtherIncomeCreate, supabase: SupabaseDep, admin: AdminDep) -> OtherIncome:
    row = {**payload.model_dump(mode="json"), "created_by": str(admin.admin_id)}
    result = supabase.table("other_income").insert(row).execute()
    return OtherIncome.model_validate(rows(result)[0])


@router.patch("/{income_id}", response_model=OtherIncome)
def update_income(
    income_id: UUID, payload: OtherIncomeUpdate, supabase: SupabaseDep, admin: AdminDep
) -> OtherIncome:
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    result = supabase.table("other_income").update(updates).eq("id", str(income_id)).execute()
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income entry not found")
    return OtherIncome.model_validate(result_rows[0])


@router.delete("/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income(income_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> None:
    result = supabase.table("other_income").delete().eq("id", str(income_id)).execute()
    if not rows(result):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income entry not found")
