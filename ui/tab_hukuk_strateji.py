# -*- coding: utf-8 -*-
import os
import tempfile
import streamlit as st
from agents.audit_logger import log_audit


def render(selected_model: str):
    st.header("Hukuk & Strateji Denetimi")
    st.markdown("Hukuki belgeleri yükleyin, kampanya metni bu belgelere göre denetlenecektir.")

    uploaded_docs = st.file_uploader(
        "Hukuki Belgeler (PDF veya TXT — birden fazla dosya seçebilirsiniz)",
        type=["pdf", "txt"],
        accept_multiple_files=True,
    )

    if uploaded_docs:
        st.success(f"✅ {len(uploaded_docs)} belge yüklendi: {', '.join(f.name for f in uploaded_docs)}")

    st.markdown("")
    legal_campaign_text = st.text_area(
        "Kampanya Metni",
        placeholder="Hukuki açıdan denetlenecek kampanya metnini girin...",
        height=140,
    )

    if st.button("Hukuki Denetim Yap", type="primary"):
        if not legal_campaign_text.strip():
            st.warning("Lütfen kampanya metnini girin.")
        else:
            with st.spinner("Belgeler işleniyor ve hukuki denetim yapılıyor..."):
                try:
                    legal_chunks: list[str] = []

                    if uploaded_docs:
                        from langchain_community.document_loaders import PyPDFLoader, TextLoader
                        from langchain.text_splitter import RecursiveCharacterTextSplitter

                        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

                        for doc_file in uploaded_docs:
                            suffix = os.path.splitext(doc_file.name)[1].lower()
                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                                tmp.write(doc_file.read())
                                tmp_path = tmp.name

                            loader = PyPDFLoader(tmp_path) if suffix == ".pdf" else TextLoader(tmp_path, encoding="utf-8")
                            pages = loader.load()
                            chunks = splitter.split_documents(pages)
                            legal_chunks.extend([c.page_content for c in chunks])
                            os.unlink(tmp_path)

                    from agents.legalstrategyagent import app as legal_app

                    result = legal_app.invoke({
                        "campaign_text": legal_campaign_text,
                        "legal_documents": legal_chunks,
                        "selected_model": selected_model,
                    })

                    report = result.get("legal_audit_report", "")
                    score = result.get("final_score", 0)

                    st.markdown("---")
                    st.subheader("Hukuki Denetim Sonucu")

                    col_score, col_report = st.columns([1, 3])
                    with col_score:
                        color = "green" if score >= 70 else "orange" if score >= 40 else "red"
                        st.markdown(
                            f"<h1 style='color:{color}; text-align:center'>{score}/100</h1>"
                            f"<p style='text-align:center'>Uygunluk Puanı</p>",
                            unsafe_allow_html=True,
                        )
                    with col_report:
                        if uploaded_docs:
                            st.caption(f"Kaynak belgeler: {', '.join(f.name for f in uploaded_docs)}")
                        else:
                            st.caption("Belge yüklenmedi — varsayılan BDDK mevzuatı kullanıldı.")
                        st.markdown(report)

                    log_audit(
                        username=st.session_state.get("username", "unknown"),
                        agent="legal",
                        model=selected_model,
                        campaign_text=legal_campaign_text,
                        score=score,
                        result_summary=report,
                    )

                except Exception as e:
                    st.error(f"Hata oluştu: {e}")
