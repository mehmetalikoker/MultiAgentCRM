# -*- coding: utf-8 -*-
import json
import streamlit as st
from agents.audit_logger import log_audit


def render(selected_model: str, models: dict):
    st.header("Kampanya Metin Denetimi")
    st.markdown("Kampanya metninizi girin ve hangi kanalda yayınlanacağını seçin.")

    col1, col2 = st.columns([3, 1])

    with col1:
        campaign_text = st.text_area(
            "Kampanya Metni",
            placeholder="Kampanya metninizi buraya girin...",
            height=180,
        )

    with col2:
        channel = st.selectbox(
            "Kampanya Kanalı",
            options=[
                "SMS",
                "E-posta",
                "Mobil Inbound Kampanya",
                "Şube İçi Inbound Kampanya",
                "Push Bildirimi",
            ],
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

                    # Raporu JSON olarak parse et; suggestions varlığını kontrol et
                    parsed_report = None
                    try:
                        clean = report.strip()
                        if clean.startswith("```"):
                            parts = clean.split("```")
                            clean = parts[1].lstrip("json").strip() if len(parts) > 1 else clean
                        parsed_report = json.loads(clean)
                    except (json.JSONDecodeError, ValueError):
                        pass

                    suggestions = []
                    if parsed_report and isinstance(parsed_report.get("suggestions"), list):
                        suggestions = [s for s in parsed_report["suggestions"] if s]

                    st.markdown("---")
                    st.subheader("Denetim Sonucu")

                    if not is_safe:
                        st.error("❌ Kampanya metninde sorunlar tespit edildi.")
                    elif suggestions:
                        st.warning("⚠️ Kampanya metni düzenlenmesi gerekiyor.")
                    else:
                        st.success("✅ Kampanya metni uygun bulundu.")

                    st.markdown(f"**Kanal:** `{channel}` &nbsp;|&nbsp; **Model:** `{models[selected_model]}`")
                    st.markdown("**Detaylı Rapor:**")
                    if parsed_report:
                        st.json(parsed_report)
                    else:
                        st.markdown(
                            f"<pre style='white-space: pre-wrap; word-wrap: break-word; "
                            f"background:#f6f8fa; padding:1rem; border-radius:0.5rem; "
                            f"font-size:0.85rem; overflow-x:hidden;'>{report}</pre>",
                            unsafe_allow_html=True,
                        )

                    log_audit(
                        username=st.session_state.get("username", "unknown"),
                        agent="compliance",
                        model=selected_model,
                        campaign_text=campaign_text,
                        channel=channel,
                        is_safe=is_safe,
                        result_summary=parsed_report.get("report", "") if parsed_report else report[:500],
                    )

                except Exception as e:
                    st.error(f"Hata oluştu: {e}")
