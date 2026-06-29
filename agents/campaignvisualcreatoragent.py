# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

import base64
import io
import os
import textwrap
import requests as _requests
from typing import TypedDict
from dotenv import load_dotenv
from agents.llm_factory import get_llm
from agents.security import sanitize_input, build_safe_system_message
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

load_dotenv()

_NON_VISION_MODELS = {"gpt-3.5-turbo", "deepseek-chat"}

# ING marka renkleri
_ING_ORANGE  = (255, 98, 0)
_DARK_BG     = (18, 18, 18)
_WHITE       = (255, 255, 255)
_LIGHT_GRAY  = (210, 215, 220)
_ORANGE_TEXT = (255, 130, 40)


class CreatorState(TypedDict):
    campaign_title: str
    campaign_content: str
    campaign_segment: str
    campaign_date: str
    visual_description: str
    campaign_criteria: str
    example_image_bytes: bytes | None
    example_image_mime: str | None
    selected_model: str
    dalle_prompt: str
    generated_image_url: str
    generated_image_bytes: bytes | None
    error: str | None


# ── Font yardımcısı ────────────────────────────────────────────────────────────

def _load_font(size: int, bold: bool = False):
    """
    Türkçe karakter desteği olan TrueType font yükler.
    Sırasıyla Windows → Linux → macOS yollarını dener.
    Hiçbiri bulunamazsa sistemdeki ilk .ttf dosyasını kullanır.
    """
    import glob
    from PIL import ImageFont

    candidates = (
        [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ] if bold else [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue

    # Son çare: sistemdeki herhangi bir TTF bul
    for pattern in ["C:/Windows/Fonts/*.ttf", "/usr/share/fonts/**/*.ttf"]:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            try:
                return ImageFont.truetype(matches[0], size)
            except (IOError, OSError):
                continue

    return ImageFont.load_default()


def _fmt_date(date_str: str) -> str:
    """'2026-07-15' → '15.07.2026' Türkçe formatı."""
    try:
        from datetime import datetime
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return date_str


def _wrap_lines(text: str, font, max_px: int, draw) -> list[str]:
    """Metni piksel genişliğine göre satırlara böler."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        w = draw.textbbox((0, 0), test, font=font)[2]
        if w <= max_px:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _line_height(draw, text: str, font) -> int:
    """Tek satırın piksel yüksekliğini döndürür."""
    bbox = draw.textbbox((0, 0), text or "A", font=font)
    return bbox[3] - bbox[1]


# ── Node 1: DALL-E prompt oluştur ─────────────────────────────────────────────

def build_prompt_node(state: CreatorState):
    from user.prompt_store import get_prompt

    model = state.get("selected_model", "claude-sonnet-4-6")
    llm = get_llm(model)

    title, _   = sanitize_input(state.get("campaign_title", ""))
    content, _ = sanitize_input(state.get("campaign_content", ""))
    segment, _ = sanitize_input(state.get("campaign_segment", ""))
    date_str   = state.get("campaign_date", "")
    visual_desc, _ = sanitize_input(state.get("visual_description", ""))
    criteria, _ = sanitize_input(state.get("campaign_criteria", ""))

    has_example = (
        state.get("example_image_bytes") is not None
        and model not in _NON_VISION_MODELS
    )
    example_note = (
        "Ek olarak bir örnek görsel sağlanmıştır. Bu görselin stilini ve düzenini referans al, ancak metin ekleme."
        if has_example else ""
    )

    template = get_prompt("visual_creator_prompt", "prompts/visual_creator_prompt.txt")
    prompt_text = template.format(
        title=title,
        content=content,
        segment=segment,
        date=date_str,
        visual_description=visual_desc,
        criteria=criteria,
        example_note=example_note,
    )

    if has_example:
        b64  = base64.b64encode(state["example_image_bytes"]).decode("utf-8")
        mime = state.get("example_image_mime", "image/jpeg")
        human_msg = HumanMessage(content=[
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ])
    else:
        human_msg = HumanMessage(content=prompt_text)

    response = llm.invoke([
        SystemMessage(content=build_safe_system_message()),
        human_msg,
    ])
    dalle_prompt = response.content.strip()
    if len(dalle_prompt) > 3900:
        dalle_prompt = dalle_prompt[:3900]

    return {"dalle_prompt": dalle_prompt, "error": None}


# ── Node 2: Görsel üret ────────────────────────────────────────────────────────

def _fetch_image(client, prompt: str) -> bytes:
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        n=1,
        size="1024x1024",
    )
    item = response.data[0]
    if getattr(item, "b64_json", None):
        return base64.b64decode(item.b64_json)
    url = getattr(item, "url", None)
    if url:
        r = _requests.get(url, timeout=60)
        r.raise_for_status()
        return r.content
    raise ValueError("API yanıtında görsel verisi bulunamadı.")


def generate_image_node(state: CreatorState):
    dalle_prompt = state.get("dalle_prompt", "")
    if not dalle_prompt:
        return {"error": "Görsel prompt oluşturulamadı.", "generated_image_bytes": None}

    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        image_bytes = _fetch_image(client, dalle_prompt)
        return {"generated_image_url": "", "generated_image_bytes": image_bytes, "error": None}
    except Exception as e:
        return {"generated_image_bytes": None, "error": str(e)}


# ── Node 3: Metin overlay ekle ────────────────────────────────────────────────

def add_text_overlay_node(state: CreatorState):
    """
    Üretilen arka plan görselinin üzerine başlık ve dipnot bantlarını
    Pillow ile programatik olarak çizer.
    Türkçe karakter desteği garantili; yazım hatası sıfır.
    """
    image_bytes = state.get("generated_image_bytes")
    if not image_bytes:
        return {}

    from PIL import Image, ImageDraw

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    W, H = img.size          # 1024 × 1024
    PAD      = 22
    HEADER_H = 88
    FOOTER_H = 160

    # ── Şeffaf bantlar oluştur ve görsel ile birleştir ────────────────────────
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    ov.rectangle([(0, 0),            (W, HEADER_H)],   fill=(*_ING_ORANGE, 225))
    ov.rectangle([(0, H - FOOTER_H), (W, H)],           fill=(*_DARK_BG,   220))
    img  = Image.alpha_composite(img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── Başlık bandı ─────────────────────────────────────────────────────────
    title      = state.get("campaign_title", "").strip()
    title_font = _load_font(36, bold=True)
    t_lines    = _wrap_lines(title, title_font, W - PAD * 2, draw)
    ty = (HEADER_H - _line_height(draw, title, title_font) * min(len(t_lines), 2)) // 2
    ty = max(ty, 8)
    for line in t_lines[:2]:
        draw.text((PAD, ty), line, font=title_font, fill=_WHITE)
        ty += _line_height(draw, line, title_font) + 5

    # ── Dipnot bandı ─────────────────────────────────────────────────────────
    raw_date = state.get("campaign_date", "")
    date_str  = _fmt_date(str(raw_date)) if raw_date else ""
    criteria  = state.get("campaign_criteria", "").strip()

    # Dipnot satırlarını birleştir: tarih + kriterler
    dipnot_parts = []
    if date_str:
        dipnot_parts.append(f"Kampanya bitiş tarihi: {date_str}")
    if criteria:
        dipnot_parts.append(criteria)
    dipnot_full = "  |  ".join(dipnot_parts)

    label_font = _load_font(14, bold=True)
    fn_font    = _load_font(13, bold=False)
    lh_label   = _line_height(draw, "A", label_font)
    lh_fn      = _line_height(draw, "A", fn_font)

    fy = H - FOOTER_H + PAD

    # "* Önemli bilgiler:" etiketi
    draw.text((PAD, fy), "* Önemli Bilgiler:", font=label_font, fill=_ORANGE_TEXT)
    fy += lh_label + 6

    # Dipnot içeriği satır satır
    fn_lines = _wrap_lines(dipnot_full, fn_font, W - PAD * 2, draw)
    max_lines = (FOOTER_H - lh_label - PAD * 2 - 12) // (lh_fn + 3)
    for line in fn_lines[:max(max_lines, 4)]:
        draw.text((PAD, fy), line, font=fn_font, fill=_LIGHT_GRAY)
        fy += lh_fn + 3
        if fy > H - 10:
            break

    # ── PNG kaydet ────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return {"generated_image_bytes": buf.getvalue()}


# ── LangGraph iş akışı ────────────────────────────────────────────────────────

workflow = StateGraph(CreatorState)
workflow.add_node("build_prompt",     build_prompt_node)
workflow.add_node("generate_image",   generate_image_node)
workflow.add_node("add_text_overlay", add_text_overlay_node)
workflow.set_entry_point("build_prompt")
workflow.add_edge("build_prompt",     "generate_image")
workflow.add_edge("generate_image",   "add_text_overlay")
workflow.add_edge("add_text_overlay", END)

app = workflow.compile()
