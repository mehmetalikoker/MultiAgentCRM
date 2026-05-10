# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langgraph.graph import StateGraph, END

load_dotenv()

llm = ChatOpenAI(model="gpt-4o", temperature=0)

class AgentState(TypedDict):
    campaign_text: str
    image_path: str
    compliance_report: str
    visual_report: str
    legal_audit_report: str
    is_safe: bool
    is_visual_safe: bool
    final_score: int
    suggestions: List[str]

# BDDK mevzuat verisi (mock)
legal_regulations = [
    "BDDK yönetmeliğine göre faiz oranı kampanya görselinde en az 10 punto büyüklüğünde belirtilmelidir.",
    "Tüketiciyi Koruma Kanunu: Kampanya bitiş tarihi açıkça belirtilmek zorundadır.",
    "Yanıltıcı reklam içeren kampanyalar BDDK tarafından 100.000 TL'ye kadar cezalandırılabilir.",
    "Zorunlu açıklamalar (masraf, komisyon, vb.) kampanya metninde yer almalıdır."
]

vectorstore_legal = Chroma.from_texts(
    texts=legal_regulations,
    embedding=OpenAIEmbeddings(),
    collection_name="legal_compliance"
)

workflow = StateGraph(AgentState)

def legal_strategy_auditor(state: AgentState):
    # RAG: BDDK ve Yasal Mevzuat dosyasından ilgili kısımları çekiyoruz
    # vectorstore_legal: BDDK dökümanlarının olduğu ayrı bir koleksiyon olduğunu varsayalım
    legal_docs = vectorstore_legal.similarity_search(state['campaign_text'], k=5)
    legal_context = "\n".join([d.page_content for d in legal_docs])
    
    prompt = f"""
    Sen bir Banka Hukuk ve Strateji Denetçisisin. 
    Eldeki kampanya materyallerini BDDK ve Yasal Mevzuat dosyasındaki kurallarla kıyasla.
    
    YASAL KAYNAKLAR:
    {legal_context}
    
    METİN ANALİZİ: {state['compliance_report']}
    GÖRSEL ANALİZİ: {state['visual_report']}
    
    GÖREVİN:
    1. Metin veya görselde BDDK yönetmeliklerine aykırı bir durum var mı? 
       (Örn: Faiz oranının font büyüklüğü, yanıltıcı kampanya bitiş tarihi, zorunlu açıklamaların eksikliği)
    2. Mevzuattaki 'tüketiciyi koruma' maddeleri ihlal ediliyor mu?
    3. Hem metin hem görselin toplam 'Yasal Uygunluk Puanını' (0-100) belirle.
    
    Yanıtını şu başlıklarla ver:
    - Mevzuat İhlalleri:
    - Risk Seviyesi (Düşük/Orta/Yüksek):
    - Gerekli Yasal Düzenlemeler:
    - Final Uygunluk Puanı:
    """

    response = llm.invoke(prompt)
    
    return {
        "legal_audit_report": response.content,
        "final_score": 85
    }

workflow.add_node("legal_audit", legal_strategy_auditor)
workflow.set_entry_point("legal_audit")
workflow.add_edge("legal_audit", END)

if __name__ == "__main__":
    app = workflow.compile()
    result = app.invoke({
        "campaign_text": "Hemen başvuran herkese masrafsız kredi!",
        "compliance_report": "Metin uygun bulundu.",
        "visual_report": "Görsel uygun bulundu."
    })
    print("--- HUKUK VE STRATEJİ DENETİM RAPORU ---")
    print(result["legal_audit_report"])