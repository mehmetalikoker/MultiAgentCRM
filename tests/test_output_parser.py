# -*- coding: utf-8 -*-
import pytest
from agents.output_parser import parse_compliance_response, parse_visual_response, parse_legal_score


class TestParseComplianceResponse:

    # ── Temiz JSON ────────────────────────────────────────────────────────────

    def test_valid_json_safe_true(self):
        content = '{"is_safe": true, "report": "Uygun", "suggestions": []}'
        is_safe, suggestions = parse_compliance_response(content)
        assert is_safe is True
        assert suggestions == []

    def test_valid_json_safe_false(self):
        content = '{"is_safe": false, "report": "İhlal var.", "suggestions": ["Bedava yerine Masrafsız"]}'
        is_safe, suggestions = parse_compliance_response(content)
        assert is_safe is False
        assert "Bedava yerine Masrafsız" in suggestions

    def test_valid_json_suggestions_returned(self):
        content = '{"is_safe": false, "report": "x", "suggestions": ["Öneri 1", "Öneri 2"]}'
        _, suggestions = parse_compliance_response(content)
        assert len(suggestions) == 2

    def test_valid_json_empty_suggestions_filtered(self):
        content = '{"is_safe": true, "report": "x", "suggestions": ["", "  ", "Geçerli öneri"]}'
        _, suggestions = parse_compliance_response(content)
        assert suggestions == ["Geçerli öneri"]

    def test_json_is_safe_string_true(self):
        content = '{"is_safe": "true", "report": "x", "suggestions": []}'
        is_safe, _ = parse_compliance_response(content)
        assert is_safe is True

    def test_json_is_safe_string_false(self):
        content = '{"is_safe": "false", "report": "x", "suggestions": []}'
        is_safe, _ = parse_compliance_response(content)
        assert is_safe is False

    # ── Markdown kod bloğu ────────────────────────────────────────────────────

    def test_markdown_json_fence_parsed(self):
        content = '```json\n{"is_safe": true, "report": "OK", "suggestions": []}\n```'
        is_safe, _ = parse_compliance_response(content)
        assert is_safe is True

    def test_markdown_fence_without_json_label(self):
        content = '```\n{"is_safe": false, "report": "Hata", "suggestions": []}\n```'
        is_safe, _ = parse_compliance_response(content)
        assert is_safe is False

    def test_markdown_fence_with_surrounding_text(self):
        content = 'İşte sonuç:\n```json\n{"is_safe": true, "report": "OK", "suggestions": []}\n```\nTeşekkürler.'
        is_safe, _ = parse_compliance_response(content)
        assert is_safe is True

    # ── Regex fallback ────────────────────────────────────────────────────────

    def test_regex_fallback_true(self):
        content = 'Analiz tamamlandı. "is_safe": true olarak değerlendirildi.'
        is_safe, suggestions = parse_compliance_response(content)
        assert is_safe is True
        assert suggestions == []

    def test_regex_fallback_false(self):
        content = 'Kampanya uygun değil. "is_safe": false'
        is_safe, _ = parse_compliance_response(content)
        assert is_safe is False

    # ── Eski kırılgan davranış artık olmamalı ─────────────────────────────────

    def test_untrue_does_not_trigger_safe(self):
        # Eski "true" in content kontrolü "untrue" için True verirdi
        content = '{"is_safe": false, "report": "This is untrue claim.", "suggestions": []}'
        is_safe, _ = parse_compliance_response(content)
        assert is_safe is False

    def test_true_in_report_text_does_not_affect_is_safe(self):
        content = '{"is_safe": false, "report": "The statement is true but non-compliant.", "suggestions": []}'
        is_safe, _ = parse_compliance_response(content)
        assert is_safe is False

    # ── Fail-closed ───────────────────────────────────────────────────────────

    def test_empty_content_returns_false(self):
        is_safe, suggestions = parse_compliance_response("")
        assert is_safe is False
        assert suggestions == []

    def test_garbage_content_returns_false(self):
        is_safe, suggestions = parse_compliance_response("lorem ipsum dolor sit amet")
        assert is_safe is False
        assert suggestions == []

    def test_malformed_json_returns_false(self):
        is_safe, _ = parse_compliance_response('{"is_safe": tru')
        assert is_safe is False

    def test_missing_is_safe_key_returns_false(self):
        is_safe, _ = parse_compliance_response('{"report": "Uygun", "suggestions": []}')
        assert is_safe is False


class TestParseVisualResponse:

    # ── Güvenli çıktılar ──────────────────────────────────────────────────────

    def test_explicit_safe_term_turkish(self):
        content = "Görsel Analizi: Görsel tutarlı.\nTutarsızlıklar: Sorun yok.\nÖneriler: -"
        assert parse_visual_response(content) is True

    def test_explicit_hata_yok(self):
        content = "Görsel incelendi. Hata yok. Metinle uyumlu."
        assert parse_visual_response(content) is True

    def test_consistent_english(self):
        content = "The visual is consistent with the approved text. No issue found."
        assert parse_visual_response(content) is True

    # ── Güvensiz çıktılar ─────────────────────────────────────────────────────

    def test_explicit_problem_term(self):
        content = "Tutarsızlıklar: Görseldeki faiz oranı metinden farklı."
        assert parse_visual_response(content) is False

    def test_multiple_problem_terms(self):
        content = "Hata tespit edildi. Metin uyumsuz. Yanıltıcı öğe mevcut."
        assert parse_visual_response(content) is False

    # ── Eski kırılgan davranış artık olmamalı ─────────────────────────────────

    def test_no_hata_bulunamadi_phrase_but_safe(self):
        # Eski kod "hata bulunamadı" yoksa False verirdi
        content = "Görsel tutarlı. Sorun yok. Tasarım uygun."
        assert parse_visual_response(content) is True

    def test_english_only_safe_response(self):
        # Eski kod Türkçe dışı yanıtta her zaman False verirdi
        content = "The visual is consistent with the text. No issues found."
        assert parse_visual_response(content) is True

    # ── Fail-closed ───────────────────────────────────────────────────────────

    def test_empty_content_returns_false(self):
        assert parse_visual_response("") is False

    def test_ambiguous_content_returns_false(self):
        content = "Görsel incelendi."
        assert parse_visual_response(content) is False

    def test_equal_signals_returns_false(self):
        # Eşit sayıda sinyal → fail-closed
        content = "Tutarlı görünüyor ancak tutarsızlık var."
        assert parse_visual_response(content) is False


class TestParseLegalScore:

    # ── Başarılı parse ────────────────────────────────────────────────────────

    def test_full_label_colon(self):
        content = "Mevzuat İhlalleri: Yok\nFinal Uygunluk Puanı: 92"
        assert parse_legal_score(content) == 92

    def test_full_label_dash(self):
        content = "Final Uygunluk Puanı - 75"
        assert parse_legal_score(content) == 75

    def test_short_label(self):
        content = "Uygunluk Puanı: 60"
        assert parse_legal_score(content) == 60

    def test_puan_label(self):
        content = "Puan: 45"
        assert parse_legal_score(content) == 45

    def test_score_english(self):
        content = "Compliance score: 88"
        assert parse_legal_score(content) == 88

    def test_case_insensitive(self):
        content = "final uygunluk puanı: 70"
        assert parse_legal_score(content) == 70

    # ── Sınır değerleri ───────────────────────────────────────────────────────

    def test_score_clamped_to_100(self):
        content = "Final Uygunluk Puanı: 150"
        assert parse_legal_score(content) == 100

    def test_score_clamped_to_0(self):
        # Regex sadece \d{1,3} yakalar, negatif olamaz; ama clamp yine de çalışmalı
        content = "Puan: 0"
        assert parse_legal_score(content) == 0

    def test_score_exactly_100(self):
        content = "Final Uygunluk Puanı: 100"
        assert parse_legal_score(content) == 100

    # ── Eski kırılgan davranış artık olmamalı ─────────────────────────────────

    def test_default_is_not_optimistic_85(self):
        # Eski kod parse başarısız olunca 85 verirdi
        content = "Kampanya yasal açıdan değerlendirildi."
        assert parse_legal_score(content) != 85

    def test_neutral_default_on_failure(self):
        content = "Kampanya yasal açıdan değerlendirildi."
        assert parse_legal_score(content) == 50

    def test_empty_content_returns_default(self):
        assert parse_legal_score("") == 50

    def test_no_score_in_content_returns_default(self):
        content = "Mevzuat ihlali tespit edilmedi. Risk seviyesi düşük."
        assert parse_legal_score(content) == 50
