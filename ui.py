# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="Kampanya Denetim Sistemi",
    page_icon="🏦",
    layout="wide"
)

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
                "Sosyal Medya",
                "Push Bildirimi",
                "Web Banner",
                "Basılı Materyal",
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
                    from agent.campaigntextagent import app
                    result = app.invoke({
                        "campaign_text": campaign_text,
                        "channel": channel
                    })

                    is_safe = result.get("is_safe", False)
                    report = result.get("compliance_report", "")

                    st.markdown("---")
                    st.subheader("Denetim Sonucu")

                    if is_safe:
                        st.success("✅ Kampanya metni uygun bulundu.")
                    else:
                        st.error("❌ Kampanya metninde sorunlar tespit edildi.")

                    st.markdown(f"**Kanal:** `{channel}`")
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
                    import tempfile
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=os.path.splitext(uploaded_file.name)[1]
                    ) as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name

                    from agent.visualcontrolagent import app as visual_app
                    result = visual_app.invoke({
                        "campaign_text": approved_text,
                        "image_path": tmp_path
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
    st.markdown("Metin ve görsel denetim raporlarını girerek BDDK mevzuat kontrolünü başlatın.")

    col_a, col_b = st.columns(2)
    with col_a:
        legal_campaign_text = st.text_area(
            "Kampanya Metni",
            placeholder="Kampanya metninizi girin...",
            height=120
        )
        compliance_report_input = st.text_area(
            "Metin Denetim Raporu",
            placeholder="Metin denetiminden gelen raporu yapıştırın...",
            height=120
        )
    with col_b:
        visual_report_input = st.text_area(
            "Görsel Denetim Raporu",
            placeholder="Görsel denetiminden gelen raporu yapıştırın...",
            height=120
        )

    if st.button("Hukuki Denetim Yap", type="primary"):
        if not legal_campaign_text.strip():
            st.warning("Lütfen kampanya metnini girin.")
        else:
            with st.spinner("Hukuki denetim yapılıyor..."):
                try:
                    from agent.legalstrategyagent import app as legal_app
                    result = legal_app.invoke({
                        "campaign_text": legal_campaign_text,
                        "compliance_report": compliance_report_input or "Metin raporu girilmedi.",
                        "visual_report": visual_report_input or "Görsel raporu girilmedi."
                    })

                    report = result.get("legal_audit_report", "")
                    score = result.get("final_score", 0)

                    st.markdown("---")
                    st.subheader("Hukuki Denetim Sonucu")

                    col_score, col_empty = st.columns([1, 3])
                    with col_score:
                        color = "green" if score >= 70 else "orange" if score >= 40 else "red"
                        st.markdown(
                            f"<h1 style='color:{color}; text-align:center'>{score}/100</h1>"
                            f"<p style='text-align:center'>Uygunluk Puanı</p>",
                            unsafe_allow_html=True
                        )

                    st.markdown("**Detaylı Rapor:**")
                    st.markdown(report)

                except Exception as e:
                    st.error(f"Hata oluştu: {e}")
