import jwt
import pytest
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("secret-password")
    assert hashed != "secret-password"
    assert hashed.startswith("$argon2")
    assert verify_password("secret-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_token_roundtrip() -> None:
    token = create_token("user-id-123", "access")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-id-123"
    assert payload["type"] == "access"


def test_wrong_token_type_rejected() -> None:
    refresh = create_token("user-id-123", "refresh")
    with pytest.raises(UnauthorizedError):
        decode_token(refresh, expected_type="access")


def test_tampered_token_rejected() -> None:
    forged = jwt.encode(
        {"sub": "x", "type": "access"}, "other-key-that-is-long-enough-32b!", algorithm="HS256"
    )
    with pytest.raises(UnauthorizedError):
        decode_token(forged, expected_type="access")
