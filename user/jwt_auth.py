# -*- coding: utf-8 -*-
import os
from datetime import datetime, timezone, timedelta

import jwt
from dotenv import load_dotenv

load_dotenv()

_ALGORITHM = "HS256"
_EXPIRY_HOURS = 8
_COOKIE_NAME = "crm_auth"


def _secret() -> str:
    s = os.getenv("JWT_SECRET", "")
    if not s:
        raise RuntimeError(
            "JWT_SECRET tanımlanmamış. .env dosyasına güvenli bir değer ekleyin."
        )
    return s


def create_jwt(username: str, display_name: str) -> str:
    payload = {
        "sub": username,
        "display_name": display_name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def verify_jwt(token: str) -> dict | None:
    """Geçerli token → payload dict. Geçersiz/süresi dolmuş → None."""
    try:
        return jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
