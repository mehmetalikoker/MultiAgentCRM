# -*- coding: utf-8 -*-
import os
import base64
import tempfile
import pytest
from unittest.mock import patch, MagicMock, mock_open


class TestEncodeImage:
    def _write_temp_image(self, suffix: str, content: bytes = b"fake-image-data") -> str:
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(content)
        tmp.close()
        return tmp.name

    def test_jpg_returns_correct_mime(self):
        path = self._write_temp_image(".jpg")
        try:
            from agents.visualcontrolagent import encode_image
            _, mime = encode_image(path)
            assert mime == "image/jpeg"
        finally:
            os.unlink(path)

    def test_jpeg_returns_correct_mime(self):
        path = self._write_temp_image(".jpeg")
        try:
            from agents.visualcontrolagent import encode_image
            _, mime = encode_image(path)
            assert mime == "image/jpeg"
        finally:
            os.unlink(path)

    def test_png_returns_correct_mime(self):
        path = self._write_temp_image(".png")
        try:
            from agents.visualcontrolagent import encode_image
            _, mime = encode_image(path)
            assert mime == "image/png"
        finally:
            os.unlink(path)

    def test_gif_returns_correct_mime(self):
        path = self._write_temp_image(".gif")
        try:
            from agents.visualcontrolagent import encode_image
            _, mime = encode_image(path)
            assert mime == "image/gif"
        finally:
            os.unlink(path)

    def test_webp_returns_correct_mime(self):
        path = self._write_temp_image(".webp")
        try:
            from agents.visualcontrolagent import encode_image
            _, mime = encode_image(path)
            assert mime == "image/webp"
        finally:
            os.unlink(path)

    def test_unknown_extension_defaults_to_jpeg(self):
        path = self._write_temp_image(".bmp")
        try:
            from agents.visualcontrolagent import encode_image
            _, mime = encode_image(path)
            assert mime == "image/jpeg"
        finally:
            os.unlink(path)

    def test_returns_valid_base64_string(self):
        content = b"sample-binary-content"
        path = self._write_temp_image(".png", content=content)
        try:
            from agents.visualcontrolagent import encode_image
            data, _ = encode_image(path)
            decoded = base64.b64decode(data)
            assert decoded == content
        finally:
            os.unlink(path)

    def test_uppercase_extension_handled(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".PNG", delete=False)
        tmp.write(b"data")
        tmp.close()
        try:
            from agents.visualcontrolagent import encode_image
            _, mime = encode_image(tmp.name)
            assert mime == "image/png"
        finally:
            os.unlink(tmp.name)


class TestVisualAuditor:
    def _make_temp_png(self) -> str:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(b"fake-png")
        tmp.close()
        return tmp.name

    def test_visual_report_stored_in_state(self):
        image_path = self._make_temp_png()
        try:
            state = {
                "campaign_text": "Masrafsız kredi fırsatı.",
                "image_path": image_path,
                "selected_model": "gpt-4o",
            }
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content="Görsel Analizi: Her şey yolunda.")

            with patch("agents.visualcontrolagent.get_llm", return_value=mock_llm):
                from agents.visualcontrolagent import visual_auditor
                result = visual_auditor(state)

            assert result["visual_report"] == "Görsel Analizi: Her şey yolunda."
        finally:
            os.unlink(image_path)

    def test_is_visual_safe_true_when_hata_bulunamadi_in_response(self):
        image_path = self._make_temp_png()
        try:
            state = {
                "campaign_text": "Masrafsız kredi.",
                "image_path": image_path,
                "selected_model": "gpt-4o",
            }
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content="Hata bulunamadı, görsel uygun.")

            with patch("agents.visualcontrolagent.get_llm", return_value=mock_llm):
                from agents.visualcontrolagent import visual_auditor
                result = visual_auditor(state)

            assert result["is_visual_safe"] is True
        finally:
            os.unlink(image_path)

    def test_is_visual_safe_false_when_hata_found(self):
        image_path = self._make_temp_png()
        try:
            state = {
                "campaign_text": "Kredi kampanyası.",
                "image_path": image_path,
                "selected_model": "gpt-4o",
            }
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content="Görselde metin tutarsızlığı tespit edildi.")

            with patch("agents.visualcontrolagent.get_llm", return_value=mock_llm):
                from agents.visualcontrolagent import visual_auditor
                result = visual_auditor(state)

            assert result["is_visual_safe"] is False
        finally:
            os.unlink(image_path)

    def test_default_model_is_gpt4o(self):
        image_path = self._make_temp_png()
        try:
            state = {
                "campaign_text": "Test metni.",
                "image_path": image_path,
            }
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content="OK")

            with patch("agents.visualcontrolagent.get_llm", return_value=mock_llm) as mock_factory:
                from agents.visualcontrolagent import visual_auditor
                visual_auditor(state)
                mock_factory.assert_called_once_with("gpt-4o")
        finally:
            os.unlink(image_path)

    def test_multimodal_message_contains_image(self):
        image_path = self._make_temp_png()
        try:
            state = {
                "campaign_text": "Kampanya metni.",
                "image_path": image_path,
                "selected_model": "gpt-4o",
            }
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content="Hata bulunamadı.")
            captured_messages = []

            def capture_invoke(messages):
                captured_messages.extend(messages)
                return MagicMock(content="Hata bulunamadı.")

            mock_llm.invoke.side_effect = capture_invoke

            with patch("agents.visualcontrolagent.get_llm", return_value=mock_llm):
                from agents.visualcontrolagent import visual_auditor
                visual_auditor(state)

            human_msg = captured_messages[1]
            content_parts = human_msg.content
            types = [p["type"] for p in content_parts]
            assert "image_url" in types
        finally:
            os.unlink(image_path)


class TestVisualAgentStateSchema:
    def test_agent_state_has_required_keys(self):
        from agents.visualcontrolagent import AgentState
        annotations = AgentState.__annotations__
        required = {"campaign_text", "image_path", "selected_model", "visual_report", "is_visual_safe", "suggestions"}
        assert required.issubset(annotations.keys())
