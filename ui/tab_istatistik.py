# -*- coding: utf-8 -*-
import streamlit as st
from collections import Counter
from agents.audit_logger import load_audit_log

_AGENT_LABELS = {
    "compliance": "Metin Denetimi",
    "visual":     "Görsel Denetim",
    "legal":      "Hukuk & Strateji",
}


def render():
    st.header("Denetim İstatistikleri")

    logs = load_audit_log()

    if not logs:
        st.info("Henüz denetim kaydı yok.")
        return

    total     = len(logs)
    safe      = sum(1 for e in logs if e.get("is_safe") is True)
    unsafe    = sum(1 for e in logs if e.get("is_safe") is False)
    safe_rate = round(safe / total * 100) if total else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Denetim", total)
    c2.metric("Uygun", safe)
    c3.metric("Uygunsuz", unsafe)
    c4.metric("Uygunluk Oranı", f"%{safe_rate}")

    st.markdown("---")

    col_agent, col_model = st.columns(2)

    with col_agent:
        st.markdown("**Denetim Türü Dağılımı**")
        agent_counts = Counter(e.get("agent", "—") for e in logs)
        for agent, count in agent_counts.most_common():
            label = _AGENT_LABELS.get(agent, agent)
            st.markdown(f"- {label}: **{count}**")

    with col_model:
        st.markdown("**Model Kullanım Dağılımı**")
        model_counts = Counter(e.get("model", "—") for e in logs)
        for model, count in model_counts.most_common():
            st.markdown(f"- {model}: **{count}**")

    st.markdown("---")
    st.markdown("**Kullanıcı Bazında Aktivite**")

    user_total  = Counter(e.get("username") for e in logs)
    user_safe   = Counter(e.get("username") for e in logs if e.get("is_safe") is True)
    user_unsafe = Counter(e.get("username") for e in logs if e.get("is_safe") is False)

    header_cols = st.columns([2, 2, 2, 2])
    header_cols[0].markdown("**Kullanıcı**")
    header_cols[1].markdown("**Toplam**")
    header_cols[2].markdown("**Uygun**")
    header_cols[3].markdown("**Uygunsuz**")

    for username in sorted(user_total, key=lambda u: -user_total[u]):
        row = st.columns([2, 2, 2, 2])
        row[0].markdown(username)
        row[1].markdown(str(user_total[username]))
        row[2].markdown(str(user_safe.get(username, 0)))
        row[3].markdown(str(user_unsafe.get(username, 0)))
