# -*- coding: utf-8 -*-
import sys
import hashlib
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from agents.llm_factory import get_llm
from agents.security import sanitize_input, wrap_user_content
from agents.output_parser import parse_legal_response
from langchain_community.vectorstores import Chroma
from langgraph.graph import StateGraph, END

load_dotenv()

# Versiyon önbelleği — mevzuat değiştiğinde otomatik yeniden oluşturulur
_fallback_vs_cache: dict = {"hash": None, "store": None}


def _get_fallback_vectorstore() -> Chroma:
    from user.prompt_store import get_prompt
    content = get_prompt("regulations_legal", "data/regulations_legal.txt")
    texts = [l.strip() for l in content.splitlines() if l.strip()]
    h = hashlib.md5(content.encode()).hexdigest()
    if _fallback_vs_cache["hash"] != h:
        _fallback_vs_cache["store"] = Chroma.from_texts(
            texts=texts,
            embedding=OpenAIEmbeddings(),
            collection_name="fallback_legal",
        )
        _fallback_vs_cache["hash"] = h
    return _fallback_vs_cache["store"]


class AgentState(TypedDict):
    campaign_text: str
    selected_model: str
    legal_documents: List[str]
    legal_audit_report: str
    legal_parsed: dict | None
    final_score: int


workflow = StateGraph(AgentState)


def legal_strategy_auditor(state: AgentState):
    from user.prompt_store import get_prompt

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
        vs = _get_fallback_vectorstore()

    hits = vs.similarity_search(safe_text, k=5)
    legal_context = "\n\n".join([d.page_content for d in hits])

    template = get_prompt("legal_strategy", "prompts/legal_strategy.txt")
    prompt = template.format(legal_context=legal_context, campaign_text=wrapped_text)

    response = llm.invoke(prompt)
    content = response.content
    parsed, score = parse_legal_response(content)
    return {
        "legal_audit_report": content,
        "legal_parsed": parsed,
        "final_score": score,
    }


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
