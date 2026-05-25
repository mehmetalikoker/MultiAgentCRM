# -*- coding: utf-8 -*-
import time
from collections import defaultdict

_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300   # 5 dakika içinde max deneme

# {username_lower: [timestamp, ...]}
_attempts: dict = defaultdict(list)


def record_failure(username: str) -> bool:
    """Başarısız deneme kaydeder. 5 hataya ulaşıldıysa True döndürür (kilitle)."""
    from user.db import lock_user

    key = username.lower()
    now = time.time()

    _attempts[key] = [t for t in _attempts[key] if now - t < _WINDOW_SECONDS]
    _attempts[key].append(now)

    if len(_attempts[key]) >= _MAX_ATTEMPTS:
        _attempts.pop(key, None)
        lock_user(username)
        return True

    return False


def record_success(username: str) -> None:
    """Başarılı girişte sayacı sıfırlar."""
    _attempts.pop(username.lower(), None)


def attempts_remaining(username: str) -> int:
    key = username.lower()
    now = time.time()
    recent = [t for t in _attempts[key] if now - t < _WINDOW_SECONDS]
    return max(0, _MAX_ATTEMPTS - len(recent))
