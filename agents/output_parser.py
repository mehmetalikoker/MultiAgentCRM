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


def parse_visual_response(content: str) -> tuple[bool, dict | None]:
    """
    Görsel denetim çıktısından (is_visual_safe, parsed_dict) döndürür.

    Önce JSON parse dener; başarısızsa keyword sayımına döner (fail-closed).
    """
    cleaned = content.strip()
    fence = _JSON_FENCE_RE.search(cleaned)
    if fence:
        cleaned = fence.group(1).strip()

    try:
        data = json.loads(cleaned)
        is_safe = bool(data.get("is_visual_safe", False))
        return is_safe, data
    except (json.JSONDecodeError, ValueError, AttributeError):
        pass

    # Keyword fallback
    lower = content.lower()
    for phrase in _VISUAL_SAFE_PHRASES:
        lower = lower.replace(phrase, " __safe__ ")
    lower = _VISUAL_SECTION_LABEL_RE.sub(" __label__ ", lower)
    safe_hits = lower.count("__safe__") + sum(1 for w in _VISUAL_SAFE_WORDS if w in lower)
    problem_hits = sum(1 for t in _VISUAL_PROBLEM_TERMS if t in lower)
    return safe_hits > problem_hits, None


# ── Hukuk & Strateji ─────────────────────────────────────────────────────────

_SCORE_PATTERNS = [
    re.compile(r"uygunluk_puani[\"']?\s*:\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"final\s+uygunluk\s+puan[ıi]\s*[:\-]?\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"uygunluk\s+puan[ıi]\s*[:\-]?\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"puan\s*[:\-]?\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"score\s*[:\-]?\s*(\d{1,3})", re.IGNORECASE),
]

_DEFAULT_SCORE = 50


def parse_legal_response(content: str) -> tuple[dict | None, int]:
    """
    Hukuk denetim çıktısından (parsed_dict, score) döndürür.
    JSON parse başarısızsa dict=None, score regex ile bulunur.
    """
    cleaned = content.strip()
    fence = _JSON_FENCE_RE.search(cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        data = json.loads(cleaned)
        score = int(data.get("uygunluk_puani", _DEFAULT_SCORE))
        score = min(100, max(0, score))
        return data, score
    except (json.JSONDecodeError, ValueError, AttributeError):
        pass

    for pattern in _SCORE_PATTERNS:
        match = pattern.search(content)
        if match:
            return None, min(100, max(0, int(match.group(1))))
    return None, _DEFAULT_SCORE


def parse_legal_score(content: str) -> int:
    """Geriye dönük uyumluluk için — yalnızca skoru döndürür."""
    _, score = parse_legal_response(content)
    return score
