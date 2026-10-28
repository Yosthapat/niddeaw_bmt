"""How a member pays an amount, in whichever way the club has set up.

Shared by a night's bill and a shop order, so the two always show the
same QR, bank account or uploaded code — set once in Admin > Settings.
PromptPay is the only method where the amount is embedded in a QR the
payer's banking app reads automatically (the only interbank QR standard
open to third-party generation); every other method shows the amount as a
plain number to type in.
"""

from fastapi import HTTPException, status
from supabase import Client

from app.db_utils import rows
from app.models.club_settings import PaymentMethod
from app.models.payment import PaymentInfoResponse
from app.services import promptpay_service


def payment_info(supabase: Client, amount: float) -> PaymentInfoResponse:
    settings_result = supabase.table("club_settings").select("*").eq("id", 1).limit(1).execute()
    settings_rows = rows(settings_result)
    if not settings_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Club settings not configured — set them in Admin > Settings first",
        )
    club_settings = settings_rows[0]
    method: PaymentMethod = club_settings["payment_method"]

    if method == "promptpay":
        if not club_settings["promptpay_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PromptPay ID not configured — set it in Admin > Settings first",
            )
        payload = promptpay_service.build_promptpay_payload(
            club_settings["promptpay_id"], club_settings["promptpay_type"], amount
        )
        return PaymentInfoResponse(
            method=method, amount=amount, data_uri=promptpay_service.generate_qr_data_uri(payload)
        )

    if method in ("bank_account", "bank_account_qr"):
        bank_name = club_settings["bank_name"]
        bank_account_number = club_settings["bank_account_number"]
        bank_account_name = club_settings["bank_account_name"]
        if not bank_name or not bank_account_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bank account not configured — set it in Admin > Settings first",
            )
        data_uri = None
        if method == "bank_account_qr":
            text = f"ธนาคาร {bank_name}\nเลขบัญชี {bank_account_number}\nชื่อบัญชี {bank_account_name or ''}"
            data_uri = promptpay_service.generate_qr_data_uri(text)
        return PaymentInfoResponse(
            method=method,
            amount=amount,
            data_uri=data_uri,
            bank_name=bank_name,
            bank_account_number=bank_account_number,
            bank_account_name=bank_account_name,
        )

    if not club_settings["uploaded_qr_url"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No QR code uploaded — upload one in Admin > Settings first",
        )
    return PaymentInfoResponse(method=method, amount=amount, data_uri=club_settings["uploaded_qr_url"])
