from app.security import hash_password, verify_password


def test_hash_and_verify_roundtrip() -> None:
    hashed = hash_password("changeme123")
    assert hashed != "changeme123"
    assert verify_password("changeme123", hashed)


def test_verify_rejects_wrong_password() -> None:
    hashed = hash_password("changeme123")
    assert not verify_password("wrong-password", hashed)
