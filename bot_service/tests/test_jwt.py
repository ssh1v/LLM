import pytest

from app.core.jwt import decode_and_validate
from tests.conftest import make_token


def test_decode_valid_token():
    token = make_token(sub="123", role="user")
    payload = decode_and_validate(token)
    assert payload["sub"] == "123"


def test_garbage_token_raises():
    with pytest.raises(ValueError):
        decode_and_validate("this-is-not-a-jwt")
