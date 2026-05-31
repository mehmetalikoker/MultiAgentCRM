# -*- coding: utf-8 -*-
import json
import html
import streamlit as st
from agents.audit_logger import log_audit


def _parse_report(raw: str) -> dict | None:
    clean = raw.strip()
    if clean.startswith("```"):
        parts = clean.split("```")
        clean = parts[1].lstrip("json").strip() if len(parts) > 1 else clean
    try:
        return json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        return None


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

    if not run_btn:
        return

    if not campaign_text.strip():
        st.warning("Lütfen kampanya metnini girin.")
        return

    with st.spinner("Metin denetleniyor..."):
        try:
            from agents.campaigntextagent import app
            result = app.invoke({
                "campaign_text": campaign_text,
                "channel": channel,
                "selected_model": selected_model,
            })

            is_safe = result.get("is_safe", False)
            report_raw = result.get("compliance_report", "")
            parsed = _parse_report(report_raw)

            st.markdown("---")
            st.subheader("Denetim Sonucu")

            if result.get("injection_detected"):
                st.warning(
                    "⚠️ **Güvenlik Uyarısı:** Girdide prompt injection girişimi tespit edildi. "
                    "Şüpheli içerik filtrelendi ve denetim temizlenmiş metin üzerinden yapıldı."
                )
            st.markdown(f"**Kanal:** `{channel}` &nbsp;|&nbsp; **Model:** `{models[selected_model]}`")

            # ── Durum banner ─────────────────────────────────────────────────
            kritik = parsed.get("kritik_hatalar", []) if parsed else []
            uyarilar = parsed.get("uyarilar", []) if parsed else []

            if not is_safe or kritik:
                st.error("❌ Kampanya metninde uyum sorunları tespit edildi.")
            elif uyarilar:
                st.warning("⚠️ Metin yayımlanabilir ancak dikkat edilmesi gereken hususlar var.")
            else:
                st.success("✅ Kampanya metni uygun bulundu.")

            # ── Özet ─────────────────────────────────────────────────────────
            if parsed and parsed.get("ozet"):
                st.info(parsed["ozet"])

            # ── Kanal uyumu ───────────────────────────────────────────────────
            if parsed and parsed.get("kanal_uyumu"):
                kanal_sorunlar = parsed["kanal_uyumu"].get("sorunlar", [])
                if kanal_sorunlar:
                    with st.expander(f"📡 Kanal Uyum Sorunları — {channel}", expanded=True):
                        for s in kanal_sorunlar:
                            st.markdown(f"- {s}")

            # ── Kritik hatalar ────────────────────────────────────────────────
            if kritik:
                with st.expander(f"🚨 Kritik Hatalar ({len(kritik)})", expanded=True):
                    for item in kritik:
                        st.markdown(
                            f"<div style='background:#fff0f0;border-left:4px solid #e74c3c;"
                            f"padding:10px 14px;border-radius:6px;margin-bottom:8px;'>"
                            f"<b>Hata:</b> {html.escape(item.get('hata',''))}<br>"
                            f"<b>İlgili madde:</b> <em>{html.escape(item.get('ilgili_madde',''))}</em><br>"
                            f"<b>Öneri:</b> {html.escape(item.get('onerim',''))}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

            # ── Uyarılar ──────────────────────────────────────────────────────
            if uyarilar:
                with st.expander(f"⚠️ Uyarılar ({len(uyarilar)})", expanded=not kritik):
                    for item in uyarilar:
                        st.markdown(
                            f"<div style='background:#fffbe6;border-left:4px solid #f39c12;"
                            f"padding:10px 14px;border-radius:6px;margin-bottom:8px;'>"
                            f"<b>Uyarı:</b> {html.escape(item.get('uyari',''))}<br>"
                            f"<b>Öneri:</b> {html.escape(item.get('onerim',''))}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

            # ── Öneriler ──────────────────────────────────────────────────────
            suggestions = parsed.get("suggestions", []) if parsed else []
            if suggestions:
                with st.expander("💡 Genel Öneriler", expanded=False):
                    for s in suggestions:
                        st.markdown(f"- {s}")

            # ── Ham JSON ──────────────────────────────────────────────────────
            with st.expander("🔍 Tam Rapor (JSON)", expanded=False):
                if parsed:
                    st.json(parsed)
                else:
                    st.markdown(
                        f"<pre style='white-space:pre-wrap;word-wrap:break-word;"
                        f"background:#f6f8fa;padding:1rem;border-radius:0.5rem;"
                        f"font-size:0.85rem;overflow-x:hidden;'>"
                        f"{html.escape(report_raw)}</pre>",
                        unsafe_allow_html=True,
                    )

            # ── Audit log ────────────────────────────────────────────────────
            log_audit(
                username=st.session_state.get("username", "unknown"),
                agent="compliance",
                model=selected_model,
                campaign_text=campaign_text,
                channel=channel,
                is_safe=is_safe,
                result_summary=parsed.get("report", "") if parsed else report_raw,
            )

        except Exception as e:
            st.error(f"Hata oluştu: {e}")
