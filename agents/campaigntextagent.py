# -*- coding: utf-8 -*-
import os
import sys
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
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END


load_dotenv()

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"
_DATA_DIR = Path(__file__).parent.parent / "data"

def _load_prompt(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8")

def _load_regulations(name: str) -> list[str]:
    lines = (_DATA_DIR / name).read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip()]

# --- 1. RAG: MEVZUAT VERİTABANI ---
regulations_data = _load_regulations("regulations_compliance.txt")

vectorstore = Chroma.from_texts(
    texts=regulations_data,
    embedding=OpenAIEmbeddings(),
    collection_name="bank_compliance"
)

# --- 2. AGENT STATE TANIMI ---
class AgentState(TypedDict):
    campaign_text: str
    channel: str
    selected_model: str
    compliance_report: str
    is_safe: bool
    suggestions: List[str]

# --- 3. COMPLIANCE AGENT LOGIC ---
def compliance_checker(state: AgentState):
    llm = get_llm(state.get("selected_model", "gpt-4o"))

    safe_text = sanitize_input(state['campaign_text'])
    wrapped_text = wrap_user_content(safe_text)

    docs = vectorstore.similarity_search(safe_text, k=2)
    context = "\n".join([d.page_content for d in docs])
    channel = state.get('channel', 'Belirtilmedi')

    template = _load_prompt("compliance.txt")
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
    }

# --- 4. LANGGRAPH AKIŞINI KURMA ---
workflow = StateGraph(AgentState)

workflow.add_node("check_compliance", compliance_checker)
workflow.set_entry_point("check_compliance")
workflow.add_edge("check_compliance", END)

app = workflow.compile()

# --- 5. TEST ÇALIŞTIRMASI ---
if __name__ == "__main__":
    test_text = "Hemen başvuran herkese bedava kredi! Kesin onay garantisiyle parası anında cebinde."
    
    inputs = {"campaign_text": test_text}
    result = app.invoke(inputs)
    
    print("--- KAMPANYA DENETİM RAPORU ---")
    print(result["compliance_report"])