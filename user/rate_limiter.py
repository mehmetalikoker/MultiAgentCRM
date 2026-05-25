# -*- coding: utf-8 -*-
import time
from collections import defaultdict

_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300   # 5 dakika içinde max deneme
_LOCKOUT_SECONDS = 300  # kilitleme süresi

# {username_lower: {"attempts": [timestamp, ...], "locked_until": float}}
_state: dict = defaultdict(lambda: {"attempts": [], "locked_until": 0.0})


def is_locked(username: str) -> tuple[bool, int]:
    """(kilitli_mi, kalan_saniye) döndürür."""
    entry = _state[username.lower()]
    remaining = entry["locked_until"] - time.time()
    if remaining > 0:
        return True, int(remaining) + 1
    return False, 0


def record_failure(username: str) -> tuple[bool, int]:
    """Başarısız deneme kaydeder. (kilitlendi_mi, kalan_saniye) döndürür."""
    key = username.lower()
    entry = _state[key]
    now = time.time()

    entry["attempts"] = [t for t in entry["attempts"] if now - t < _WINDOW_SECONDS]
    entry["attempts"].append(now)

    if len(entry["attempts"]) >= _MAX_ATTEMPTS:
        entry["locked_until"] = now + _LOCKOUT_SECONDS
        entry["attempts"] = []
        return True, _LOCKOUT_SECONDS

    return False, 0


def record_success(username: str) -> None:
    """Başarılı girişte sayacı sıfırlar."""
    _state.pop(username.lower(), None)


def attempts_remaining(username: str) -> int:
    key = username.lower()
    entry = _state[key]
    now = time.time()
    recent = [t for t in entry["attempts"] if now - t < _WINDOW_SECONDS]
    return max(0, _MAX_ATTEMPTS - len(recent))
