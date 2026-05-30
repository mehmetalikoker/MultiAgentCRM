# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import altair as alt
from collections import Counter
from datetime import datetime, timezone, timedelta
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


def _trend_df(logs: list, days: int = 7) -> pd.DataFrame:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    date_counts: Counter = Counter()
    safe_counts: Counter = Counter()
    unsafe_counts: Counter = Counter()

    for e in logs:
        try:
            dt = datetime.strptime(e["timestamp"], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            continue
        if dt < cutoff:
            continue
        day = dt.strftime("%m/%d")
        date_counts[day] += 1
        if e.get("is_safe") is True:
            safe_counts[day] += 1
        elif e.get("is_safe") is False:
            unsafe_counts[day] += 1

    all_days = []
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%m/%d")
        all_days.append(d)

    rows = []
    for d in all_days:
        rows.append({"Tarih": d, "Tür": "Uygun",    "Adet": safe_counts.get(d, 0)})
        rows.append({"Tarih": d, "Tür": "Uygunsuz", "Adet": unsafe_counts.get(d, 0)})

    return pd.DataFrame(rows)


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


def _model_df(logs: list) -> pd.DataFrame:
    counts = Counter(e.get("model", "—") for e in logs)
    return pd.DataFrame(
        [{"Model": k, "Kullanım": v} for k, v in counts.most_common()],
    )


def _agent_df(logs: list) -> pd.DataFrame:
    counts = Counter(e.get("agent", "—") for e in logs)
    return pd.DataFrame(
        [{"Denetim Türü": get_agent_label(k), "Adet": v} for k, v in counts.most_common()],
    )


def render():
    st.header("Arama İstatistikleri")

    logs = load_audit_log()

    if not logs:
        st.info("Henüz denetim kaydı yok.")
        return

    # ── Özet metrikler ────────────────────────────────────────────────────────
    summary = compute_summary(logs)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Denetim", summary["total"])
    c2.metric("Uygun",          summary["safe"])
    c3.metric("Uygunsuz",       summary["unsafe"])
    c4.metric("Uygunluk Oranı", f"%{summary['safe_rate']}")

    st.markdown("---")

    # ── Son 7 gün trend ───────────────────────────────────────────────────────
    st.subheader("Son 7 Gün Denetim Trendi")

    trend = _trend_df(logs, days=7)
    if trend["Adet"].sum() == 0:
        st.info("Son 7 günde denetim kaydı yok.")
    else:
        chart = (
            alt.Chart(trend)
            .mark_bar()
            .encode(
                x=alt.X("Tarih:O", sort=None, title="Tarih"),
                y=alt.Y("Adet:Q", title="Denetim Sayısı"),
                color=alt.Color(
                    "Tür:N",
                    scale=alt.Scale(
                        domain=["Uygun", "Uygunsuz"],
                        range=["#2ecc71", "#e74c3c"],
                    ),
                    legend=alt.Legend(title="Sonuç"),
                ),
                tooltip=["Tarih", "Tür", "Adet"],
            )
            .properties(height=260)
        )
        st.altair_chart(chart, use_container_width=True)

    st.markdown("---")

    # ── Model ve Agent dağılımı ───────────────────────────────────────────────
    col_model, col_agent = st.columns(2)

    with col_model:
        st.subheader("Model Kullanımı")
        model_df = _model_df(logs)
        if not model_df.empty:
            chart = (
                alt.Chart(model_df)
                .mark_bar(color="#FF6200")
                .encode(
                    x=alt.X("Kullanım:Q", title="Kullanım Sayısı"),
                    y=alt.Y("Model:N", sort="-x", title=""),
                    tooltip=["Model", "Kullanım"],
                )
                .properties(height=200)
            )
            st.altair_chart(chart, use_container_width=True)

    with col_agent:
        st.subheader("Denetim Türü")
        agent_df = _agent_df(logs)
        if not agent_df.empty:
            chart = (
                alt.Chart(agent_df)
                .mark_bar(color="#3498db")
                .encode(
                    x=alt.X("Adet:Q", title="Denetim Sayısı"),
                    y=alt.Y("Denetim Türü:N", sort="-x", title=""),
                    tooltip=["Denetim Türü", "Adet"],
                )
                .properties(height=200)
            )
            st.altair_chart(chart, use_container_width=True)

    st.markdown("---")

    # ── Kullanıcı bazında aktivite ────────────────────────────────────────────
    st.subheader("Kullanıcı Bazında Aktivite")

    user_total  = Counter(e.get("username") for e in logs)
    user_safe   = Counter(e.get("username") for e in logs if e.get("is_safe") is True)
    user_unsafe = Counter(e.get("username") for e in logs if e.get("is_safe") is False)

    rows = []
    for username in sorted(user_total, key=lambda u: -user_total[u]):
        rows.append({
            "Kullanıcı":  username,
            "Toplam":     user_total[username],
            "Uygun":      user_safe.get(username, 0),
            "Uygunsuz":   user_unsafe.get(username, 0),
        })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
