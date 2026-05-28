# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from agents.llm_factory import get_llm
from agents.security import sanitize_input, wrap_user_content
from agents.output_parser import parse_legal_score
from langchain_community.vectorstores import Chroma
from langgraph.graph import StateGraph, END

load_dotenv()

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

def _load_prompt(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8")

# Fallback: dosya yüklenmezse kullanılacak mock mevzuat
_fallback_regulations = [
    "BDDK yönetmeliğine göre faiz oranı kampanya görselinde en az 10 punto büyüklüğünde belirtilmelidir.",
    "Tüketiciyi Koruma Kanunu: Kampanya bitiş tarihi açıkça belirtilmek zorundadır.",
    "Yanıltıcı reklam içeren kampanyalar BDDK tarafından 100.000 TL'ye kadar cezalandırılabilir.",
    "Zorunlu açıklamalar (masraf, komisyon, vb.) kampanya metninde yer almalıdır.",
]

class AgentState(TypedDict):
    campaign_text: str
    selected_model: str
    legal_documents: List[str]
    legal_audit_report: str
    final_score: int

workflow = StateGraph(AgentState)

def legal_strategy_auditor(state: AgentState):
    llm = get_llm(state.get("selected_model", "gpt-4o"))
    documents = state.get("legal_documents") or []

    safe_text = sanitize_input(state["campaign_text"])
    wrapped_text = wrap_user_content(safe_text)

    if documents:
        vs = Chroma.from_texts(
            texts=documents,
            embedding=OpenAIEmbeddings(),
            collection_name="dynamic_legal",
        )
    else:
        vs = Chroma.from_texts(
            texts=_fallback_regulations,
            embedding=OpenAIEmbeddings(),
            collection_name="fallback_legal",
        )

    hits = vs.similarity_search(safe_text, k=5)
    legal_context = "\n\n".join([d.page_content for d in hits])

    template = _load_prompt("legal_strategy.txt")
    prompt = template.format(legal_context=legal_context, campaign_text=wrapped_text)

    response = llm.invoke(prompt)
    content = response.content
    return {"legal_audit_report": content, "final_score": parse_legal_score(content)}


workflow.add_node("legal_audit", legal_strategy_auditor)
workflow.set_entry_point("legal_audit")
workflow.add_edge("legal_audit", END)

app = workflow.compile()

if __name__ == "__main__":
    result = app.invoke({
        "campaign_text": "Hemen başvuran herkese masrafsız kredi!",
        "legal_documents": [],
    })
    print("--- HUKUK VE STRATEJİ DENETİM RAPORU ---")
    print(result["legal_audit_report"])
