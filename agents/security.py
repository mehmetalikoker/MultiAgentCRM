# -*- coding: utf-8 -*-
"""
Prompt güvenlik katmanı: sanitizasyon, izolasyon, output doğrulama.
"""
import re
import unicodedata
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

_MAX_INPUT_LENGTH = 2000

# Injection girişimlerinde sıkça görülen kalıplar
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions?",
    r"forget\s+(all\s+)?(previous|above|prior)\s+instructions?",
    r"önceki\s+talimat(lar)?\s*(ı|i)?\s*unut",
    r"sistem\s+prompt",
    r"system\s+prompt",
    r"you\s+are\s+now",
    r"artık\s+sen",
    r"new\s+persona",
    r"yeni\s+kimli",
    r"jailbreak",
    r"DAN\b",
    r"act\s+as\s+if",
    r"pretend\s+(you\s+are|to\s+be)",
    r"rol\s+yap",
    r"karakter\s+oyna",
]

_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS), re.IGNORECASE | re.UNICODE
)


def sanitize_input(text: str) -> str:
    """
    Kullanıcı girdisini temizler:
    - Maksimum uzunluk sınırı uygular
    - Kontrol karakterlerini kaldırır
    - Bilinen injection kalıplarını tespit edip kaldırır
    """
    if not isinstance(text, str):
        return ""

    # Uzunluk sınırı
    text = text[:_MAX_INPUT_LENGTH]

    # Unicode normalize + kontrol karakterlerini kaldır
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) not in ("Cc", "Cf") or ch in "\n\t")

    # Injection kalıplarını kaldır / maskele
    text = _INJECTION_RE.sub("[FILTERED]", text)

    return text.strip()


def wrap_user_content(text: str) -> str:
    """
    Kullanıcı içeriğini XML etiketiyle izole eder.
    Model, bu etiket içindeki metni talimat olarak yorumlamamalıdır.
    """
    return f"<user_input>\n{text}\n</user_input>"


def build_safe_system_message() -> str:
    from user.prompt_store import get_prompt
    return get_prompt("security_system", "prompts/security_system.txt").strip()