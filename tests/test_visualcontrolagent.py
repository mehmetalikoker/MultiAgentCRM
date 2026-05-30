# -*- coding: utf-8 -*-
import base64
import pytest
from unittest.mock import patch, MagicMock


class TestEncodeImage:
    """
    encode_image(image_bytes) fonksiyonunu test eder.

    Bu fonksiyon, görsel verisini (bytes) base64 string'e dönüştürür.
    Dönüştürülen string, LLM'e multimodal mesaj içinde data URI olarak gönderilir.
    Disk'e yazılmaz; bellek içinde çalışır.

    Test edilen senaryolar:
    - Döndürülen base64 string'in orijinal bytes'a decode edilebilmesi
    - Boş bytes için geçerli base64 döndürülmesi
    - Dönen değerin bytes değil string tipinde olması
    - Büyük görsel verisinin doğru encode edilmesi
    """

    def test_returns_valid_base64_string(self):
        from agents.visualcontrolagent import encode_image
        content = b"sample-binary-content"
        result = encode_image(content)
        assert base64.b64decode(result) == content

    def test_empty_bytes_returns_empty_base64(self):
        from agents.visualcontrolagent import encode_image
        result = encode_image(b"")
        assert base64.b64decode(result) == b""

    def test_returns_string_not_bytes(self):
        from agents.visualcontrolagent import encode_image
        result = encode_image(b"data")
        assert isinstance(result, str)

    def test_large_image_encoded_correctly(self):
        from agents.visualcontrolagent import encode_image
        content = b"x" * 100_000
        result = encode_image(content)
        assert base64.b64decode(result) == content


class TestVisualAuditor:
    """
    visual_auditor(state) LangGraph node fonksiyonunu test eder.

    Bu fonksiyon, kampanya görselini onaylanan metinle karşılaştırarak denetler.
    Görsel, state'teki image_bytes ve image_mime alanlarından alınır; disk'e
    yazılmadan doğrudan base64'e çevrilerek LLM'e multimodal mesaj olarak gönderilir.

    Test edilen senaryolar:
    - Görsel denetim raporunun state'e kaydedilmesi
    - "Hata bulunamadı" gibi güvenli ifade içeren yanıtta is_visual_safe:True
    - "Tutarsızlık" gibi problem ifadesi içeren yanıtta is_visual_safe:False
    - selected_model belirtilmediğinde varsayılan modelin (gpt-4o) kullanılması
    - LLM'e gönderilen mesajın image_url tipinde bir parça içermesi
    - MIME tipinin data URI'ye doğru eklenmesi
    - Görsel bytes'ının base64 olarak data URI içinde iletilmesi
    """

    def _make_state(self, image_bytes=b"fake-png", mime="image/png",
                    campaign_text="Masrafsız kredi.", model="gpt-4o"):
        return {
            "campaign_text": campaign_text,
            "image_bytes": image_bytes,
            "image_mime": mime,
            "selected_model": model,
        }

    def test_visual_report_stored_in_state(self):
        state = self._make_state()
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Görsel Analizi: Her şey yolunda.")

        with patch("agents.visualcontrolagent.get_llm", return_value=mock_llm):
            from agents.visualcontrolagent import visual_auditor
            result = visual_auditor(state)

        assert result["visual_report"] == "Görsel Analizi: Her şey yolunda."

    def test_is_visual_safe_true_when_hata_bulunamadi_in_response(self):
        state = self._make_state()
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Hata bulunamadı, görsel uygun.")

        with patch("agents.visualcontrolagent.get_llm", return_value=mock_llm):
            from agents.visualcontrolagent import visual_auditor
            result = visual_auditor(state)

        assert result["is_visual_safe"] is True

    def test_is_visual_safe_false_when_tutarsizlik_found(self):
        state = self._make_state()
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Görselde metin tutarsızlığı tespit edildi.")

        with patch("agents.visualcontrolagent.get_llm", return_value=mock_llm):
            from agents.visualcontrolagent import visual_auditor
            result = visual_auditor(state)

        assert result["is_visual_safe"] is False

    def test_default_model_is_gpt4o(self):
        state = {
            "campaign_text": "Test metni.",
            "image_bytes": b"fake",
            "image_mime": "image/png",
        }
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="OK")

        with patch("agents.visualcontrolagent.get_llm", return_value=mock_llm) as mock_factory:
            from agents.visualcontrolagent import visual_auditor
            visual_auditor(state)
            mock_factory.assert_called_once_with("gpt-4o")

    def test_multimodal_message_contains_image_url(self):
        state = self._make_state(image_bytes=b"fake-png", mime="image/png")
        mock_llm = MagicMock()
        captured_messages = []

        def capture_invoke(messages):
            captured_messages.extend(messages)
            return MagicMock(content="Hata bulunamadı.")

        mock_llm.invoke.side_effect = capture_invoke

        with patch("agents.visualcontrolagent.get_llm", return_value=mock_llm):
            from agents.visualcontrolagent import visual_auditor
            visual_auditor(state)

        human_msg = captured_messages[1]
        types = [p["type"] for p in human_msg.content]
        assert "image_url" in types

    def test_mime_type_passed_to_message(self):
        state = self._make_state(image_bytes=b"data", mime="image/png")
        mock_llm = MagicMock()
        captured_messages = []

        def capture_invoke(messages):
            captured_messages.extend(messages)
            return MagicMock(content="Sorun yok.")

        mock_llm.invoke.side_effect = capture_invoke

        with patch("agents.visualcontrolagent.get_llm", return_value=mock_llm):
            from agents.visualcontrolagent import visual_auditor
            visual_auditor(state)

        human_msg = captured_messages[1]
        image_part = next(p for p in human_msg.content if p["type"] == "image_url")
        assert "image/png" in image_part["image_url"]["url"]

    def test_image_bytes_base64_encoded_in_message(self):
        image_bytes = b"real-image-bytes"
        state = self._make_state(image_bytes=image_bytes, mime="image/jpeg")
        mock_llm = MagicMock()
        captured_messages = []

        def capture_invoke(messages):
            captured_messages.extend(messages)
            return MagicMock(content="Sorun yok.")

        mock_llm.invoke.side_effect = capture_invoke

        with patch("agents.visualcontrolagent.get_llm", return_value=mock_llm):
            from agents.visualcontrolagent import visual_auditor
            visual_auditor(state)

        human_msg = captured_messages[1]
        image_part = next(p for p in human_msg.content if p["type"] == "image_url")
        expected_b64 = base64.b64encode(image_bytes).decode("utf-8")
        assert expected_b64 in image_part["image_url"]["url"]


class TestVisualAgentStateSchema:
    """
    VisualControlAgent AgentState TypedDict şemasını test eder.

    image_path kaldırılıp image_bytes + image_mime'a geçildiğinden bu testler
    şemanın güncel kalmasını ve eski alanın yanlışlıkla geri eklenmemesini sağlar.

    Test edilen senaryolar:
    - AgentState'in image_bytes ve image_mime alanlarını içermesi
    - Eski image_path alanının artık şemada bulunmaması
    """

    def test_agent_state_has_required_keys(self):
        from agents.visualcontrolagent import AgentState
        annotations = AgentState.__annotations__
        required = {"campaign_text", "image_bytes", "image_mime", "selected_model",
                    "visual_report", "is_visual_safe"}
        assert required.issubset(annotations.keys())

    def test_image_path_no_longer_in_state(self):
        from agents.visualcontrolagent import AgentState
        assert "image_path" not in AgentState.__annotations__
