# -*- coding: utf-8 -*-
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END


load_dotenv()

# --- 1. RAG: MEVZUAT VERİTABANI (MOCK) ---
# Gerçekte burası PDF'lerden veya banka rehberinden beslenecek
regulations_data = [
    "Bankacılık kampanyalarında 'Bedava' kelimesi kullanılamaz, 'Masrafsız' veya 'Ücretsiz' denmelidir.",
    "Faiz oranları belirtilirken yıllık maliyet oranı mutlaka parantez içinde verilmelidir.",
    "Kredi kampanyalarında 'Kesin onay' veya 'Anında hesapta' gibi yanıltıcı ifadeler yasaktır.",
    "Kampanya bitiş tarihi ve katılım koşulları metinde açıkça belirtilmelidir."
]

vectorstore = Chroma.from_texts(
    texts=regulations_data,
    embedding=OpenAIEmbeddings(),
    collection_name="bank_compliance"
)

# --- 2. AGENT STATE TANIMI ---
class AgentState(TypedDict):
    campaign_text: str
    channel: str
    compliance_report: str
    is_safe: bool
    suggestions: List[str]

# --- 3. COMPLIANCE AGENT LOGIC ---
llm = ChatOpenAI(model="gpt-4o", temperature=0)

def compliance_checker(state: AgentState):
    docs = vectorstore.similarity_search(state['campaign_text'], k=2)
    context = "\n".join([d.page_content for d in docs])
    channel = state.get('channel', 'Belirtilmedi')

    prompt = ChatPromptTemplate.from_template("""
    Sen bir banka uyum (compliance) uzmanısın.
    Aşağıdaki kampanya metnini, verilen bankacılık kurallarına göre denetle.

    KANAL: {channel}
    KURALLAR:
    {context}

    KAMPANYA METNİ:
    {campaign_text}

    Yanıtını şu JSON formatında ver:
    {{
        "is_safe": bool (Hata yoksa true),
        "report": "Hataların analizi",
        "suggestions": ["Öneri 1", "Öneri 2"]
    }}
    """)

    chain = prompt | llm
    response = chain.invoke({"context": context, "campaign_text": state['campaign_text'], "channel": channel})
    
    # Not: Gerçekte bir JSON parser kullanmak daha sağlıklı olur
    # Şimdilik doğrudan state'e yazıyoruz
    return {
        "compliance_report": response.content,
        "is_safe": "true" in response.content.lower()
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