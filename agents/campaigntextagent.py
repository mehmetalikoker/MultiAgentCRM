# -*- coding: utf-8 -*-
import os
import sys
import hashlib
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from agents.llm_factory import get_llm
from agents.security import sanitize_input, wrap_user_content
from agents.output_parser import parse_compliance_response
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

load_dotenv()

_DATA_DIR = Path(__file__).parent.parent / "data"

# Versiyon önbelleği — mevzuat değiştiğinde otomatik yeniden oluşturulur
_vs_cache: dict = {"hash": None, "store": None}


def _get_vectorstore() -> Chroma:
    from user.prompt_store import get_prompt
    content = get_prompt("regulations_compliance", "data/regulations_compliance.txt")
    texts = [l.strip() for l in content.splitlines() if l.strip()]
    h = hashlib.md5(content.encode()).hexdigest()
    if _vs_cache["hash"] != h:
        _vs_cache["store"] = Chroma.from_texts(
            texts=texts,
            embedding=OpenAIEmbeddings(),
            collection_name="bank_compliance",
        )
        _vs_cache["hash"] = h
    return _vs_cache["store"]


class AgentState(TypedDict):
    campaign_text: str
    channel: str
    selected_model: str
    compliance_report: str
    is_safe: bool
    suggestions: List[str]
    injection_detected: bool


def compliance_checker(state: AgentState):
    from user.prompt_store import get_prompt

    llm = get_llm(state.get("selected_model", "gpt-4o"))

    safe_text, injection_detected = sanitize_input(state['campaign_text'])
    wrapped_text = wrap_user_content(safe_text)

    vectorstore = _get_vectorstore()
    docs = vectorstore.similarity_search(safe_text, k=2)
    context = "\n".join([d.page_content for d in docs])
    channel = state.get('channel', 'Belirtilmedi')

    template = get_prompt("compliance", "prompts/compliance.txt")
    prompt = ChatPromptTemplate.from_template(template)

    chain = prompt | llm
    response = chain.invoke({
        "context": context,
        "campaign_text": wrapped_text,
        "channel": channel,
    })

    is_safe, suggestions = parse_compliance_response(response.content)
    return {
        "compliance_report": response.content,
        "is_safe": is_safe,
        "suggestions": suggestions,
        "injection_detected": injection_detected,
    }


workflow = StateGraph(AgentState)
workflow.add_node("check_compliance", compliance_checker)
workflow.set_entry_point("check_compliance")
workflow.add_edge("check_compliance", END)

app = workflow.compile()

if __name__ == "__main__":
    test_text = "Hemen başvuran herkese bedava kredi! Kesin onay garantisiyle parası anında cebinde."
    result = app.invoke({"campaign_text": test_text})
    print("--- KAMPANYA DENETİM RAPORU ---")
    print(result["compliance_report"])
