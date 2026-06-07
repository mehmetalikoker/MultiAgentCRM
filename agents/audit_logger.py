# -*- coding: utf-8 -*-
import streamlit as st
from datetime import datetime, timezone, timedelta

_MAX_TEXT_PREVIEW = 200
_MAX_SUMMARY = 3000


def _col():
    from user.mongo import get_db
    return get_db()["audit_logs"]


@st.cache_data(ttl=60)
def load_audit_log() -> list:
    return list(_col().find({}, {"_id": 0}).sort("timestamp", -1))


@st.cache_data(ttl=60)
def load_user_audit_log(username: str, days: int = 7) -> list:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    return list(
        _col()
        .find({"username": username, "timestamp": {"$gte": cutoff}}, {"_id": 0})
        .sort("timestamp", -1)
    )


def log_audit(
    *,
    username: str,
    agent: str,
    model: str,
    campaign_text: str,
    is_safe: bool | None = None,
    score: int | None = None,
    channel: str | None = None,
    result_summary: str = "",
) -> None:
    _col().insert_one({
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "username": username,
        "agent": agent,
        "model": model,
        "channel": channel,
        "campaign_text_preview": campaign_text[:_MAX_TEXT_PREVIEW],
        "is_safe": is_safe,
        "score": score,
        "result_summary": result_summary[:_MAX_SUMMARY],
    })
    load_audit_log.clear()
    load_user_audit_log.clear()
