# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import tempfile

st.set_page_config(
    page_title="Kampanya Denetim Sistemi",
    page_icon="🏦",
    layout="wide"
)

MODELS = {
    # OpenAI
    "gpt-4o":                    "GPT-4o",
    "gpt-4o-mini":               "GPT-4o Mini",
    "gpt-4-turbo":               "GPT-4 Turbo",
    "gpt-3.5-turbo":             "GPT-3.5 Turbo",
    # Anthropic
    "claude-opus-4-7":           "Claude Opus 4.7",
    "claude-sonnet-4-6":         "Claude Sonnet 4.6",
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    # Google Gemini
    # "gemini-2.0-flash":          "Gemini 2.0 Flash",
    # "gemini-1.5-pro":            "Gemini 1.5 Pro",
    # "gemini-1.5-flash":          "Gemini 1.5 Flash",
    
    # DeepSeek
    "deepseek-chat":             "DeepSeek Chat",
}

# Görsel denetimi desteklemeyen modeller
_NON_VISION_MODELS = {"gpt-3.5-turbo", "deepseek-chat"}

with st.sidebar:
    st.header("⚙️ Model Ayarları")
    selected_model = st.selectbox(
        "LLM Modeli",
        options=list(MODELS.keys()),
        format_func=lambda k: MODELS[k],
        index=0,
    )
    st.caption(f"Seçili model tüm denetim adımlarında kullanılır.")
    if selected_model in _NON_VISION_MODELS:
        st.warning("⚠️ Seçili model görsel denetimi desteklemiyor.")

st.title("🏦 Kampanya Denetim Sistemi")
st.markdown("---")

tab1, tab2, tab3 = st.tabs([
    "📝 Metin Denetimi",
    "🖼️ Görsel Denetim",
    "⚖️ Hukuk & Strateji Denetimi"
])

# ─── TAB 1: Kampanya Metin Denetimi ───────────────────────────────────────────
with tab1:
    st.header("Kampanya Metin Denetimi")
    st.markdown("Kampanya metninizi girin ve hangi kanalda yayınlanacağını seçin.")

    col1, col2 = st.columns([3, 1])

    with col1:
        campaign_text = st.text_area(
            "Kampanya Metni",
            placeholder="Kampanya metninizi buraya girin...",
            height=180
        )

    with col2:
        channel = st.selectbox(
            "Yayın Kanalı",
            options=[
                "SMS",
                "E-posta",
                "Mobil Inbound Kampanya",
                "Şube İçi Inbound Kampanya",
                "Push Bildirimi",
            ]
        )
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("Denetle", type="primary", use_container_width=True)

    if run_btn:
        if not campaign_text.strip():
            st.warning("Lütfen kampanya metnini girin.")
        else:
            with st.spinner("Metin denetleniyor..."):
                try:
                    from agents.campaigntextagent import app
                    result = app.invoke({
                        "campaign_text": campaign_text,
                        "channel": channel,
                        "selected_model": selected_model,
                    })

                    is_safe = result.get("is_safe", False)
                    report = result.get("compliance_report", "")

                    st.markdown("---")
                    st.subheader("Denetim Sonucu")

                    if is_safe:
                        st.success("✅ Kampanya metni uygun bulundu.")
                    else:
                        st.error("❌ Kampanya metninde sorunlar tespit edildi.")

                    st.markdown(f"**Kanal:** `{channel}` &nbsp;|&nbsp; **Model:** `{MODELS[selected_model]}`")
                    st.markdown("**Detaylı Rapor:**")
                    st.code(report, language="json")

                except Exception as e:
                    st.error(f"Hata oluştu: {e}")

# ─── TAB 2: Görsel Denetim ────────────────────────────────────────────────────
with tab2:
    st.header("Görsel Denetim")
    st.markdown("Denetlenecek kampanya görselini ve onaylanmış metni girin.")

    uploaded_file = st.file_uploader(
        "Kampanya Görseli", type=["jpg", "jpeg", "png"]
    )

    approved_text = st.text_area(
        "Onaylanmış Kampanya Metni",
        placeholder="Daha önce onaylanan kampanya metnini buraya girin...",
        height=120
    )

    if st.button("Görseli Denetle", type="primary"):
        if not uploaded_file:
            st.warning("Lütfen bir görsel yükleyin.")
        elif not approved_text.strip():
            st.warning("Lütfen onaylanmış kampanya metnini girin.")
        else:
            with st.spinner("Görsel denetleniyor..."):
                try:
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=os.path.splitext(uploaded_file.name)[1]
                    ) as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name

                    from agents.visualcontrolagent import app as visual_app
                    result = visual_app.invoke({
                        "campaign_text": approved_text,
                        "image_path": tmp_path,
                        "selected_model": selected_model,
                    })
                    os.unlink(tmp_path)

                    is_visual_safe = result.get("is_visual_safe", False)
                    report = result.get("visual_report", "")

                    st.markdown("---")
                    st.subheader("Görsel Denetim Sonucu")
                    col_img, col_report = st.columns([1, 2])
                    with col_img:
                        st.image(uploaded_file, caption="Yüklenen Görsel", use_container_width=True)
                    with col_report:
                        if is_visual_safe:
                            st.success("✅ Görsel uygun bulundu.")
                        else:
                            st.error("❌ Görselde sorunlar tespit edildi.")
                        st.markdown("**Detaylı Rapor:**")
                        st.markdown(report)

                except Exception as e:
                    st.error(f"Hata oluştu: {e}")

# ─── TAB 3: Hukuk & Strateji Denetimi ────────────────────────────────────────
with tab3:
    st.header("Hukuk & Strateji Denetimi")
    st.markdown("Hukuki belgeleri yükleyin, kampanya metni bu belgelere göre denetlenecektir.")

    # Dosya yükleme
    uploaded_docs = st.file_uploader(
        "Hukuki Belgeler (PDF veya TXT — birden fazla dosya seçebilirsiniz)",
        type=["pdf", "txt"],
        accept_multiple_files=True
    )

    if uploaded_docs:
        st.success(f"✅ {len(uploaded_docs)} belge yüklendi: {', '.join(f.name for f in uploaded_docs)}")

    st.markdown("")
    legal_campaign_text = st.text_area(
        "Kampanya Metni",
        placeholder="Hukuki açıdan denetlenecek kampanya metnini girin...",
        height=140
    )

    if st.button("Hukuki Denetim Yap", type="primary"):
        if not legal_campaign_text.strip():
            st.warning("Lütfen kampanya metnini girin.")
        else:
            with st.spinner("Belgeler işleniyor ve hukuki denetim yapılıyor..."):
                try:
                    # Yüklenen dosyalardan metin çıkar
                    legal_chunks: list[str] = []

                    if uploaded_docs:
                        from langchain_community.document_loaders import PyPDFLoader, TextLoader
                        from langchain.text_splitter import RecursiveCharacterTextSplitter

                        splitter = RecursiveCharacterTextSplitter(
                            chunk_size=800, chunk_overlap=100
                        )

                        for doc_file in uploaded_docs:
                            suffix = os.path.splitext(doc_file.name)[1].lower()
                            with tempfile.NamedTemporaryFile(
                                delete=False, suffix=suffix
                            ) as tmp:
                                tmp.write(doc_file.read())
                                tmp_path = tmp.name

                            if suffix == ".pdf":
                                loader = PyPDFLoader(tmp_path)
                            else:
                                loader = TextLoader(tmp_path, encoding="utf-8")

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
                            unsafe_allow_html=True
                        )
                    with col_report:
                        if uploaded_docs:
                            st.caption(f"Kaynak belgeler: {', '.join(f.name for f in uploaded_docs)}")
                        else:
                            st.caption("Belge yüklenmedi — varsayılan BDDK mevzuatı kullanıldı.")
                        st.markdown(report)

                except Exception as e:
                    st.error(f"Hata oluştu: {e}")
