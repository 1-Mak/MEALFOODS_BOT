"""Authentication: initData validation (HMAC-SHA256) and JWT tokens."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs

import jwt

from app.config import settings

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 86400  # 24 hours


def _get_secret_key() -> bytes:
    """Derive secret key from bot token for initData validation.

    secret = HMAC-SHA256(key="WebAppData", msg=bot_token)
    """
    token = settings.max_bot_token.get_secret_value()
    return hmac.new(
        b"WebAppData",
        token.encode(),
        hashlib.sha256,
    ).digest()


def validate_init_data(init_data: str) -> dict[str, str] | None:
    """Validate MAX Bridge initData HMAC-SHA256 signature.

    Returns parsed data dict if valid, None if invalid.
    """
    parsed = parse_qs(init_data, keep_blank_values=True)
    data = {k: v[0] for k, v in parsed.items()}

    received_hash = data.pop("hash", None)
    if not received_hash:
        return None

    # data-check string: sorted key=value pairs joined by \n
    check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items())
    )

    secret = _get_secret_key()
    computed = hmac.new(
        secret,
        check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed, received_hash):
        return None

    return data


def extract_user_id(init_data_dict: dict[str, str]) -> int | None:
    """Extract user_id from validated initData dict."""
    user_json = init_data_dict.get("user", "{}")
    try:
        user_info = json.loads(user_json)
    except json.JSONDecodeError:
        return None
    return user_info.get("id")


def create_jwt(user_id: int) -> str:
    """Create a JWT token for the given MAX user_id."""
    secret = settings.max_bot_token.get_secret_value()
    payload = {
        "sub": str(user_id),
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRY_SECONDS,
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict | None:
    """Decode and verify a JWT token. Returns payload or None."""
    secret = settings.max_bot_token.get_secret_value()
    try:
        return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
