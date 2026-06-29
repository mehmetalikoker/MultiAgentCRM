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


def _render_audit_results(parsed: dict | None, is_safe: bool) -> None:
    if not parsed:
        return

    if parsed.get("ozet"):
        st.info(parsed["ozet"])

    ok_puan = parsed.get("okunabilirlik", {}).get("puan")
    if ok_puan is not None:
        color = "#2ecc71" if ok_puan >= 7 else "#e67e22" if ok_puan >= 4 else "#e74c3c"
        st.markdown(
            f"<div style='display:inline-block;background:#f0f2f6;"
            f"padding:8px 16px;border-radius:8px;margin-bottom:12px;'>"
            f"<span style='color:#666;font-size:0.82rem;'>Okunabilirlik</span> "
            f"<span style='font-size:1.3rem;font-weight:700;color:{color};'>"
            f"{ok_puan}/10</span></div>",
            unsafe_allow_html=True,
        )

    mtg = parsed.get("metin_gorsel_tutarliligi", {})
    farklilıklar = mtg.get("farkliliklar", [])
    with st.expander(
        f"🔤 Metin–Görsel Tutarlılık  {_bool_icon(mtg.get('tutarli'))}",
        expanded=bool(farklilıklar),
    ):
        if mtg.get("tutarli") is None:
            st.caption("Onaylanan metin girilmediği için karşılaştırma yapılmadı.")
        elif mtg.get("tutarli"):
            st.success("Görsel üzerindeki metinler kampanya içeriğiyle tutarlı.")
        if farklilıklar:
            _section_card(farklilıklar, "#e74c3c", "#fff5f5")
        if mtg.get("not"):
            st.caption(mtg["not"])

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

    ok_sorunlar = parsed.get("okunabilirlik", {}).get("sorunlar", [])
    if ok_sorunlar:
        with st.expander(f"👁️ Okunabilirlik Sorunları ({len(ok_sorunlar)})", expanded=False):
            _section_card(ok_sorunlar, "#2980b9", "#eaf4fb")

    yaniltici = parsed.get("yaniltici_unsurlar", [])
    if yaniltici:
        with st.expander(f"⚠️ Yanıltıcı / Etik Dışı Unsurlar ({len(yaniltici)})", expanded=True):
            _section_card(yaniltici, "#e74c3c", "#fff0f0")

    oneriler = parsed.get("genel_oneriler", [])
    if oneriler:
        with st.expander("💡 Genel Öneriler", expanded=False):
            for o in oneriler:
                st.markdown(f"- {o}")

    with st.expander("🔍 Tam Denetim Raporu (JSON)", expanded=False):
        st.json(parsed)


def render(selected_model: str, models: dict, non_vision_models: set):
    st.header("Kampanya Görseli Oluştur")
    st.markdown(
        "Kampanya bilgilerini girin; mevzuat kurallarına uygun bir kampanya görseli "
        "yapay zeka ile otomatik oluşturulacak ve ardından denetlenecektir."
    )

    with st.form("gorsel_olustur_form"):
        col_left, col_right = st.columns([1, 1])

        with col_left:
            example_image = st.file_uploader(
                "Örnek Görsel (İsteğe Bağlı)",
                type=["jpg", "jpeg", "png"],
                help="Stil ve düzen referansı olarak kullanılacak örnek bir görsel yükleyebilirsiniz.",
            )
            campaign_title = st.text_input(
                "Teklif Başlığı *",
                placeholder="Örn: Yaz Tatili Tüketici Kredisi",
                max_chars=120,
            )
            campaign_segment = st.text_input(
                "Teklif Segmenti *",
                placeholder="Örn: 25-45 yaş bireysel müşteriler",
            )
            campaign_date = st.date_input("Kampanya Bitiş Tarihi *")

        with col_right:
            campaign_content = st.text_area(
                "Teklif İçeriği *",
                placeholder="Örn: %1.49 aylık faiz oranıyla 12 ay vadeli tüketici kredisi. İlk 3 ay ödemesiz.",
                height=105,
            )
            visual_description = st.text_area(
                "Görsel İçeriği *",
                placeholder=(
                    "Görsel de ne görmek istediğinizi açıklayın.\n"
                    "Örn: Deniz kenarında mutlu bir aile, ING turuncu tonları, minimal modern tasarım."
                ),
                height=105,
            )
            campaign_criteria = st.text_area(
                "Teklif Kriteri (Zorunlu Koşullar) *",
                placeholder=(
                    "Teklifin geçerli olması için zorunlu koşulları girin.\n"
                    "Örn: YMO: %24.36 · Minimum gelir 5.000 TL · Aktif ING müşterisi · BDDK lisanslı"
                ),
                height=105,
            )

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        submit = st.form_submit_button(
            "Kampanya Görseli Oluştur",
            type="primary",
            use_container_width=True,
        )

    if not submit:
        return

    # ── Doğrulama ─────────────────────────────────────────────────────────────
    missing = []
    if not campaign_title.strip():
        missing.append("Teklif Başlığı")
    if not campaign_content.strip():
        missing.append("Teklif İçeriği")
    if not campaign_segment.strip():
        missing.append("Teklif Segmenti")
    if not visual_description.strip():
        missing.append("Görsel İçeriği")
    if not campaign_criteria.strip():
        missing.append("Teklif Kriteri")

    if missing:
        st.warning(f"Lütfen şu zorunlu alanları doldurun: {', '.join(missing)}")
        return

    # ── Örnek görsel hazırlığı ────────────────────────────────────────────────
    example_bytes = None
    example_mime = None
    if example_image is not None:
        ext = os.path.splitext(example_image.name)[1].lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
        example_mime = mime_map.get(ext, "image/jpeg")
        example_bytes = example_image.read()

    # ── Adım 1: Prompt oluştur ve görsel üret ────────────────────────────────
    progress = st.progress(0, text="DALL-E prompt oluşturuluyor...")
    try:
        from agents.campaignvisualcreatoragent import app as creator_app

        result = creator_app.invoke({
            "campaign_title": campaign_title.strip(),
            "campaign_content": campaign_content.strip(),
            "campaign_segment": campaign_segment.strip(),
            "campaign_date": str(campaign_date),
            "visual_description": visual_description.strip(),
            "campaign_criteria": campaign_criteria.strip(),
            "example_image_bytes": example_bytes,
            "example_image_mime": example_mime,
            "selected_model": selected_model,
        })
        progress.progress(60, text="Görsel üretiliyor...")
    except Exception as e:
        progress.empty()
        from ui.error_handler import handle_error
        handle_error(e, "kampanya_gorseli_olustur")
        return

    agent_error = result.get("error")
    image_bytes = result.get("generated_image_bytes")
    dalle_prompt = result.get("dalle_prompt", "")

    progress.empty()

    if agent_error or not image_bytes:
        msg = agent_error or "Görsel oluşturulamadı."
        if "api_key" in msg.lower() or "openai" in msg.lower() or "auth" in msg.lower():
            st.error(
                "OpenAI API anahtarı bulunamadı veya geçersiz. "
                "Görsel oluşturma özelliği için geçerli bir `OPENAI_API_KEY` tanımlanmalıdır."
            )
        else:
            st.error(f"Görsel oluşturma başarısız: {msg}")
        if dalle_prompt:
            with st.expander("Oluşturulan DALL-E Prompt (görsel üretilemedi)", expanded=False):
                st.text(dalle_prompt)
        return

    # ── Sonuç: Görsel ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Oluşturulan Kampanya Görseli")

    # Görseli ortalanmış, sabit maksimum genişlikte göster (kesilme olmaz)
    col_pad_l, col_center, col_pad_r = st.columns([1, 3, 1])
    with col_center:
        st.image(image_bytes, caption="Yapay Zeka Tarafından Oluşturulan Görsel", use_container_width=True)

    # Meta bilgi + indirme butonu — görsel altında
    col_meta, col_dl = st.columns([3, 1])
    with col_meta:
        st.markdown(
            f"<div style='background:#f8f9fb;border-radius:8px;padding:12px 16px;font-size:0.9rem;line-height:1.8;'>"
            f"<b>Başlık:</b> {html.escape(campaign_title)} &nbsp;|&nbsp; "
            f"<b>Segment:</b> {html.escape(campaign_segment)} &nbsp;|&nbsp; "
            f"<b>Bitiş:</b> {campaign_date} &nbsp;|&nbsp; "
            f"<b>Model:</b> {models.get(selected_model, selected_model)}"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_dl:
        filename = f"kampanya_{campaign_title[:30].strip().replace(' ', '_')}.png"
        st.download_button(
            "Görseli İndir (PNG)",
            data=image_bytes,
            file_name=filename,
            mime="image/png",
            use_container_width=True,
        )

    with st.expander("Kullanılan Görsel Prompt", expanded=False):
        st.text_area("", value=dalle_prompt, height=160, disabled=True, label_visibility="collapsed")

    # ── Adım 2: Görsel Denetim ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Otomatik Görsel Denetim")

    if selected_model in non_vision_models:
        st.warning(
            f"⚠️ **{models.get(selected_model, selected_model)}** görsel denetimi desteklemiyor. "
            "Sol menüden görsel destekli bir model seçerek denetim yapabilirsiniz."
        )
        return

    with st.spinner("Oluşturulan görsel mevzuat kurallarına göre denetleniyor..."):
        try:
            from agents.visualcontrolagent import app as visual_app

            audit_text = (
                f"Teklif Başlığı: {campaign_title}\n"
                f"Teklif İçeriği: {campaign_content}\n"
                f"Hedef Segment: {campaign_segment}\n"
                f"Kampanya Bitiş Tarihi: {campaign_date}\n"
                f"Zorunlu Koşullar / Kriterler: {campaign_criteria}"
            )

            audit_result = visual_app.invoke({
                "campaign_text": audit_text,
                "image_bytes": image_bytes,
                "image_mime": "image/png",
                "selected_model": selected_model,
            })

            is_safe = audit_result.get("is_visual_safe", False)
            parsed = audit_result.get("visual_parsed")

        except Exception as e:
            from ui.error_handler import handle_error
            handle_error(e, "kampanya_gorseli_denetim")
            return

    if is_safe:
        st.success("✅ Oluşturulan görsel mevzuat ve marka kurallarına uygundur.")
    else:
        st.error(
            "❌ Görselde uyum sorunları tespit edildi. "
            "Aşağıdaki bulgulara göre görseli güncelleyebilir veya yeniden oluşturabilirsiniz."
        )

    _render_audit_results(parsed, is_safe)

    log_audit(
        username=st.session_state.get("username", "unknown"),
        agent="visual_creator",
        model=selected_model,
        campaign_text=audit_text,
        is_safe=is_safe,
        result_summary=parsed.get("report", "") if parsed else "",
    )
