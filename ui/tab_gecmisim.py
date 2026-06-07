# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from agents.audit_logger import load_user_audit_log

_AGENT_LABELS = {
    "compliance": "Metin Denetimi",
    "visual":     "Görsel Denetim",
    "legal":      "Hukuk & Strateji",
}

_RESULT_ICONS = {
    True:  "✅ Uygun",
    False: "❌ Sorunlu",
    None:  "—",
}


def _summary_cards(entries: list):
    total  = len(entries)
    safe   = sum(1 for e in entries if e.get("is_safe") is True)
    unsafe = sum(1 for e in entries if e.get("is_safe") is False)
    rate   = round(safe / total * 100) if total else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Denetim", total)
    c2.metric("✅ Uygun",        safe)
    c3.metric("❌ Sorunlu",      unsafe)
    c4.metric("Uygunluk Oranı",  f"%{rate}")


def render():
    st.header("Denetim Geçmişim")

    username = st.session_state.get("username", "")
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%d.%m.%Y")
    today_str   = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    st.caption(f"Son 7 gün — {cutoff_date} ile {today_str} arası denetimleriniz")

    entries = load_user_audit_log(username, days=7)

    if not entries:
        st.info("Son 7 günde hiç denetim kaydınız yok.")
        return

    # ── Özet kartlar ──────────────────────────────────────────────────────────
    _summary_cards(entries)
    st.markdown("---")

    # ── Filtreler ─────────────────────────────────────────────────────────────
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        agent_filter = st.selectbox(
            "Denetim Türü",
            options=["Tümü"] + list(_AGENT_LABELS.values()),
            key="gim_agent",
        )
    with col_f2:
        result_filter = st.selectbox(
            "Sonuç",
            options=["Tümü", "✅ Uygun", "❌ Sorunlu"],
            key="gim_result",
        )

    # ── Arama ─────────────────────────────────────────────────────────────────
    search = st.text_input("Metin önizlemesinde ara...", placeholder="Anahtar kelime...", key="gim_search")

    # ── Filtre uygula ─────────────────────────────────────────────────────────
    filtered = entries
    if agent_filter != "Tümü":
        key = next((k for k, v in _AGENT_LABELS.items() if v == agent_filter), None)
        filtered = [e for e in filtered if e.get("agent") == key]
    if result_filter == "✅ Uygun":
        filtered = [e for e in filtered if e.get("is_safe") is True]
    elif result_filter == "❌ Sorunlu":
        filtered = [e for e in filtered if e.get("is_safe") is False]
    if search.strip():
        filtered = [e for e in filtered if search.lower() in (e.get("campaign_text_preview") or "").lower()]

    st.caption(f"{len(filtered)} kayıt gösteriliyor (toplam {len(entries)})")

    if not filtered:
        st.warning("Seçili filtrelere uygun kayıt yok.")
        return

    # ── Tablo ─────────────────────────────────────────────────────────────────
    rows = []
    for e in filtered:
        is_safe = e.get("is_safe")
        score   = e.get("score")
        sonuc   = f"{score}/100" if score is not None else _RESULT_ICONS.get(is_safe, "—")
        rows.append({
            "Tarih":            e.get("timestamp", ""),
            "Denetim Türü":     _AGENT_LABELS.get(e.get("agent", ""), e.get("agent", "")),
            "Kanal":            e.get("channel") or "—",
            "Model":            e.get("model", ""),
            "Sonuç":            sonuc,
            "Metin Önizleme":   e.get("campaign_text_preview", ""),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── CSV indir ─────────────────────────────────────────────────────────────
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="CSV İndir",
        data=csv,
        file_name=f"denetimlerim_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

    # ── Kayıt detayı ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Kayıt Detayı")

    idx = st.selectbox(
        "İncelenecek kaydı seçin",
        options=range(len(filtered)),
        format_func=lambda i: (
            f"{filtered[i]['timestamp']}  |  "
            f"{_AGENT_LABELS.get(filtered[i].get('agent',''), '')}  |  "
            f"{'✅' if filtered[i].get('is_safe') else '❌'}"
        ),
        key="gim_idx",
    )

    e = filtered[idx]
    is_safe = e.get("is_safe")
    score   = e.get("score")

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown(f"**Tarih:** {e.get('timestamp')}")
        st.markdown(f"**Denetim Türü:** {_AGENT_LABELS.get(e.get('agent',''), '')}")
        st.markdown(f"**Model:** {e.get('model')}")
        st.markdown(f"**Kanal:** {e.get('channel') or '—'}")
    with col_d2:
        if score is not None:
            color = "green" if score >= 70 else "orange" if score >= 40 else "red"
            st.markdown(f"<h2 style='color:{color}'>{score}/100</h2>", unsafe_allow_html=True)
        elif is_safe is True:
            st.success("✅ Uygun")
        elif is_safe is False:
            st.error("❌ Sorunlu")

    st.markdown("**Metin Önizleme:**")
    st.code(e.get("campaign_text_preview", ""), language=None)

    if e.get("result_summary"):
        st.markdown("**Denetim Özeti:**")
        st.text_area(
            label="ozet",
            value=e["result_summary"],
            height=260,
            disabled=True,
            label_visibility="collapsed",
        )
