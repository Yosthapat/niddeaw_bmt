"""The QR the page draws as the club's card: the same code as the plain
image, as rows of 0/1, at error correction H so the cat can sit on it."""

import qrcode

from app.services import promptpay_service


def test_modules_are_the_same_code_at_level_h() -> None:
    payload = promptpay_service.build_promptpay_payload("0812345678", "phone", 109.0)
    rows = promptpay_service.qr_modules(payload)
    assert len(rows) == len(rows[0]) and set("".join(rows)) <= {"0", "1"}
    expected = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=0)
    expected.add_data(payload)
    expected.make(fit=True)
    assert rows == ["".join("1" if c else "0" for c in r) for r in expected.get_matrix()]
    # The three corner squares are where the card draws its rounded ones.
    assert rows[0][:7] == rows[0][-7:] == rows[-1][:7] == "1111111"
