# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from agents.audit_logger import load_audit_log

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


def render():
    st.header("Arama Geçmişi")

    entries = load_audit_log()

    if not entries:
        st.info("Henüz denetim kaydı yok.")
        return

    # ── Filtreler ─────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        agent_filter = st.selectbox(
            "Agent",
            options=["Tümü"] + list(_AGENT_LABELS.values()),
        )
    with col_f2:
        user_options = ["Tümü"] + sorted({e["username"] for e in entries})
        user_filter = st.selectbox("Kullanıcı", options=user_options)
    with col_f3:
        result_filter = st.selectbox(
            "Sonuç",
            options=["Tümü", "✅ Uygun", "❌ Sorunlu"],
        )

    # ── Filtre uygula ─────────────────────────────────────────────────────────
    filtered = entries
    if agent_filter != "Tümü":
        key = next((k for k, v in _AGENT_LABELS.items() if v == agent_filter), None)
        filtered = [e for e in filtered if e["agent"] == key]
    if user_filter != "Tümü":
        filtered = [e for e in filtered if e["username"] == user_filter]
    if result_filter == "✅ Uygun":
        filtered = [e for e in filtered if e.get("is_safe") is True]
    elif result_filter == "❌ Sorunlu":
        filtered = [e for e in filtered if e.get("is_safe") is False]

    st.caption(f"{len(filtered)} kayıt gösteriliyor (toplam {len(entries)})")
    st.markdown("---")

    if not filtered:
        st.warning("Seçili filtrelere uygun kayıt yok.")
        return

    # ── Tablo ─────────────────────────────────────────────────────────────────
    rows = []
    for e in filtered:
        is_safe = e.get("is_safe")
        score = e.get("score")

        sonuc = _RESULT_ICONS.get(is_safe, "—")
        if score is not None:
            sonuc = f"{score}/100"

        rows.append({
            "Tarih (UTC)":  e.get("timestamp", ""),
            "Kullanıcı":    e.get("username", ""),
            "Agent":        _AGENT_LABELS.get(e.get("agent", ""), e.get("agent", "")),
            "Kanal":        e.get("channel") or "—",
            "Model":        e.get("model", ""),
            "Sonuç":        sonuc,
            "Metin (önizleme)": e.get("campaign_text_preview", ""),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── CSV indir ─────────────────────────────────────────────────────────────
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="CSV İndir",
        data=csv,
        file_name="denetim_gecmisi.csv",
        mime="text/csv",
    )

    # ── Detay görünümü ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Kayıt Detayı")
    idx = st.selectbox(
        "Aşağıdan İncelenecek kaydı seçiniz",
        options=range(len(filtered)),
        format_func=lambda i: f"{filtered[i]['timestamp']}  |  {_AGENT_LABELS.get(filtered[i]['agent'], '')}  |  {filtered[i]['username']}",
    )
    entry = filtered[idx]
    st.markdown("---")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown(f"**Tarih:** {entry.get('timestamp')}")
        st.markdown(f"**Kullanıcı:** {entry.get('username')}")
        st.markdown(f"**Agent:** {_AGENT_LABELS.get(entry.get('agent', ''), '')}")
        st.markdown(f"**Model:** {entry.get('model')}")
        st.markdown(f"**Kanal:** {entry.get('channel') or '—'}")
    with col_d2:
        is_safe = entry.get("is_safe")
        score = entry.get("score")
        if score is not None:
            color = "green" if score >= 70 else "orange" if score >= 40 else "red"
            st.markdown(
                f"<h2 style='color:{color}'>{score}/100</h2>",
                unsafe_allow_html=True,
            )
        elif is_safe is True:
            st.success("✅ Uygun")
        elif is_safe is False:
            st.error("❌ Sorunlu")

    st.markdown("**Kampanya Metni (önizleme):**")
    st.code(entry.get("campaign_text_preview", ""), language=None)

    if entry.get("result_summary"):
        st.markdown("**Özet:**")
        st.markdown(entry["result_summary"])
