# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from user.mongo import get_db

_MAX_ATTEMPTS = 5


def _col():
    return get_db()["login_attempts"]


def record_failure(username: str) -> bool:
    """Başarısız deneme kaydeder. 5 hataya ulaşıldıysa True döndürür (kilitle)."""
    from user.db import lock_user

    col = _col()
    col.insert_one({"username": username.lower(), "created_at": datetime.now(timezone.utc)})

    count = col.count_documents({"username": username.lower()})
    if count >= _MAX_ATTEMPTS:
        col.delete_many({"username": username.lower()})
        lock_user(username)
        return True
    return False


def record_success(username: str) -> None:
    """Başarılı girişte sayacı sıfırlar."""
    _col().delete_many({"username": username.lower()})


def attempts_remaining(username: str) -> int:
    count = _col().count_documents({"username": username.lower()})
    return max(0, _MAX_ATTEMPTS - count)
