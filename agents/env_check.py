# -*- coding: utf-8 -*-
"""
Başlangıç ortam değişkeni doğrulaması.
Embedding katmanı her zaman OpenAI kullandığından OPENAI_API_KEY zorunludur.
Seçili modele göre ek bir provider key de gerekebilir.
"""
import os

# Model prefix → gerekli env değişkeni
_MODEL_KEY_MAP = {
    "gpt-":      "OPENAI_API_KEY",
    "claude-":   "ANTHROPIC_API_KEY",
    "gemini-":   "GEMINI_API_KEY",
    "deepseek-": "DEEPSEEK_API_KEY",
}

# Her zaman gerekli (embedding katmanı)
_ALWAYS_REQUIRED = "OPENAI_API_KEY"


def required_key_for_model(model: str) -> str | None:
    """Verilen model adı için gereken env key adını döndürür."""
    for prefix, key in _MODEL_KEY_MAP.items():
        if model.startswith(prefix):
            return key
    return None


def missing_keys(model: str) -> list[str]:
    """
    Eksik ortam değişkenlerini listeler.
    Sonuç boşsa her şey tamam.
    """
    missing = []

    if not os.getenv(_ALWAYS_REQUIRED):
        missing.append(_ALWAYS_REQUIRED)

    model_key = required_key_for_model(model)
    if model_key and model_key != _ALWAYS_REQUIRED and not os.getenv(model_key):
        missing.append(model_key)

    return missing


def is_ready(model: str) -> bool:
    return len(missing_keys(model)) == 0
