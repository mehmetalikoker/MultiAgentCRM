# -*- coding: utf-8 -*-
import os
import streamlit as st
from pymongo import MongoClient


def _get_uri() -> str:
    try:
        return st.secrets["MONGODB_URI"]
    except Exception:
        pass
    uri = os.getenv("MONGODB_URI", "")
    if not uri:
        raise RuntimeError(
            "MONGODB_URI tanımlanmamış. "
            "Streamlit secrets veya .env dosyasına ekleyin."
        )
    return uri


@st.cache_resource
def get_db():
    client = MongoClient(_get_uri())
    db = client["agentcrm"]
    # TTL index'leri bağlantı kurulduğunda bir kez oluştur
    db["login_attempts"].create_index("created_at", expireAfterSeconds=300)
    db["reset_tokens"].create_index("created_at", expireAfterSeconds=1800)
    return db
