"""Regression tests pinned to dtinth/promptpay-qr's known-good test vectors
(https://github.com/dtinth/promptpay-qr/blob/master/index.test.js) — verified
byte-for-byte against this Python port before it ever touches real money."""

import pytest

from app.services.promptpay_service import build_promptpay_payload

CASES = [
    (
        "0801234567",
        "phone",
        None,
        "00020101021129370016A000000677010111011300668012345675802TH530376463046197",
    ),
    (
        "080-123-4567",
        "phone",
        None,
        "00020101021129370016A000000677010111011300668012345675802TH530376463046197",
    ),
    (
        "1111111111111",
        "national_id",
        None,
        "00020101021129370016A000000677010111021311111111111115802TH530376463047B5A",
    ),
    (
        "0123456789012",
        "national_id",
        None,
        "00020101021129370016A000000677010111021301234567890125802TH530376463040CBD",
    ),
    (
        "012345678901234",
        "ewallet",
        None,
        "00020101021129390016A00000067701011103150123456789012345802TH530376463049781",
    ),
    (
        "000-000-0000",
        "phone",
        4.22,
        "00020101021229370016A000000677010111011300660000000005802TH530376454044.226304E469",
    ),
]


@pytest.mark.parametrize("promptpay_id,promptpay_type,amount,expected", CASES)
def test_matches_reference_vector(
    promptpay_id: str, promptpay_type: str, amount: float | None, expected: str
) -> None:
    assert build_promptpay_payload(promptpay_id, promptpay_type, amount) == expected  # type: ignore[arg-type]
