# -*- coding: utf-8 -*-
import html
import streamlit as st
from agents.audit_logger import log_audit


def _parse_report(raw: str) -> dict | None:
    import json
    clean = raw.strip()
    if clean.startswith("```"):
        parts = clean.split("```")
        clean = parts[1].lstrip("json").strip() if len(parts) > 1 else clean
    try:
        return json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        return None


def _run_agent(text: str, channel: str, model: str) -> dict:
    from agents.campaigntextagent import app
    return app.invoke({
        "campaign_text": text,
        "channel": channel,
        "selected_model": model,
    })


def _status_badge(is_safe: bool, kritik: list, uyarilar: list) -> str:
    if not is_safe or kritik:
        return "❌ Uygunsuz"
    if uyarilar:
        return "⚠️ Uyarı Var"
    return "✅ Uygun"


def _render_result(label: str, result: dict, parsed: dict | None, report_raw: str):
    is_safe   = result.get("is_safe", False)
    kritik    = parsed.get("kritik_hatalar", []) if parsed else []
    uyarilar  = parsed.get("uyarilar", []) if parsed else []

    badge = _status_badge(is_safe, kritik, uyarilar)
    bg    = "#f0faf0" if is_safe and not kritik else "#fff8e1" if uyarilar and not kritik else "#fff0f0"
    border = "#2ecc71" if is_safe and not kritik else "#f39c12" if uyarilar and not kritik else "#e74c3c"

    st.markdown(
        f"<div style='background:{bg};border-left:5px solid {border};"
        f"padding:12px 16px;border-radius:8px;margin-bottom:12px;'>"
        f"<div style='font-size:1.05rem;font-weight:700;'>{label} &nbsp;—&nbsp; {badge}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if result.get("injection_detected"):
        st.warning("⚠️ Prompt injection girişimi tespit edildi, içerik filtrelendi.")

    if parsed and parsed.get("ozet"):
        st.info(parsed["ozet"])

    if kritik:
        with st.expander(f"🚨 Kritik Hatalar ({len(kritik)})", expanded=True):
            for item in kritik:
                st.markdown(
                    f"<div style='background:#fff0f0;border-left:4px solid #e74c3c;"
                    f"padding:10px 14px;border-radius:6px;margin-bottom:8px;'>"
                    f"<b>Hata:</b> {html.escape(item.get('hata', ''))}<br>"
                    f"<b>Madde:</b> <em>{html.escape(item.get('ilgili_madde', ''))}</em><br>"
                    f"<b>Öneri:</b> {html.escape(item.get('onerim', ''))}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    if uyarilar:
        with st.expander(f"⚠️ Uyarılar ({len(uyarilar)})", expanded=not kritik):
            for item in uyarilar:
                st.markdown(
                    f"<div style='background:#fffbe6;border-left:4px solid #f39c12;"
                    f"padding:10px 14px;border-radius:6px;margin-bottom:8px;'>"
                    f"<b>Uyarı:</b> {html.escape(item.get('uyari', ''))}<br>"
                    f"<b>Öneri:</b> {html.escape(item.get('onerim', ''))}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    with st.expander("🔍 Tam Rapor (JSON)", expanded=False):
        if parsed:
            st.json(parsed)
        else:
            st.markdown(
                f"<pre style='white-space:pre-wrap;word-wrap:break-word;"
                f"background:#f6f8fa;padding:1rem;border-radius:0.5rem;"
                f"font-size:0.85rem;'>{html.escape(report_raw)}</pre>",
                unsafe_allow_html=True,
            )

    return {"kritik": len(kritik), "uyari": len(uyarilar), "is_safe": is_safe and not kritik}


def _render_comparison_summary(a: dict, b: dict):
    st.markdown("---")
    st.subheader("📊 Karşılaştırma Özeti")

    col_a, col_mid, col_b = st.columns([2, 1, 2])

    with col_a:
        st.markdown("**Metin A**")
        st.metric("Kritik Hata", a["kritik"])
        st.metric("Uyarı",       a["uyari"])

    with col_mid:
        st.markdown("<div style='text-align:center;font-size:2rem;padding-top:28px;'>vs</div>",
                    unsafe_allow_html=True)

    with col_b:
        st.markdown("**Metin B**")
        st.metric("Kritik Hata", b["kritik"], delta=b["kritik"] - a["kritik"],
                  delta_color="inverse")
        st.metric("Uyarı",       b["uyari"],  delta=b["uyari"] - a["uyari"],
                  delta_color="inverse")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if a["is_safe"] and not b["is_safe"]:
        st.success("✅ **Metin A** uyum açısından daha güvenli.")
    elif b["is_safe"] and not a["is_safe"]:
        st.success("✅ **Metin B** uyum açısından daha güvenli.")
    elif a["is_safe"] and b["is_safe"]:
        if a["uyari"] <= b["uyari"]:
            st.success("✅ Her iki metin de uygun. **Metin A** daha az uyarı içeriyor.")
        else:
            st.success("✅ Her iki metin de uygun. **Metin B** daha az uyarı içeriyor.")
    else:
        if a["kritik"] < b["kritik"]:
            st.warning("⚠️ Her iki metin de sorunlu. **Metin A** daha az kritik hata içeriyor.")
        elif b["kritik"] < a["kritik"]:
            st.warning("⚠️ Her iki metin de sorunlu. **Metin B** daha az kritik hata içeriyor.")
        else:
            st.warning("⚠️ Her iki metin de benzer düzeyde sorun içeriyor.")


def render(selected_model: str, models: dict):
    st.header("Karşılaştırmalı Kampanya Analizi")
    st.markdown("İki farklı kampanya metnini yan yana denetleyip sonuçları karşılaştırın.")

    # ── Giriş alanları ────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        text_a = st.text_area("Metin A", placeholder="Birinci kampanya metni...", height=180, key="kars_a")
    with col_b:
        text_b = st.text_area("Metin B", placeholder="İkinci kampanya metni...", height=180, key="kars_b")

    col_ch, col_btn = st.columns([3, 1])
    with col_ch:
        channel = st.selectbox(
            "Kampanya Kanalı",
            options=["SMS", "E-posta", "Mobil Inbound Kampanya",
                     "Şube İçi Inbound Kampanya", "Push Bildirimi"],
            key="kars_channel",
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("Karşılaştır", type="primary", use_container_width=True)

    if not run_btn:
        return

    if not text_a.strip() or not text_b.strip():
        st.warning("Lütfen her iki metin alanını da doldurun.")
        return

    # ── Denetim ───────────────────────────────────────────────────────────────
    with st.spinner("Her iki metin denetleniyor..."):
        try:
            result_a = _run_agent(text_a, channel, selected_model)
            result_b = _run_agent(text_b, channel, selected_model)
        except Exception as e:
            from ui.error_handler import handle_error
            handle_error(e, "karsilastirma")
            return

    parsed_a = _parse_report(result_a.get("compliance_report", ""))
    parsed_b = _parse_report(result_b.get("compliance_report", ""))

    st.markdown("---")
    st.markdown(f"**Kanal:** `{channel}` &nbsp;|&nbsp; **Model:** `{models[selected_model]}`")
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Sonuçlar yan yana ─────────────────────────────────────────────────────
    col_ra, col_rb = st.columns(2)
    with col_ra:
        summary_a = _render_result("Metin A", result_a, parsed_a,
                                   result_a.get("compliance_report", ""))
    with col_rb:
        summary_b = _render_result("Metin B", result_b, parsed_b,
                                   result_b.get("compliance_report", ""))

    # ── Karşılaştırma özeti ───────────────────────────────────────────────────
    _render_comparison_summary(summary_a, summary_b)

    # ── Audit log ─────────────────────────────────────────────────────────────
    username = st.session_state.get("username", "unknown")
    for text, result, parsed, label in [
        (text_a, result_a, parsed_a, "A"),
        (text_b, result_b, parsed_b, "B"),
    ]:
        log_audit(
            username=username,
            agent="compliance",
            model=selected_model,
            campaign_text=f"[Karşılaştırma-{label}] {text}",
            channel=channel,
            is_safe=result.get("is_safe", False),
            result_summary=parsed.get("report", "") if parsed else result.get("compliance_report", ""),
        )
