# -*- coding: utf-8 -*-
import os
import html
import tempfile
import streamlit as st
from agents.audit_logger import log_audit

_RISK_COLOR = {
    "KRİTİK": "#e74c3c",
    "YÜKSEK": "#e67e22",
    "ORTA":   "#f1c40f",
    "DÜŞÜK":  "#2ecc71",
}

_ONCELIK_COLOR = {
    "Acil":   "#e74c3c",
    "Yüksek": "#e67e22",
    "Orta":   "#3498db",
}


def _score_color(score: int) -> str:
    if score >= 70:
        return "#2ecc71"
    if score >= 40:
        return "#e67e22"
    return "#e74c3c"


def _risk_badge(seviye: str) -> str:
    color = _RISK_COLOR.get(seviye.upper(), "#888")
    return (
        f"<span style='background:{color};color:#fff;padding:2px 8px;"
        f"border-radius:4px;font-size:0.78rem;font-weight:700;'>{seviye}</span>"
    )


def render(selected_model: str):
    st.header("Hukuk & Strateji Denetimi")
    st.markdown("Hukuki belgeleri yükleyin; kampanya metni mevzuat ve strateji açısından denetlenecektir.")

    uploaded_docs = st.file_uploader(
        "Hukuki Belgeler — PDF veya TXT (birden fazla dosya seçebilirsiniz)",
        type=["pdf", "txt"],
        accept_multiple_files=True,
    )
    if uploaded_docs:
        st.success(f"✅ {len(uploaded_docs)} belge yüklendi: {', '.join(f.name for f in uploaded_docs)}")

    legal_campaign_text = st.text_area(
        "Kampanya Metni",
        placeholder="Hukuki açıdan denetlenecek kampanya metnini girin...",
        height=140,
    )

    if not st.button("Hukuki Denetim Yap", type="primary"):
        return

    if not legal_campaign_text.strip():
        st.warning("Lütfen kampanya metnini girin.")
        return

    with st.spinner("Belgeler işleniyor, hukuki denetim yapılıyor..."):
        try:
            legal_chunks: list[str] = []

            if uploaded_docs:
                from langchain_community.document_loaders import PyPDFLoader, TextLoader
                from langchain.text_splitter import RecursiveCharacterTextSplitter
                splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

                for doc_file in uploaded_docs:
                    suffix = os.path.splitext(doc_file.name)[1].lower()
                    tmp_path = None
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(doc_file.read())
                            tmp_path = tmp.name
                        loader = PyPDFLoader(tmp_path) if suffix == ".pdf" else TextLoader(tmp_path, encoding="utf-8")
                        chunks = splitter.split_documents(loader.load())
                        legal_chunks.extend([c.page_content for c in chunks])
                    finally:
                        if tmp_path and os.path.exists(tmp_path):
                            os.unlink(tmp_path)

            from agents.legalstrategyagent import app as legal_app
            result = legal_app.invoke({
                "campaign_text": legal_campaign_text,
                "legal_documents": legal_chunks,
                "selected_model": selected_model,
            })

            score  = result.get("final_score", 0)
            report = result.get("legal_audit_report", "")
            parsed = result.get("legal_parsed")

            st.markdown("---")
            st.subheader("Hukuki Denetim Sonucu")

            if uploaded_docs:
                st.caption(f"Kaynak belgeler: {', '.join(f.name for f in uploaded_docs)}")
            else:
                st.caption("Belge yüklenmedi — varsayılan BDDK/TKHK mevzuatı kullanıldı.")

            # ── Puan + risk + özet ────────────────────────────────────────────
            col_score, col_meta = st.columns([1, 3])

            with col_score:
                st.markdown(
                    f"<div style='text-align:center;padding:20px 0;'>"
                    f"<div style='font-size:3rem;font-weight:900;color:{_score_color(score)};'>"
                    f"{score}</div>"
                    f"<div style='color:#888;font-size:0.85rem;'>/ 100 Uygunluk</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            with col_meta:
                if parsed:
                    risk = parsed.get("risk_seviyesi", "")
                    if risk:
                        st.markdown(
                            f"**Genel Risk Seviyesi:** {_risk_badge(risk)}",
                            unsafe_allow_html=True,
                        )
                    if parsed.get("ozet"):
                        st.info(parsed["ozet"])

                    # Kriter puanları
                    kriterler = parsed.get("kriter_puanlari", {})
                    if kriterler:
                        kriter_labels = {
                            "zorunlu_beyanlar":      "Zorunlu Beyanlar (%30)",
                            "yaniltici_ifade_yoklugu": "Yanıltıcı İfade Yokluğu (%25)",
                            "tuketici_koruma":       "Tüketici Koruma (%20)",
                            "kvkk_elektronik_ileti": "KVKK/Elektronik İleti (%15)",
                            "etik_ve_itibar":        "Etik & İtibar (%10)",
                        }
                        with st.expander("📊 Kriter Bazlı Puanlar", expanded=False):
                            for key, label in kriter_labels.items():
                                val = kriterler.get(key, "—")
                                if isinstance(val, (int, float)):
                                    color = _score_color(int(val))
                                    st.markdown(
                                        f"<div style='display:flex;justify-content:space-between;"
                                        f"margin-bottom:4px;'>"
                                        f"<span style='font-size:0.88rem;'>{label}</span>"
                                        f"<span style='font-weight:700;color:{color};'>{val}/100</span>"
                                        f"</div>",
                                        unsafe_allow_html=True,
                                    )
                                    st.progress(int(val) / 100)

            # ── Mevzuat ihlalleri ────────────────────────────────────────────
            ihlaller = parsed.get("mevzuat_ihlalleri", []) if parsed else []
            if ihlaller:
                with st.expander(f"⚖️ Mevzuat İhlalleri ({len(ihlaller)})", expanded=True):
                    for item in ihlaller:
                        sev = item.get("risk_seviyesi", "ORTA").upper()
                        color = _RISK_COLOR.get(sev, "#888")
                        st.markdown(
                            f"<div style='background:#fafafa;border-left:4px solid {color};"
                            f"padding:12px 16px;border-radius:6px;margin-bottom:10px;'>"
                            f"<div style='margin-bottom:4px;'>{_risk_badge(sev)} "
                            f"<strong>{html.escape(item.get('ihlal',''))}</strong></div>"
                            f"<div style='font-size:0.85rem;color:#555;margin-bottom:2px;'>"
                            f"📋 <em>{html.escape(item.get('kanun_maddesi',''))}</em></div>"
                            f"<div style='font-size:0.85rem;color:#c0392b;'>"
                            f"⚠️ {html.escape(item.get('yaptirim_riski',''))}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

            # ── Strateji önerileri ───────────────────────────────────────────
            oneriler = parsed.get("strateji_onerileri", []) if parsed else []
            if oneriler:
                with st.expander(f"💡 Strateji Önerileri ({len(oneriler)})", expanded=not ihlaller):
                    for item in oneriler:
                        onc = item.get("oncelik", "Orta")
                        color = _ONCELIK_COLOR.get(onc, "#888")
                        st.markdown(
                            f"<div style='background:#f8f9fb;border-left:4px solid {color};"
                            f"padding:10px 14px;border-radius:6px;margin-bottom:8px;'>"
                            f"<span style='font-size:0.78rem;background:{color};color:#fff;"
                            f"padding:1px 7px;border-radius:3px;'>{onc}</span><br>"
                            f"<b>Mevcut:</b> {html.escape(item.get('sorun',''))}<br>"
                            f"<b>Öneri:</b> {html.escape(item.get('oneri',''))}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

            # ── Olumlu yönler ────────────────────────────────────────────────
            olumlu = parsed.get("olumlu_yonler", []) if parsed else []
            if olumlu:
                with st.expander("✅ Uygun Bulunan Yönler", expanded=False):
                    for madde in olumlu:
                        st.markdown(f"- {madde}")

            # ── Ham rapor ────────────────────────────────────────────────────
            with st.expander("🔍 Tam Rapor (JSON)", expanded=False):
                if parsed:
                    st.json(parsed)
                else:
                    st.markdown(
                        f"<pre style='white-space:pre-wrap;word-wrap:break-word;"
                        f"background:#f6f8fa;padding:1rem;border-radius:0.5rem;"
                        f"font-size:0.85rem;'>{html.escape(report)}</pre>",
                        unsafe_allow_html=True,
                    )

            log_audit(
                username=st.session_state.get("username", "unknown"),
                agent="legal",
                model=selected_model,
                campaign_text=legal_campaign_text,
                score=score,
                result_summary=parsed.get("report", "") if parsed else report,
            )

        except Exception as e:
            st.error(f"Hata oluştu: {e}")
