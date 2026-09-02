from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.admin import Admin
from app.models.expense import Expense, ExpenseCreate, ExpenseUpdate, MonthlyExpenseSummary
from app.services import expense_service

router = APIRouter(prefix="/api/admin/expenses", tags=["admin-expenses"])

RECEIPT_BUCKET = "receipts"
MAX_RECEIPT_BYTES = 5 * 1024 * 1024  # 5MB — full receipt photos run bigger than avatars


@router.get("", response_model=list[Expense])
def list_expenses(supabase: SupabaseDep, admin: AdminDep, month: str | None = None) -> list[Expense]:
    """`month` filters to a "YYYY-MM" — omit it to get the full history."""
    query = supabase.table("expenses").select("*").order("expense_date", desc=True)
    if month is not None:
        try:
            year_num, month_num = (int(part) for part in month.split("-", 1))
            start = date(year_num, month_num, 1)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='month must be "YYYY-MM"'
            ) from exc
        end = date(year_num + 1, 1, 1) if month_num == 12 else date(year_num, month_num + 1, 1)
        query = query.gte("expense_date", start.isoformat()).lt("expense_date", end.isoformat())
    result = query.execute()
    return [Expense.model_validate(row) for row in rows(result)]


@router.get("/summary", response_model=list[MonthlyExpenseSummary])
def get_monthly_summary(supabase: SupabaseDep, admin: AdminDep) -> list[MonthlyExpenseSummary]:
    result = supabase.table("expenses").select("expense_date, category, amount").execute()
    summary = expense_service.build_monthly_summary(rows(result))  # type: ignore[arg-type]
    return [MonthlyExpenseSummary.model_validate(vars(entry)) for entry in summary]


@router.get("/payers", response_model=list[Admin])
def list_payers(supabase: SupabaseDep, admin: AdminDep) -> list[Admin]:
    """The club's 3 admins, for the "paid by" dropdown — anyone with an
    admin login can be recorded as the one who actually paid, regardless
    of who's logged in entering the expense."""
    result = supabase.table("admins").select("*").order("username").execute()
    return [Admin.model_validate(row) for row in rows(result)]


def _validate_category(category: str, category_other: str | None) -> None:
    if category == "other" and not (category_other and category_other.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='category_other is required when category is "other"',
        )


@router.post("", response_model=Expense, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, supabase: SupabaseDep, admin: AdminDep) -> Expense:
    _validate_category(payload.category, payload.category_other)
    row = {
        **payload.model_dump(mode="json"),
        "created_by": str(admin.admin_id),
    }
    result = supabase.table("expenses").insert(row).execute()
    return Expense.model_validate(rows(result)[0])


@router.patch("/{expense_id}", response_model=Expense)
def update_expense(
    expense_id: UUID, payload: ExpenseUpdate, supabase: SupabaseDep, admin: AdminDep
) -> Expense:
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    if "category" in updates:
        _validate_category(updates["category"], updates.get("category_other"))
    result = supabase.table("expenses").update(updates).eq("id", str(expense_id)).execute()
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return Expense.model_validate(result_rows[0])


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> None:
    result = supabase.table("expenses").delete().eq("id", str(expense_id)).execute()
    if not rows(result):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")


@router.post("/{expense_id}/pay", response_model=Expense)
def mark_expense_paid(expense_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> Expense:
    result = (
        supabase.table("expenses")
        .update({"is_paid": True, "paid_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", str(expense_id))
        .execute()
    )
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return Expense.model_validate(result_rows[0])


@router.post("/{expense_id}/receipt", response_model=Expense)
async def upload_receipt(
    expense_id: UUID, file: UploadFile, supabase: SupabaseDep, admin: AdminDep
) -> Expense:
    contents = await file.read()
    if len(contents) > MAX_RECEIPT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Receipt file too large (max 5MB)",
        )
    extension = (file.filename or "receipt.jpg").rsplit(".", 1)[-1].lower()
    if extension not in {"jpg", "jpeg", "png", "webp", "heic"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type"
        )
    # Timestamped path (not just expense_id) so re-uploading a replacement
    # doesn't require a cache-busting query param on the <img> src.
    storage_path = f"{expense_id}-{int(datetime.now(timezone.utc).timestamp())}.{extension}"

    supabase.storage.from_(RECEIPT_BUCKET).upload(
        storage_path,
        contents,
        {"content-type": file.content_type or "image/jpeg", "upsert": "true"},
    )
    public_url = supabase.storage.from_(RECEIPT_BUCKET).get_public_url(storage_path)

    result = (
        supabase.table("expenses")
        .update({"receipt_url": public_url})
        .eq("id", str(expense_id))
        .execute()
    )
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return Expense.model_validate(result_rows[0])
