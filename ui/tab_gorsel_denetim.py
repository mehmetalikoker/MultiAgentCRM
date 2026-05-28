# -*- coding: utf-8 -*-
import os
import streamlit as st
from agents.audit_logger import log_audit


def render(selected_model: str, models: dict, non_vision_models: set):
    st.header("Görsel Denetim")
    st.markdown("Denetlenecek kampanya görselini ve onaylanmış metni girin.")

    vision_model_names = [name for key, name in models.items() if key not in non_vision_models]
    non_vision_names = [models[k] for k in non_vision_models if k in models]

    if selected_model in non_vision_models:
        st.error(
            f"**{models[selected_model]}** görüntü işlemeyi desteklemiyor. "
            f"Sol menüden görsel destekli bir model seçin."
        )
        st.info("**Görsel denetim destekleyen modeller:** " + " · ".join(vision_model_names))
    else:
        st.info(
            f"**Aktif model:** {models[selected_model]} &nbsp;·&nbsp; Görsel denetim destekleniyor.  \n"
            f"Desteklenmeyen modeller: {', '.join(non_vision_names)}",
            icon="ℹ️",
        )

    uploaded_file = st.file_uploader("Kampanya Görseli", type=["jpg", "jpeg", "png"])

    approved_text = st.text_area(
        "Kampanya Metni (İsteğe Bağlı)",
        placeholder="Daha önce onaylanan kampanya metnini buraya girin...",
        height=120,
    )

    if st.button("Görseli Denetle", type="primary"):
        if not uploaded_file:
            st.warning("Lütfen bir görsel yükleyin.")
        else:
            with st.spinner("Görsel denetleniyor..."):
                try:
                    ext = os.path.splitext(uploaded_file.name)[1].lower()
                    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
                    mime_type = mime_map.get(ext, "image/jpeg")

                    from agents.visualcontrolagent import app as visual_app

                    result = visual_app.invoke({
                        "campaign_text": approved_text,
                        "image_bytes": uploaded_file.read(),
                        "image_mime": mime_type,
                        "selected_model": selected_model,
                    })

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

                    log_audit(
                        username=st.session_state.get("username", "unknown"),
                        agent="visual",
                        model=selected_model,
                        campaign_text=approved_text,
                        is_safe=is_visual_safe,
                        result_summary=report,
                    )

                except Exception as e:
                    st.error(f"Hata oluştu: {e}")
