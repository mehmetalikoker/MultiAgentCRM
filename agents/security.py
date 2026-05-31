# -*- coding: utf-8 -*-
"""
Prompt güvenlik katmanı: sanitizasyon, izolasyon, output doğrulama.
"""
import re
import unicodedata
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

_MAX_INPUT_LENGTH = 4000

# ── Injection pattern kategorileri ────────────────────────────────────────────

_PATTERNS_DIRECT = [
    # Talimat sıfırlama — İngilizce
    r"ignore\s+(all\s+)?(previous|above|prior|earlier)\s+instructions?",
    r"forget\s+(all\s+)?(previous|above|prior|earlier)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|above|prior)\s+instructions?",
    r"override\s+(all\s+)?(previous|above|prior)\s+instructions?",
    r"reset\s+to\s+(default|factory|original)",
    r"clear\s+(all\s+)?instructions?",
    # Talimat sıfırlama — Türkçe (ö/o varyantlarıyla)
    r"(önceki|onceki|eski)\s+talimat(lar)?\s*(ı|i|nı|ni)?\s*unut",
    r"talimat(lar)?\s*(ı|i)?\s*sıfırla",
    r"sistem(i)?\s+sıfırla",
    r"kurallar[ıi]\s+(unut|durdur|sıfırla|atla)",
    r"kısıtlamaları\s+(kaldır|unut|durdur|atla)",
]

_PATTERNS_PERSONA = [
    # Rol ve persona değiştirme
    r"you\s+are\s+now\s+\w+",
    r"act\s+as\s+(if\s+you\s+(are|were)|a|an)\s+\w+",
    r"pretend\s+(you\s+are|to\s+be)\s+\w+",
    r"play\s+(the\s+role|a\s+character)\s+of",
    r"roleplay\s+as",
    r"simulate\s+(being|a|an)",
    r"from\s+now\s+on\s+(you|act|be|respond)",
    r"new\s+persona",
    r"artık\s+sen\s+\w+",
    r"yeni\s+kimli",
    r"yeni\s+persona",
    r"rol\s+yap",
    r"karakter\s+oyna",
    r"gibi\s+davran",
    r"olduğunu\s+(hayal|farz)\s+et",
    # Bilinen jailbreak isimleri
    r"\bDAN\b",
    r"\bJailbreak\b",
    r"\bDevMode\b",
    r"\bDeveloper\s*Mode\b",
    r"\bUnrestricted\s*Mode\b",
    r"\bGodMode\b",
    r"\bEvilBot\b",
    r"\bAIM\b",           # Always Intelligent and Machiavellian
    r"\bSUPER\s*AI\b",
    r"\bAntiGPT\b",
    r"\bChatGPT[-\s]?(Classic|Ultra|Jailbreak)\b",
]

_PATTERNS_SYSTEM = [
    # Sistem promptunu açığa çıkarma
    r"(show|reveal|display|print|output|repeat|tell\s+me)\s+(your\s+)?(system\s+prompt|instructions?|prompt)",
    r"what\s+(are\s+)?your\s+(system\s+)?instructions?",
    r"sistem\s+prompt",
    r"system\s+prompt",
    r"başlangıç\s+(talimat|prompt)",
    r"gizli\s+talimat",
    r"(göster|paylaş|söyle)\s+(bana\s+)?sistem",
]

_PATTERNS_INDIRECT = [
    # Dolaylı injection — çeviri / kodlama kılığı
    r"translate\s+(this\s+)?to\s+\w+\s*:\s*(ignore|forget|act)",
    r"(encode|decode|convert)\s+(this|the\s+following)\s+(in|to|from)\s+(base64|hex|rot)",
    r"base64\s*:\s*[A-Za-z0-9+/=]{10,}",
    # Hipotez / varsayım kılığı
    r"hypothetically\s+(speaking|if)\s+you\s+(had\s+no|could|were)",
    r"farz\s+edelim\s+ki\s+kısıtlama",
    r"(what\s+would|how\s+would)\s+you\s+(respond|answer|say)\s+if\s+you\s+(had\s+no|were\s+not)",
    # Araştırmacı / güvenlik kılığı
    r"(security\s+researcher|güvenlik\s+araştırmacı)",
    r"for\s+(research|testing|educational)\s+purposes?\s+(only\s+)?(ignore|bypass|override)",
    # Onay kılığı
    r"you\s+(already\s+)?(said|agreed|confirmed|told\s+me)\s+(that\s+)?(you\s+)?(will|can|would)",
]

_PATTERNS_MULTILANG = [
    # Almanca
    r"ignoriere\s+(alle\s+)?(vorherigen|früheren)\s+anweisungen",
    r"vergiss\s+(alle\s+)?(vorherigen|früheren)\s+anweisungen",
    # Fransızca
    r"ignore\s+(toutes\s+les\s+)?(instructions?\s+)?(précédentes?|antérieures?)",
    r"oublie\s+(toutes\s+les\s+)?instructions?\s+précédentes?",
    # İspanyolca
    r"ignora\s+(todas\s+las\s+)?instrucciones?\s+anteriores?",
    # Arapça transliterasyon
    r"ansa\s+al-ta3limat",
    r"ignore\s+al-awami",
]

_ALL_PATTERNS = (
    _PATTERNS_DIRECT
    + _PATTERNS_PERSONA
    + _PATTERNS_SYSTEM
    + _PATTERNS_INDIRECT
    + _PATTERNS_MULTILANG
)

_INJECTION_RE = re.compile(
    "|".join(_ALL_PATTERNS), re.IGNORECASE | re.UNICODE
)

# Sıfır genişlikli ve görünmez Unicode karakterleri
_INVISIBLE_RE = re.compile(
    r"[​‌‍‎‏‪-‮⁠-⁤﻿]"
)


def sanitize_input(text: str) -> tuple[str, bool]:
    """
    Kullanıcı girdisini temizler.

    Döndürür: (temiz_metin, injection_tespit_edildi_mi)
    - Uzunluk sınırı uygular
    - Görünmez Unicode karakterleri kaldırır
    - NFKC normalize eder (homoglyph saldırılarını azaltır)
    - Kontrol karakterlerini kaldırır
    - Bilinen injection kalıplarını maskeler
    """
    if not isinstance(text, str):
        return "", False

    text = text[:_MAX_INPUT_LENGTH]
    text = _INVISIBLE_RE.sub("", text)
    text = unicodedata.normalize("NFKC", text)
    text = "".join(
        ch for ch in text
        if unicodedata.category(ch) not in ("Cc", "Cf") or ch in "\n\t"
    )

    injection_found = bool(_INJECTION_RE.search(text))
    text = _INJECTION_RE.sub("[FILTERED]", text)

    return text.strip(), injection_found


def wrap_user_content(text: str) -> str:
    """Kullanıcı içeriğini XML etiketiyle izole eder."""
    return f"<user_input>\n{text}\n</user_input>"


def build_safe_system_message() -> str:
    from user.prompt_store import get_prompt
    return get_prompt("security_system", "prompts/security_system.txt").strip()
