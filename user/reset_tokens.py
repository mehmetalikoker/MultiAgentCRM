# -*- coding: utf-8 -*-
import secrets
from datetime import datetime, timezone
from user.mongo import get_db


def _col():
    return get_db()["reset_tokens"]


def create_token(username: str) -> str:
    """6 haneli OTP oluşturur ve veritabanına yazar."""
    code = f"{secrets.randbelow(900000) + 100000}"
    col = _col()
    col.delete_many({"username": username.lower()})
    col.insert_one({"username": username.lower(), "code": code, "created_at": datetime.now(timezone.utc)})
    return code


def verify_token(username: str, code: str) -> bool:
    """Kodu doğrular. TTL index süresi dolmuş kayıtları otomatik siler."""
    entry = _col().find_one({"username": username.lower()})
    if not entry:
        return False
    return entry["code"] == code.strip()


def consume_token(username: str) -> None:
    """Kullanılan kodu siler (tek kullanımlık)."""
    _col().delete_many({"username": username.lower()})
