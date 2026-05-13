# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

import base64
import os
from typing import TypedDict, List
from dotenv import load_dotenv
from agents.llm_factory import get_llm
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

load_dotenv()

class AgentState(TypedDict):
    campaign_text: str
    image_path: str
    selected_model: str
    compliance_report: str
    visual_report: str
    is_safe: bool
    is_visual_safe: bool
    suggestions: List[str]

workflow = StateGraph(AgentState)

# --- 1. GÖRSEL İŞLEME YARDIMCISI ---
def encode_image(image_path: str):
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime_type

# --- 2. VISUAL AUDITOR AGENT LOGIC ---
def visual_auditor(state: AgentState):
    llm = get_llm(state.get("selected_model", "gpt-4o"))
    base64_image, mime_type = encode_image(state["image_path"])

    prompt = f"""
Sen bir Banka Görsel Denetçisisin.
Sana verilen kampanya görselini ve onaylanmış kampanya metnini karşılaştır.

ONAYLANAN METİN: {state['campaign_text']}

GÖREVİN:
1. Görsel üzerindeki metinleri oku (OCR) ve onaylanan metinle tutarlı mı bak.
2. Banka logosu görünüyor mu ve konumu uygun mu?
3. Renk paleti ve tasarım genel bankacılık ciddiyetine uygun mu?
4. Görselde yanıltıcı bir öğe (metinden farklı bir faiz oranı vb.) var mı?

Yanıtını şu formatta ver:
- Görsel Analizi: (Genel açıklama)
- Tutarsızlıklar: (Varsa metin-görsel farkları)
- Tasarım Önerileri: (Daha iyi olması için öneriler)
"""

    messages = [
        SystemMessage(content="Sen uzman bir banka görsel denetçisisin."),
        HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}},
        ]),
    ]

    response = llm.invoke(messages)

    return {
        "visual_report": response.content,
        "is_visual_safe": "hata bulunamadı" in response.content.lower()
    }

# --- 3. LANGGRAPH AKIŞI ---
workflow.add_node("check_visual", visual_auditor)
workflow.set_entry_point("check_visual")
workflow.add_edge("check_visual", END)

app = workflow.compile()

if __name__ == "__main__":
    print("Visual Control Agent hazır. Görsel denetimi için image_path sağlayın.")