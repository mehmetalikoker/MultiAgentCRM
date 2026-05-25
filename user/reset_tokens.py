# -*- coding: utf-8 -*-
import secrets
import time
import json
import os

_TOKENS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reset_tokens.json")
_EXPIRY_SECONDS = 1800  # 30 dakika


def _load() -> dict:
    if not os.path.exists(_TOKENS_FILE):
        return {}
    with open(_TOKENS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(_TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_token(username: str) -> str:
    """6 haneli OTP oluşturur ve dosyaya yazar."""
    code = f"{secrets.randbelow(900000) + 100000}"
    data = _load()
    data[username.lower()] = {"code": code, "expires": time.time() + _EXPIRY_SECONDS}
    _save(data)
    return code


def verify_token(username: str, code: str) -> bool:
    """Kodu doğrular; süresi dolmuşsa otomatik siler."""
    data = _load()
    entry = data.get(username.lower())
    if not entry:
        return False
    if time.time() > entry["expires"]:
        data.pop(username.lower(), None)
        _save(data)
        return False
    return entry["code"] == code.strip()


def consume_token(username: str) -> None:
    """Kullanılan kodu siler (tek kullanımlık)."""
    data = _load()
    if username.lower() in data:
        data.pop(username.lower())
        _save(data)
