# -*- coding: utf-8 -*-
"""
test_campaignvisualcreatoragent.py

Kampanya Görseli Oluşturma ajanının tüm bileşenlerini test eder.
Dış bağımlılıklar (LLM, OpenAI images API, HTTP) mock'lanır;
add_text_overlay_node Pillow ile gerçek PNG üretilerek test edilir.
"""
import base64
import io
import pytest
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────────────────────────────────────
# Yardımcılar
# ─────────────────────────────────────────────────────────────────────────────

def _make_png(w: int = 64, h: int = 64) -> bytes:
    """Geçerli küçük bir PNG üretir (Pillow'suz, salt-header yöntemi)."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color=(200, 200, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _base_state(**overrides) -> dict:
    """Geçerli bir CreatorState taslağı döndürür."""
    state = {
        "campaign_title": "Yaz Tatili Kredisi",
        "campaign_content": "%1.49 aylık faizle 12 ay vadeli kredi.",
        "campaign_segment": "25-45 yaş bireysel müşteriler",
        "campaign_date": "2026-08-31",
        "visual_description": "Deniz kenarında mutlu bir aile.",
        "campaign_criteria": "YMO: %24.36 | Minimum gelir: 5.000 TL | Aktif ING müşterisi",
        "example_image_bytes": None,
        "example_image_mime": None,
        "selected_model": "claude-sonnet-4-6",
        "dalle_prompt": "",
        "generated_image_url": "",
        "generated_image_bytes": None,
        "error": None,
    }
    state.update(overrides)
    return state


# ─────────────────────────────────────────────────────────────────────────────
# TestFmtDate
# ─────────────────────────────────────────────────────────────────────────────

class TestFmtDate:
    """
    _fmt_date(date_str) yardımcı fonksiyonunu test eder.

    ISO 8601 tarihini (YYYY-MM-DD) Türkçe görsel formatına (DD.MM.YYYY) çevirir.

    Test edilen senaryolar:
    - Geçerli ISO tarihinin DD.MM.YYYY formatına dönüşmesi
    - Boş string'in aynen döndürülmesi
    - Geçersiz formatın girdi olarak aynen geri dönmesi
    - Yıl-ay-gün sıralamasının doğru tersine çevrilmesi
    """

    def _fmt(self, s):
        from agents.campaignvisualcreatoragent import _fmt_date
        return _fmt_date(s)

    def test_iso_to_turkish_format(self):
        assert self._fmt("2026-08-31") == "31.08.2026"

    def test_empty_string_returns_empty(self):
        assert self._fmt("") == ""

    def test_invalid_format_returned_as_is(self):
        assert self._fmt("31/08/2026") == "31/08/2026"

    def test_year_is_last_component(self):
        result = self._fmt("2026-01-15")
        assert result.endswith("2026")

    def test_day_is_first_component(self):
        result = self._fmt("2026-03-07")
        assert result.startswith("07")


# ─────────────────────────────────────────────────────────────────────────────
# TestWrapLines
# ─────────────────────────────────────────────────────────────────────────────

class TestWrapLines:
    """
    _wrap_lines(text, font, max_px, draw) yardımcı fonksiyonunu test eder.

    Uzun metni piksel genişliğine göre satırlara böler.

    Test edilen senaryolar:
    - Kısa metnin tek satır olarak kalması
    - Boş metnin boş liste döndürmesi
    - Çok uzun metnin birden fazla satıra bölünmesi
    - Her satırın max_px sınırını aşmaması
    """

    def _make_draw_and_font(self):
        from PIL import Image, ImageDraw, ImageFont
        img  = Image.new("RGB", (400, 100))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
        except (IOError, OSError):
            font = ImageFont.load_default()
        return draw, font

    def test_short_text_single_line(self):
        from agents.campaignvisualcreatoragent import _wrap_lines
        draw, font = self._make_draw_and_font()
        lines = _wrap_lines("Kısa metin", font, 500, draw)
        assert len(lines) == 1

    def test_empty_text_returns_empty_list(self):
        from agents.campaignvisualcreatoragent import _wrap_lines
        draw, font = self._make_draw_and_font()
        lines = _wrap_lines("", font, 500, draw)
        assert lines == []

    def test_long_text_wrapped_to_multiple_lines(self):
        from agents.campaignvisualcreatoragent import _wrap_lines
        draw, font = self._make_draw_and_font()
        long_text = "Bu çok uzun bir metin cümlesidir ve " * 10
        lines = _wrap_lines(long_text.strip(), font, 200, draw)
        assert len(lines) > 1

    def test_each_line_within_max_width(self):
        from agents.campaignvisualcreatoragent import _wrap_lines
        draw, font = self._make_draw_and_font()
        max_px = 180
        text = "YMO yüzde yirmi dört nokta otuz altı aktif ING müşterisi zorunludur"
        lines = _wrap_lines(text, font, max_px, draw)
        for line in lines:
            w = draw.textbbox((0, 0), line, font=font)[2]
            assert w <= max_px


# ─────────────────────────────────────────────────────────────────────────────
# TestLoadFont
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadFont:
    """
    _load_font(size, bold) yardımcı fonksiyonunu test eder.

    Sistemden TrueType font yükler; bulamazsa glob ile arar.

    Test edilen senaryolar:
    - Dönen nesnenin bir ImageFont örneği olması
    - bold=True için farklı (veya aynı) nesne döndürülmesi
    - Farklı boyutlarda font yüklenebilmesi
    """

    def test_returns_font_object(self):
        from PIL import ImageFont
        from agents.campaignvisualcreatoragent import _load_font
        font = _load_font(14)
        assert isinstance(font, ImageFont.FreeTypeFont) or hasattr(font, "getbbox")

    def test_bold_font_loads(self):
        from agents.campaignvisualcreatoragent import _load_font
        font = _load_font(16, bold=True)
        assert font is not None

    def test_different_sizes_load(self):
        from agents.campaignvisualcreatoragent import _load_font
        for size in [10, 14, 20, 36]:
            font = _load_font(size)
            assert font is not None


# ─────────────────────────────────────────────────────────────────────────────
# TestBuildPromptNode
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildPromptNode:
    """
    build_prompt_node(state) LangGraph node fonksiyonunu test eder.

    Kampanya bilgilerinden gpt-image-1 için optimize edilmiş İngilizce
    DALL-E prompt üretir. Örnek görsel varsa multimodal mesaj gönderilir.

    Test edilen senaryolar:
    - LLM yanıtının dalle_prompt olarak state'e kaydedilmesi
    - error alanının None olarak dönmesi
    - Prompt 3900 karakteri aştığında kırpılması
    - Örnek görsel yokken text-only mesaj gönderilmesi
    - Örnek görsel varken image_url içeren multimodal mesaj gönderilmesi
    - Non-vision modelde örnek görsel gönderilmemesi
    """

    def _run(self, state: dict, llm_response: str = "A professional banking ad background.") -> dict:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content=llm_response)
        with patch("agents.campaignvisualcreatoragent.get_llm", return_value=mock_llm):
            from agents.campaignvisualcreatoragent import build_prompt_node
            return build_prompt_node(state)

    def test_dalle_prompt_stored_in_state(self):
        result = self._run(_base_state())
        assert result["dalle_prompt"] == "A professional banking ad background."

    def test_error_is_none_on_success(self):
        result = self._run(_base_state())
        assert result["error"] is None

    def test_long_prompt_truncated_at_3900_chars(self):
        long_response = "x" * 4100
        result = self._run(_base_state(), llm_response=long_response)
        assert len(result["dalle_prompt"]) <= 3900

    def test_text_only_message_without_example_image(self):
        captured = []
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = lambda msgs: (
            captured.extend(msgs) or MagicMock(content="prompt text")
        )
        state = _base_state(example_image_bytes=None)
        with patch("agents.campaignvisualcreatoragent.get_llm", return_value=mock_llm):
            from agents.campaignvisualcreatoragent import build_prompt_node
            build_prompt_node(state)
        human = captured[1]
        assert isinstance(human.content, str)

    def test_multimodal_message_with_example_image(self):
        captured = []
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = lambda msgs: (
            captured.extend(msgs) or MagicMock(content="prompt text")
        )
        state = _base_state(
            example_image_bytes=b"fake-image",
            example_image_mime="image/png",
            selected_model="claude-sonnet-4-6",
        )
        with patch("agents.campaignvisualcreatoragent.get_llm", return_value=mock_llm):
            from agents.campaignvisualcreatoragent import build_prompt_node
            build_prompt_node(state)
        human = captured[1]
        assert isinstance(human.content, list)
        types = [p["type"] for p in human.content]
        assert "image_url" in types

    def test_non_vision_model_ignores_example_image(self):
        captured = []
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = lambda msgs: (
            captured.extend(msgs) or MagicMock(content="prompt text")
        )
        state = _base_state(
            example_image_bytes=b"fake-image",
            example_image_mime="image/png",
            selected_model="deepseek-chat",
        )
        with patch("agents.campaignvisualcreatoragent.get_llm", return_value=mock_llm):
            from agents.campaignvisualcreatoragent import build_prompt_node
            build_prompt_node(state)
        human = captured[1]
        # Non-vision modelde görsel gönderilmez; içerik string kalır
        assert isinstance(human.content, str)


# ─────────────────────────────────────────────────────────────────────────────
# TestFetchImage
# ─────────────────────────────────────────────────────────────────────────────

class TestFetchImage:
    """
    _fetch_image(client, prompt) yardımcı fonksiyonunu test eder.

    gpt-image-1 API'sini çağırır; b64_json veya url üzerinden bytes döndürür.

    Test edilen senaryolar:
    - b64_json yanıtının doğru şekilde decode edilmesi
    - url yanıtında HTTP GET ile görsel indirilmesi
    - Ne b64_json ne url varsa ValueError fırlatılması
    """

    def test_b64_json_decoded_correctly(self):
        from agents.campaignvisualcreatoragent import _fetch_image
        raw = b"fake-image-data"
        b64 = base64.b64encode(raw).decode()
        item = MagicMock(b64_json=b64, url=None)
        client = MagicMock()
        client.images.generate.return_value = MagicMock(data=[item])
        result = _fetch_image(client, "test prompt")
        assert result == raw

    def test_url_downloads_image(self):
        from agents.campaignvisualcreatoragent import _fetch_image
        item = MagicMock(b64_json=None, url="http://fake.url/img.png")
        client = MagicMock()
        client.images.generate.return_value = MagicMock(data=[item])
        fake_response = MagicMock(content=b"downloaded-image")
        fake_response.raise_for_status = MagicMock()
        with patch("agents.campaignvisualcreatoragent._requests.get", return_value=fake_response):
            result = _fetch_image(client, "test prompt")
        assert result == b"downloaded-image"

    def test_raises_when_no_image_data(self):
        from agents.campaignvisualcreatoragent import _fetch_image
        item = MagicMock(b64_json=None, url=None)
        client = MagicMock()
        client.images.generate.return_value = MagicMock(data=[item])
        with pytest.raises(ValueError):
            _fetch_image(client, "test prompt")


# ─────────────────────────────────────────────────────────────────────────────
# TestGenerateImageNode
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateImageNode:
    """
    generate_image_node(state) LangGraph node fonksiyonunu test eder.

    gpt-image-1 API'sini kullanarak kampanya görseli üretir.

    Test edilen senaryolar:
    - Başarılı üretimde generated_image_bytes'ın dolu olması
    - Başarılı üretimde error alanının None olması
    - dalle_prompt boşsa hata mesajı döndürülmesi
    - API hatasında error alanının dolu olması
    - generated_image_bytes'ın None olmaması (bytes tipinde olması)
    """

    # OpenAI, generate_image_node içinde `from openai import OpenAI` ile lokal
    # import edildiğinden `openai.OpenAI` üzerinden patch edilmeli.
    _PATCH_TARGET = "openai.OpenAI"

    def _run(self, state: dict, image_bytes: bytes = b"png-data"):
        item = MagicMock(b64_json=base64.b64encode(image_bytes).decode(), url=None)
        mock_client = MagicMock()
        mock_client.images.generate.return_value = MagicMock(data=[item])
        with patch(self._PATCH_TARGET, return_value=mock_client):
            from agents.campaignvisualcreatoragent import generate_image_node
            return generate_image_node(state)

    def test_image_bytes_returned_on_success(self):
        state = _base_state(dalle_prompt="A clean banking background.")
        result = self._run(state, image_bytes=b"real-png")
        assert result["generated_image_bytes"] == b"real-png"

    def test_error_is_none_on_success(self):
        state = _base_state(dalle_prompt="A clean banking background.")
        result = self._run(state)
        assert result["error"] is None

    def test_empty_prompt_returns_error(self):
        state = _base_state(dalle_prompt="")
        with patch(self._PATCH_TARGET):
            from agents.campaignvisualcreatoragent import generate_image_node
            result = generate_image_node(state)
        assert result["error"] is not None
        assert result["generated_image_bytes"] is None

    def test_api_exception_stored_in_error(self):
        state = _base_state(dalle_prompt="valid prompt")
        mock_client = MagicMock()
        mock_client.images.generate.side_effect = Exception("API baglanti hatasi")
        with patch(self._PATCH_TARGET, return_value=mock_client):
            from agents.campaignvisualcreatoragent import generate_image_node
            result = generate_image_node(state)
        assert result["error"] is not None
        assert result["generated_image_bytes"] is None

    def test_returned_bytes_are_bytes_type(self):
        state = _base_state(dalle_prompt="prompt")
        result = self._run(state, image_bytes=b"data")
        assert isinstance(result["generated_image_bytes"], bytes)


# ─────────────────────────────────────────────────────────────────────────────
# TestAddTextOverlayNode
# ─────────────────────────────────────────────────────────────────────────────

class TestAddTextOverlayNode:
    """
    add_text_overlay_node(state) LangGraph node fonksiyonunu test eder.

    Üretilen arka plan görselinin üzerine başlık ve dipnot bantlarını
    Pillow ile programatik olarak çizer. Türkçe karakter desteği ve
    tarih formatı bu katmanda garantilenir.

    Test edilen senaryolar:
    - Geçerli PNG ile sonucun bytes döndürmesi
    - Dönen görselin orijinalden farklı olması (overlay eklendi)
    - generated_image_bytes None ise boş dict dönmesi
    - Türkçe karakterlerin (ş, ğ, ı, ö, ü, ç) çökmeden işlenmesi
    - Tarih alanı boş olduğunda hata fırlatılmaması
    - Kriterler alanı çok uzun olduğunda hata fırlatılmaması
    - Çıktının geçerli PNG formatında olması
    """

    def _run(self, **overrides) -> dict:
        png = _make_png(1024, 1024)
        state = _base_state(generated_image_bytes=png, **overrides)
        from agents.campaignvisualcreatoragent import add_text_overlay_node
        return add_text_overlay_node(state)

    def test_returns_bytes_on_valid_input(self):
        result = self._run()
        assert isinstance(result["generated_image_bytes"], bytes)

    def test_output_differs_from_input(self):
        png = _make_png(1024, 1024)
        state = _base_state(generated_image_bytes=png)
        from agents.campaignvisualcreatoragent import add_text_overlay_node
        result = add_text_overlay_node(state)
        assert result["generated_image_bytes"] != png

    def test_none_image_returns_empty_dict(self):
        state = _base_state(generated_image_bytes=None)
        from agents.campaignvisualcreatoragent import add_text_overlay_node
        result = add_text_overlay_node(state)
        assert result == {}

    def test_turkish_characters_do_not_raise(self):
        result = self._run(
            campaign_title="Özel Şube Teklifi — Çeyiz Kredisi",
            campaign_criteria="Şart: Aylık gelir ≥ 5.000 TL · Faiz: %1,49 · YMO: %24,36",
        )
        assert "generated_image_bytes" in result

    def test_empty_date_does_not_raise(self):
        result = self._run(campaign_date="")
        assert "generated_image_bytes" in result

    def test_very_long_criteria_does_not_raise(self):
        long_criteria = "Bu bir zorunlu koşul metnidir. " * 30
        result = self._run(campaign_criteria=long_criteria)
        assert "generated_image_bytes" in result

    def test_output_is_valid_png(self):
        from PIL import Image
        result = self._run()
        img = Image.open(io.BytesIO(result["generated_image_bytes"]))
        assert img.format == "PNG"

    def test_output_dimensions_preserved(self):
        from PIL import Image
        result = self._run()
        img = Image.open(io.BytesIO(result["generated_image_bytes"]))
        assert img.size == (1024, 1024)


# ─────────────────────────────────────────────────────────────────────────────
# TestCreatorStateSchema
# ─────────────────────────────────────────────────────────────────────────────

class TestCreatorStateSchema:
    """
    CreatorState TypedDict şemasını test eder.

    LangGraph iş akışı bu şemaya bağımlıdır; beklenmedik alan
    kaldırmaları veya yeniden adlandırmalar pipeline'ı sessizce bozar.

    Test edilen senaryolar:
    - Şemanın kampanya giriş alanlarını içermesi
    - Şemanın pipeline çıktı alanlarını içermesi
    - Şemanın hata alanını içermesi
    """

    def test_input_fields_present(self):
        from agents.campaignvisualcreatoragent import CreatorState
        keys = CreatorState.__annotations__
        for field in ("campaign_title", "campaign_content", "campaign_segment",
                      "campaign_date", "visual_description", "campaign_criteria",
                      "example_image_bytes", "example_image_mime", "selected_model"):
            assert field in keys, f"Eksik alan: {field}"

    def test_output_fields_present(self):
        from agents.campaignvisualcreatoragent import CreatorState
        keys = CreatorState.__annotations__
        for field in ("dalle_prompt", "generated_image_url", "generated_image_bytes"):
            assert field in keys, f"Eksik alan: {field}"

    def test_error_field_present(self):
        from agents.campaignvisualcreatoragent import CreatorState
        assert "error" in CreatorState.__annotations__
