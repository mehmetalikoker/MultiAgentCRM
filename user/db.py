# -*- coding: utf-8 -*-
import os
import json
import hashlib

_USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")


def _get_supabase():
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    except Exception:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

    if url and key:
        from supabase import create_client
        return create_client(url, key)
    return None


def _local_load_list() -> list:
    if os.path.exists(_USERS_FILE):
        with open(_USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("users", [])
    try:
        import streamlit as st
        return [dict(u) for u in st.secrets.get("users", [])]
    except Exception:
        return []


def _local_save_list(users: list):
    with open(_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": users}, f, ensure_ascii=False, indent=2)


def load_users() -> dict:
    sb = _get_supabase()
    if sb:
        resp = sb.table("users").select("username, password_hash, display_name").execute()
        return {u["username"]: u for u in resp.data}
    return {u["username"]: u for u in _local_load_list()}


def load_users_list() -> list:
    sb = _get_supabase()
    if sb:
        resp = sb.table("users").select("username, password_hash, display_name").execute()
        return resp.data
    return _local_load_list()


def add_user(username: str, password: str, display_name: str) -> None:
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    sb = _get_supabase()
    if sb:
        sb.table("users").insert({
            "username": username,
            "password_hash": password_hash,
            "display_name": display_name or username,
        }).execute()
        return
    users = _local_load_list()
    users.append({"username": username, "password_hash": password_hash, "display_name": display_name or username})
    _local_save_list(users)


def delete_user(username: str) -> None:
    sb = _get_supabase()
    if sb:
        sb.table("users").delete().eq("username", username).execute()
        return
    users = [u for u in _local_load_list() if u["username"] != username]
    _local_save_list(users)
