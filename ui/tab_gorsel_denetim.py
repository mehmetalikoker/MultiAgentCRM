# -*- coding: utf-8 -*-
import os
import html
import streamlit as st
from agents.audit_logger import log_audit


def _bool_icon(val) -> str:
    if val is True:
        return "✅"
    if val is False:
        return "❌"
    return "—"


def _section_card(items: list, border: str = "#e74c3c", bg: str = "#fff5f5") -> None:
    for item in items:
        st.markdown(
            f"<div style='background:{bg};border-left:4px solid {border};"
            f"padding:9px 14px;border-radius:6px;margin-bottom:6px;font-size:0.9rem;'>"
            f"{html.escape(str(item))}</div>",
            unsafe_allow_html=True,
        )


def render(selected_model: str, models: dict, non_vision_models: set):
    st.header("Görsel Denetim")
    st.markdown("Kampanya görselini yükleyin; marka uyumu, yasal zorunluluklar ve tutarlılık denetlenecektir.")

    vision_names    = [name for key, name in models.items() if key not in non_vision_models]
    non_vision_names = [models[k] for k in non_vision_models if k in models]

    if selected_model in non_vision_models:
        st.error(
            f"**{models[selected_model]}** görüntü işlemeyi desteklemiyor. "
            f"Sol menüden görsel destekli bir model seçin."
        )
        st.info("**Görsel denetim destekleyen modeller:** " + " · ".join(vision_names))
        return

    st.info(
        f"**Aktif model:** {models[selected_model]} &nbsp;·&nbsp; Görsel denetim destekleniyor.  \n"
        f"Desteklenmeyen modeller: {', '.join(non_vision_names)}",
        icon="ℹ️",
    )

    uploaded_file = st.file_uploader("Kampanya Görseli", type=["jpg", "jpeg", "png"])
    approved_text = st.text_area(
        "Onaylanan Kampanya Metni (İsteğe Bağlı)",
        placeholder="Daha önce onaylanan kampanya metnini buraya girin; görsel ile karşılaştırılır...",
        height=110,
    )

    if not st.button("Görseli Denetle", type="primary"):
        return

    if not uploaded_file:
        st.warning("Lütfen bir görsel yükleyin.")
        return

    with st.spinner("Görsel analiz ediliyor..."):
        try:
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            mime_map = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png",  ".gif": "image/gif",
                ".webp": "image/webp",
            }
            mime_type = mime_map.get(ext, "image/jpeg")

            from agents.visualcontrolagent import app as visual_app
            result = visual_app.invoke({
                "campaign_text": approved_text,
                "image_bytes":   uploaded_file.read(),
                "image_mime":    mime_type,
                "selected_model": selected_model,
            })

            is_safe = result.get("is_visual_safe", False)
            report  = result.get("visual_report", "")
            parsed  = result.get("visual_parsed")

            st.markdown("---")
            st.subheader("Görsel Denetim Sonucu")

            # ── Görsel + durum ────────────────────────────────────────────────
            col_img, col_status = st.columns([1, 2])
            with col_img:
                uploaded_file.seek(0)
                st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)

            with col_status:
                if is_safe:
                    st.success("✅ Görsel uygun bulundu.")
                else:
                    st.error("❌ Görselde uyum sorunları tespit edildi.")

                if parsed and parsed.get("ozet"):
                    st.info(parsed["ozet"])

                # Okunabilirlik puanı
                if parsed:
                    ok_puan = parsed.get("okunabilirlik", {}).get("puan")
                    if ok_puan is not None:
                        color = "#2ecc71" if ok_puan >= 7 else "#e67e22" if ok_puan >= 4 else "#e74c3c"
                        st.markdown(
                            f"<div style='display:inline-block;background:#f0f2f6;"
                            f"padding:8px 16px;border-radius:8px;margin-top:6px;'>"
                            f"<span style='color:#666;font-size:0.82rem;'>Okunabilirlik</span> "
                            f"<span style='font-size:1.3rem;font-weight:700;color:{color};'>"
                            f"{ok_puan}/10</span></div>",
                            unsafe_allow_html=True,
                        )

            st.markdown("")

            # ── Detay kartları ────────────────────────────────────────────────
            if parsed:
                # 1. Metin-Görsel Tutarlılık
                mtg = parsed.get("metin_gorsel_tutarliligi", {})
                farklilıklar = mtg.get("farkliliklar", [])
                with st.expander(
                    f"🔤 Metin–Görsel Tutarlılık  {_bool_icon(mtg.get('tutarli'))}",
                    expanded=bool(farklilıklar),
                ):
                    if mtg.get("tutarli") is None:
                        st.caption("Onaylanan metin girilmediği için karşılaştırma yapılmadı.")
                    elif mtg.get("tutarli"):
                        st.success("Görsel üzerindeki metinler onaylanan metinle tutarlı.")
                    if farklilıklar:
                        _section_card(farklilıklar, "#e74c3c", "#fff5f5")
                    if mtg.get("not"):
                        st.caption(mtg["not"])

                # 2. Yasal Uyum
                yasal = parsed.get("yasal_uyum", {})
                yasal_sorunlar = yasal.get("sorunlar", [])
                with st.expander(
                    f"⚖️ Yasal Zorunlu Unsurlar  {'❌' if yasal_sorunlar else '✅'}",
                    expanded=bool(yasal_sorunlar),
                ):
                    col_y1, col_y2, col_y3 = st.columns(3)
                    col_y1.markdown(f"**YMO Mevcut:** {_bool_icon(yasal.get('ymo_mevcut'))}")
                    col_y2.markdown(f"**YMO Okunabilir:** {_bool_icon(yasal.get('ymo_okunabilir'))}")
                    col_y3.markdown(f"**Bitiş Tarihi:** {_bool_icon(yasal.get('bitis_tarihi_mevcut'))}")
                    if yasal_sorunlar:
                        st.markdown("")
                        _section_card(yasal_sorunlar, "#e67e22", "#fffbe6")

                # 3. Marka Uyumu
                marka = parsed.get("marka_uyumu", {})
                marka_sorunlar = marka.get("sorunlar", [])
                with st.expander(
                    f"🎨 Marka ve Tasarım Uyumu  {'❌' if marka_sorunlar else '✅'}",
                    expanded=bool(marka_sorunlar),
                ):
                    col_m1, col_m2 = st.columns(2)
                    col_m1.markdown(f"**Logo Mevcut:** {_bool_icon(marka.get('logo_mevcut'))}")
                    col_m2.markdown(f"**Logo Doğru:** {_bool_icon(marka.get('logo_dogru'))}")
                    if marka_sorunlar:
                        st.markdown("")
                        _section_card(marka_sorunlar, "#8e44ad", "#fdf5ff")

                # 4. Okunabilirlik
                ok_sorunlar = parsed.get("okunabilirlik", {}).get("sorunlar", [])
                if ok_sorunlar:
                    with st.expander(f"👁️ Okunabilirlik Sorunları ({len(ok_sorunlar)})", expanded=False):
                        _section_card(ok_sorunlar, "#2980b9", "#eaf4fb")

                # 5. Yanıltıcı Unsurlar
                yaniltici = parsed.get("yaniltici_unsurlar", [])
                if yaniltici:
                    with st.expander(f"⚠️ Yanıltıcı / Etik Dışı Unsurlar ({len(yaniltici)})", expanded=True):
                        _section_card(yaniltici, "#e74c3c", "#fff0f0")

                # 6. Genel Öneriler
                oneriler = parsed.get("genel_oneriler", [])
                if oneriler:
                    with st.expander("💡 Genel Öneriler", expanded=False):
                        for o in oneriler:
                            st.markdown(f"- {o}")

            # ── Ham rapor ────────────────────────────────────────────────────
            with st.expander("🔍 Tam Rapor (JSON)", expanded=False):
                if parsed:
                    st.json(parsed)
                else:
                    st.markdown(report)

            log_audit(
                username=st.session_state.get("username", "unknown"),
                agent="visual",
                model=selected_model,
                campaign_text=approved_text,
                is_safe=is_safe,
                result_summary=parsed.get("report", "") if parsed else report,
            )

        except Exception as e:
            from ui.error_handler import handle_error
            handle_error(e, "gorsel_denetim")
