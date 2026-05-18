# -*- coding: utf-8 -*-
"""
LLM çıktı ayrıştırıcıları.
Belirsizlik durumunda her zaman "güvensiz" tarafına düşer (fail-closed).
"""
import json
import re


# ── Compliance (JSON beklenen) ────────────────────────────────────────────────

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_IS_SAFE_RE = re.compile(r'"is_safe"\s*:\s*(true|false)', re.IGNORECASE)


def parse_compliance_response(content: str) -> tuple[bool, list[str]]:
    """
    Compliance agent çıktısından (is_safe, suggestions) döndürür.

    Önce JSON parse dener; başarısız olursa regex ile is_safe alanını arar.
    Her iki yöntem de başarısız olursa fail-closed: (False, []).
    """
    cleaned = content.strip()

    # Markdown kod bloğu varsa içini al
    fence_match = _JSON_FENCE_RE.search(cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # JSON parse dene
    try:
        data = json.loads(cleaned)
        is_safe_raw = data.get("is_safe", False)
        is_safe = bool(is_safe_raw) if isinstance(is_safe_raw, bool) else str(is_safe_raw).lower() == "true"
        suggestions = data.get("suggestions") or []
        suggestions = [s for s in suggestions if isinstance(s, str) and s.strip()]
        return is_safe, suggestions
    except (json.JSONDecodeError, ValueError, AttributeError):
        pass

    # Regex fallback: "is_safe": true/false
    match = _IS_SAFE_RE.search(content)
    if match:
        return match.group(1).lower() == "true", []

    # Fail-closed
    return False, []


# ── Görsel denetim (yapılandırılmış metin beklenen) ───────────────────────────

# Çok kelimeli güvenli ifadeler — önce bunlar kaldırılır, böylece içlerindeki
# "sorun", "hata" gibi kelimeler hatalı şekilde problem sayılmaz.
_VISUAL_SAFE_PHRASES = [
    "sorun yok", "hata yok", "hata bulunamadı", "tutarsızlık yok",
    "sorun tespit edilmedi", "problem yok",
    "no issue", "no problem", "no error", "no issues", "no errors",
]

# Prompt formatında her zaman çıkan bölüm etiketleri — anlam taşımaz.
_VISUAL_SECTION_LABEL_RE = re.compile(
    r"\b(tutarsızlıklar|görsel analizi|tasarım önerileri)\s*:", re.IGNORECASE
)

_VISUAL_SAFE_WORDS = ["tutarlı", "uygun", "consistent"]

_VISUAL_PROBLEM_TERMS = [
    "tutarsızlık", "tutarsız", "sorun", "hata", "uyumsuz",
    "yanıltıcı", "farklı", "eksik", "yanlış", "aykırı",
    "inconsistency", "mismatch", "error", "problem", "issue",
]


def parse_visual_response(content: str) -> bool:
    """
    Görsel denetim çıktısından is_visual_safe döndürür.

    1. Çok kelimeli güvenli ifadeler placeholder ile değiştirilir.
    2. Prompt bölüm etiketleri çıkarılır.
    3. Kalan metinde problem/güvenli sinyal sayısı karşılaştırılır.
    Eşit veya belirsizse fail-closed: False.
    """
    lower = content.lower()

    # Güvenli bileşik ifadeleri önce al, içlerindeki problem sözcükleri etkisiz kılsın
    for phrase in _VISUAL_SAFE_PHRASES:
        lower = lower.replace(phrase, " __safe__ ")

    # Bölüm etiketlerini kaldır ("Tutarsızlıklar:" etiketi sorun değildir)
    lower = _VISUAL_SECTION_LABEL_RE.sub(" __label__ ", lower)

    safe_hits = lower.count("__safe__")
    safe_hits += sum(1 for word in _VISUAL_SAFE_WORDS if word in lower)
    problem_hits = sum(1 for term in _VISUAL_PROBLEM_TERMS if term in lower)

    return safe_hits > problem_hits


# ── Hukuk & Strateji (puan içeren metin beklenen) ────────────────────────────

_SCORE_PATTERNS = [
    re.compile(r"final\s+uygunluk\s+puan[ıi]\s*[:\-]?\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"uygunluk\s+puan[ıi]\s*[:\-]?\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"puan\s*[:\-]?\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"score\s*[:\-]?\s*(\d{1,3})", re.IGNORECASE),
]

_DEFAULT_SCORE = 50  # belirsizlikte nötr, iyimser 85 değil


def parse_legal_score(content: str) -> int:
    """
    Hukuk denetim çıktısından 0-100 uygunluk puanı döndürür.
    Hiçbir kalıp eşleşmezse nötr varsayılan (50) döner.
    """
    for pattern in _SCORE_PATTERNS:
        match = pattern.search(content)
        if match:
            score = int(match.group(1))
            return min(100, max(0, score))
    return _DEFAULT_SCORE
