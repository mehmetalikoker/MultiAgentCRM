# -*- coding: utf-8 -*-
import streamlit as st
from collections import Counter
from agents.audit_logger import load_audit_log

_AGENT_LABELS = {
    "compliance": "Metin Denetimi",
    "visual":     "Görsel Denetim",
    "legal":      "Hukuk & Strateji",
}


def get_agent_label(agent: str) -> str:
    return _AGENT_LABELS.get(agent, agent)


def compute_summary(logs: list) -> dict:
    total     = len(logs)
    safe      = sum(1 for e in logs if e.get("is_safe") is True)
    unsafe    = sum(1 for e in logs if e.get("is_safe") is False)
    safe_rate = round(safe / total * 100) if total else 0
    return {"total": total, "safe": safe, "unsafe": unsafe, "safe_rate": safe_rate}


def compute_agent_counts(logs: list) -> Counter:
    return Counter(e.get("agent", "—") for e in logs)


def compute_model_counts(logs: list) -> Counter:
    return Counter(e.get("model", "—") for e in logs)


def compute_user_stats(logs: list) -> dict:
    return {
        "total":  Counter(e.get("username") for e in logs),
        "safe":   Counter(e.get("username") for e in logs if e.get("is_safe") is True),
        "unsafe": Counter(e.get("username") for e in logs if e.get("is_safe") is False),
    }


def render():
    st.header("Denetim İstatistikleri")

    logs = load_audit_log()

    if not logs:
        st.info("Henüz denetim kaydı yok.")
        return

    summary = compute_summary(logs)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Denetim", summary["total"])
    c2.metric("Uygun",          summary["safe"])
    c3.metric("Uygunsuz",       summary["unsafe"])
    c4.metric("Uygunluk Oranı", f"%{summary['safe_rate']}")

    st.markdown("---")

    col_agent, col_model = st.columns(2)

    with col_agent:
        st.markdown("**Denetim Türü Dağılımı**")
        for agent, count in compute_agent_counts(logs).most_common():
            st.markdown(f"- {get_agent_label(agent)}: **{count}**")

    with col_model:
        st.markdown("**Model Kullanım Dağılımı**")
        for model, count in compute_model_counts(logs).most_common():
            st.markdown(f"- {model}: **{count}**")

    st.markdown("---")
    st.markdown("**Kullanıcı Bazında Aktivite**")

    user_stats  = compute_user_stats(logs)
    user_total  = user_stats["total"]
    user_safe   = user_stats["safe"]
    user_unsafe = user_stats["unsafe"]

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
