# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langgraph.graph import StateGraph, END

load_dotenv()

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
    llm = ChatOpenAI(model=state.get("selected_model", "gpt-4o"), temperature=0)
    documents = state.get("legal_documents") or []

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

    hits = vs.similarity_search(state["campaign_text"], k=5)
    legal_context = "\n\n".join([d.page_content for d in hits])

    prompt = f"""
Sen bir Banka Hukuk ve Strateji Denetçisisin.
Aşağıdaki kampanya metnini, sana verilen yasal kaynaklara göre denetle.

YASAL KAYNAKLAR:
{legal_context}

KAMPANYA METNİ:
{state['campaign_text']}

GÖREVİN:
1. Kampanya metninde yasal kaynaklara aykırı ifade var mı?
2. Tüketiciyi koruma açısından risk oluşturan bir durum var mı?
3. Yasal Uygunluk Puanını (0-100) belirle.

Yanıtını şu başlıklarla ver:
- Mevzuat İhlalleri:
- Risk Seviyesi (Düşük/Orta/Yüksek):
- Gerekli Yasal Düzenlemeler:
- Final Uygunluk Puanı: <sadece sayı>
"""

    response = llm.invoke(prompt)
    content = response.content

    # Puanı metinden parse et
    score = 85
    for line in content.splitlines():
        if "Final Uygunluk Puanı" in line:
            digits = "".join(filter(str.isdigit, line.split(":")[-1]))
            if digits:
                score = min(100, max(0, int(digits)))
            break

    return {"legal_audit_report": content, "final_score": score}


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
