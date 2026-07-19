"""EMVCo Merchant Presented QR payload builder for Thai PromptPay.

Self-implemented (no unverified pip dependency for something payment-adjacent).
TLV tag structure, target formatting, and CRC-16/CCITT-FALSE checksum were
cross-checked against the widely used dtinth/promptpay-qr reference
implementation (MIT licensed, https://github.com/dtinth/promptpay-qr).

This produces a *static-amount display QR* for the payer to scan and
transfer manually — there is no live payment callback/webhook (see issue
doc's explicit scope note: PromptPay QR is not a payment gateway here).
"""

import base64
import io
import re

import qrcode
from qrcode.image.pil import PilImage

from app.models.club_settings import PromptPayType

_PROMPTPAY_AID = "A000000677010111"
_CURRENCY_THB = "764"
_COUNTRY_TH = "TH"


def _tlv(tag: str, value: str) -> str:
    return f"{tag}{len(value):02d}{value}"


def _crc16_ccitt_false(data: str) -> str:
    crc = 0xFFFF
    for byte in data.encode("ascii"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def _format_target(promptpay_id: str, promptpay_type: PromptPayType) -> tuple[str, str]:
    """Returns (merchant-info subfield tag, formatted target value)."""
    digits = re.sub(r"\D", "", promptpay_id)
    if promptpay_type == "phone":
        national_number = re.sub(r"^0", "66", digits)
        return "01", national_number.rjust(13, "0")
    if promptpay_type == "national_id":
        return "02", digits.rjust(13, "0")
    return "03", digits.rjust(15, "0")  # ewallet


def build_promptpay_payload(
    promptpay_id: str, promptpay_type: PromptPayType, amount: float | None
) -> str:
    subfield_tag, target_value = _format_target(promptpay_id, promptpay_type)
    merchant_info = _tlv("00", _PROMPTPAY_AID) + _tlv(subfield_tag, target_value)

    fields = [
        _tlv("00", "01"),
        _tlv("01", "12" if amount is not None else "11"),
        _tlv("29", merchant_info),
        _tlv("58", _COUNTRY_TH),
        _tlv("53", _CURRENCY_THB),
    ]
    if amount is not None:
        fields.append(_tlv("54", f"{amount:.2f}"))

    payload_without_crc = "".join(fields) + "6304"
    checksum = _crc16_ccitt_false(payload_without_crc)
    return payload_without_crc + checksum


def generate_qr_data_uri(payload: str) -> str:
    img = qrcode.make(payload, image_factory=PilImage)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
