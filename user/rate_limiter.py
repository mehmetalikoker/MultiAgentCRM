# -*- coding: utf-8 -*-
import time
import json
import os

_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300  # 5 dakika

_ATTEMPTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login_attempts.json")


def _load() -> dict:
    if not os.path.exists(_ATTEMPTS_FILE):
        return {}
    with open(_ATTEMPTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(_ATTEMPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _clean(timestamps: list) -> list:
    cutoff = time.time() - _WINDOW_SECONDS
    return [t for t in timestamps if t > cutoff]


def record_failure(username: str) -> bool:
    """Başarısız deneme kaydeder. 5 hataya ulaşıldıysa True döndürür (kilitle)."""
    from user.db import lock_user

    key = username.lower()
    data = _load()
    data[key] = _clean(data.get(key, []))
    data[key].append(time.time())

    if len(data[key]) >= _MAX_ATTEMPTS:
        data.pop(key, None)
        _save(data)
        lock_user(username)
        return True

    _save(data)
    return False


def record_success(username: str) -> None:
    """Başarılı girişte sayacı sıfırlar."""
    key = username.lower()
    data = _load()
    if key in data:
        data.pop(key)
        _save(data)


def attempts_remaining(username: str) -> int:
    key = username.lower()
    data = _load()
    recent = _clean(data.get(key, []))
    return max(0, _MAX_ATTEMPTS - len(recent))
