# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

import base64
from pathlib import Path
from typing import TypedDict, List
from dotenv import load_dotenv
from agents.llm_factory import get_llm
from agents.security import sanitize_input, wrap_user_content, build_safe_system_message
from agents.output_parser import parse_visual_response
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

load_dotenv()

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

def _load_prompt(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8")

class AgentState(TypedDict):
    campaign_text: str
    image_bytes: bytes
    image_mime: str
    selected_model: str
    compliance_report: str
    visual_report: str
    is_safe: bool
    is_visual_safe: bool
    suggestions: List[str]

workflow = StateGraph(AgentState)

# --- 1. GÖRSEL İŞLEME YARDIMCISI ---
def encode_image(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")

# --- 2. VISUAL AUDITOR AGENT LOGIC ---
def visual_auditor(state: AgentState):
    llm = get_llm(state.get("selected_model", "gpt-4o"))
    base64_image = encode_image(state["image_bytes"])
    mime_type = state["image_mime"]

    safe_text = sanitize_input(state["campaign_text"])
    wrapped_text = wrap_user_content(safe_text)

    template = _load_prompt("visual_control.txt")
    prompt = template.format(campaign_text=wrapped_text)

    messages = [
        SystemMessage(content=build_safe_system_message()),
        HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}},
        ]),
    ]

    response = llm.invoke(messages)

    return {
        "visual_report": response.content,
        "is_visual_safe": parse_visual_response(response.content),
    }

# --- 3. LANGGRAPH AKIŞI ---
workflow.add_node("check_visual", visual_auditor)
workflow.set_entry_point("check_visual")
workflow.add_edge("check_visual", END)

app = workflow.compile()

if __name__ == "__main__":
    print("Visual Control Agent hazır. Görsel denetimi için image_path sağlayın.")