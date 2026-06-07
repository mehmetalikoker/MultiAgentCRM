# -*- coding: utf-8 -*-
import os
import time
from collections import Counter
from datetime import datetime, timezone, timedelta

import pandas as pd
import altair as alt
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

_API_KEYS = {
    "ANTHROPIC_API_KEY": "Anthropic (Claude)",
    "OPENAI_API_KEY":    "OpenAI",
    "GEMINI_API_KEY":    "Google Gemini",
    "DEEPSEEK_API_KEY":  "DeepSeek",
    "LANGCHAIN_API_KEY": "LangSmith",
    "MONGODB_URI":       "MongoDB URI",
    "JWT_SECRET":        "JWT Secret",
    "SMTP_HOST":         "SMTP Sunucu",
}


# ── Yardımcı sorgular ─────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def _check_mongo() -> tuple[bool, float, str]:
    try:
        from user.mongo import get_db
        t0 = time.perf_counter()
        get_db().command("ping")
        return True, round((time.perf_counter() - t0) * 1000, 1), ""
    except Exception as e:
        return False, 0.0, str(e)


@st.cache_data(ttl=60)
def _collection_counts() -> dict:
    try:
        from user.mongo import get_db
        db = get_db()
        return {
            "Kullanıcılar":     db["users"].count_documents({}),
            "Denetim Logları":  db["audit_logs"].count_documents({}),
            "Promptlar (DB)":   db["prompts"].count_documents({}),
            "Login Denemeleri": db["login_attempts"].count_documents({}),
            "Reset Tokenları":  db["reset_tokens"].count_documents({}),
        }
    except Exception:
        return {}


@st.cache_data(ttl=60)
def _audit_stats_24h() -> dict:
    try:
        from user.mongo import get_db
        db = get_db()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": None,
                "total":  {"$sum": 1},
                "safe":   {"$sum": {"$cond": [{"$eq": ["$is_safe", True]},  1, 0]}},
                "unsafe": {"$sum": {"$cond": [{"$eq": ["$is_safe", False]}, 1, 0]}},
            }},
        ]
        result = list(db["audit_logs"].aggregate(pipeline))
        if result:
            r = result[0]
            return {"total": r["total"], "safe": r["safe"], "unsafe": r["unsafe"]}
        return {"total": 0, "safe": 0, "unsafe": 0}
    except Exception:
        return {"total": 0, "safe": 0, "unsafe": 0}


@st.cache_data(ttl=30)
def _locked_users() -> list[dict]:
    try:
        from user.db import load_users_list
        return [u for u in load_users_list() if u.get("locked")]
    except Exception:
        return []


@st.cache_data(ttl=30)
def _pending_attempts() -> Counter:
    try:
        from user.mongo import get_db
        docs = get_db()["login_attempts"].find({}, {"_id": 0, "username": 1})
        return Counter(d["username"] for d in docs)
    except Exception:
        return Counter()


@st.cache_data(ttl=30)
def _active_sessions() -> int:
    try:
        from user.mongo import get_db
        return get_db()["users"].count_documents({"active_token_id": {"$exists": True}})
    except Exception:
        return 0


_ATLAS_FREE_LIMIT_MB = 512

@st.cache_data(ttl=300)
def _storage_stats() -> dict:
    try:
        from user.mongo import get_db
        db = get_db()
        rows = []
        total_mb = 0.0
        for name in db.list_collection_names():
            s = db.command("collStats", name, scale=1024)
            size_mb = s["storageSize"] / 1024
            total_mb += size_mb
            rows.append({"Koleksiyon": name, "Boyut (MB)": round(size_mb, 4)})
        pct = round(total_mb / _ATLAS_FREE_LIMIT_MB * 100, 3)
        return {"rows": rows, "total_mb": round(total_mb, 4), "pct": pct}
    except Exception:
        return {"rows": [], "total_mb": 0.0, "pct": 0.0}


# ── Bileşen yardımcıları ──────────────────────────────────────────────────────

def _key_card(label: str, env_key: str) -> None:
    raw = os.getenv(env_key, "").strip()
    ok  = bool(raw)
    bg, border = ("#f0faf0", "#2ecc71") if ok else ("#fff0f0", "#e74c3c")
    icon    = "✅" if ok else "❌"
    preview = f"`{raw[:4]}···`" if ok else "—"
    st.markdown(
        f"<div style='background:{bg};border-left:4px solid {border};"
        f"padding:10px 14px;border-radius:6px;margin-bottom:8px;'>"
        f"<div style='font-size:0.78rem;color:#555;margin-bottom:2px;'>{label}</div>"
        f"<div style='font-size:0.95rem;font-weight:600;'>{icon} {preview}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _metric_card(label: str, value: str, color: str = "#333") -> None:
    st.markdown(
        f"<div style='background:#f8f9fb;padding:14px 16px;border-radius:8px;text-align:center;'>"
        f"<div style='font-size:0.78rem;color:#666;'>{label}</div>"
        f"<div style='font-size:1.5rem;font-weight:700;color:{color};'>{value}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Ana render ────────────────────────────────────────────────────────────────

def render():
    col_title, col_btn = st.columns([5, 1])
    with col_title:
        st.header("Sistem Durumu")
    with col_btn:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Yenile", use_container_width=True):
            _check_mongo.clear()
            _collection_counts.clear()
            _audit_stats_24h.clear()
            _locked_users.clear()
            _pending_attempts.clear()
            _active_sessions.clear()
            _storage_stats.clear()
            st.rerun()

    # ── 1. MongoDB ────────────────────────────────────────────────────────────
    st.subheader("🗄️ Veritabanı")

    mongo_ok, latency, mongo_err = _check_mongo()

    if not mongo_ok:
        st.error(f"❌ MongoDB bağlantısı başarısız: `{mongo_err}`")
    else:
        lat_color = "green" if latency < 50 else "orange" if latency < 200 else "red"
        counts = _collection_counts()

        c_status, c_latency, c_sessions, *c_cols = st.columns([1.2, 1, 1] + [1] * len(counts))

        with c_status:
            _metric_card("Durum", "● Bağlı", "#2ecc71")
        with c_latency:
            _metric_card("Gecikme", f"{latency} ms", lat_color)
        with c_sessions:
            _metric_card("Aktif Oturum", str(_active_sessions()), "#3498db")
        for col, (name, cnt) in zip(c_cols, counts.items()):
            with col:
                _metric_card(name, str(cnt))

        # ── Depolama Alanı ────────────────────────────────────────────────────
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        storage = _storage_stats()
        pct      = storage["pct"]
        total_mb = storage["total_mb"]
        bar_color = "#2ecc71" if pct < 50 else "#e67e22" if pct < 80 else "#e74c3c"
        txt_color = "#2ecc71" if pct < 50 else "#e67e22" if pct < 80 else "#e74c3c"

        col_prog, col_detail = st.columns([3, 1])
        with col_prog:
            st.markdown("**Depolama Alanı (Atlas Free Tier — 512 MB)**")
            st.progress(min(pct / 100, 1.0))
        with col_detail:
            st.markdown(
                f"<div style='padding-top:28px;font-size:1.05rem;font-weight:700;color:{txt_color};'>"
                f"{total_mb:.3f} MB / 512 MB &nbsp;(%{pct:.2f})"
                f"</div>",
                unsafe_allow_html=True,
            )

        if storage["rows"]:
            df = pd.DataFrame(storage["rows"]).sort_values("Boyut (MB)", ascending=False)
            chart = (
                alt.Chart(df)
                .mark_bar(color=bar_color)
                .encode(
                    x=alt.X("Boyut (MB):Q", title="MB"),
                    y=alt.Y("Koleksiyon:N", sort="-x", title=""),
                    tooltip=["Koleksiyon", "Boyut (MB)"],
                )
                .properties(height=40 + len(storage["rows"]) * 32)
            )
            st.altair_chart(chart, use_container_width=True)

    st.markdown("---")

    # ── 2. API Anahtarları ────────────────────────────────────────────────────
    st.subheader("🔑 API Anahtarları")

    items = list(_API_KEYS.items())
    cols  = st.columns(4)
    for i, (env_key, label) in enumerate(items):
        with cols[i % 4]:
            _key_card(label, env_key)

    defined = sum(1 for k in _API_KEYS if os.getenv(k, "").strip())
    missing = len(_API_KEYS) - defined
    if missing:
        st.warning(f"{missing} anahtar tanımlanmamış — ilgili modeller/özellikler çalışmayabilir.")
    else:
        st.success("Tüm anahtarlar tanımlı.")

    st.markdown("---")

    # ── 3. Son 24 Saat ────────────────────────────────────────────────────────
    st.subheader("📊 Son 24 Saat Denetim Özeti")

    stats = _audit_stats_24h()
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Toplam Denetim", stats["total"])
    s2.metric("✅ Uygun",       stats["safe"])
    s3.metric("❌ Uygunsuz",    stats["unsafe"])
    rate = round(stats["safe"] / stats["total"] * 100) if stats["total"] else 0
    s4.metric("Uygunluk Oranı", f"%{rate}")

    st.markdown("---")

    # ── 4. Güvenlik ───────────────────────────────────────────────────────────
    st.subheader("🔒 Güvenlik Olayları")

    col_locked, col_attempts = st.columns(2)

    with col_locked:
        st.markdown("**Kilitli Hesaplar**")
        locked = _locked_users()
        if not locked:
            st.success("Kilitli hesap yok.")
        else:
            for u in locked:
                name = u.get("display_name") or u["username"]
                st.error(f"🔒 **{u['username']}** — {name}")
            if st.button("Tüm Kilitleri Aç", type="secondary"):
                from user.db import unlock_user
                for u in locked:
                    unlock_user(u["username"])
                st.success("Tüm kilitler açıldı.")
                st.rerun()

    with col_attempts:
        st.markdown("**Aktif Başarısız Giriş Denemeleri**")
        attempts = _pending_attempts()
        if not attempts:
            st.success("Bekleyen başarısız deneme yok.")
        else:
            for username, count in sorted(attempts.items(), key=lambda x: -x[1]):
                color  = "#e74c3c" if count >= 4 else "#e67e22"
                filled = "█" * count + "░" * (5 - count)
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:6px;'>"
                    f"<span style='width:110px;font-weight:600;'>{username}</span>"
                    f"<span style='font-family:monospace;color:{color};'>{filled}</span>"
                    f"<span style='color:{color};font-size:0.85rem;'>{count}/5</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.markdown("---")
    st.caption(f"Son yenileme: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
