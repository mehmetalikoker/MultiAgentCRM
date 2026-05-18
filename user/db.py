# -*- coding: utf-8 -*-
import os
import json
import hashlib
import requests

_USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")


def _supabase_config():
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    except Exception:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
    return url, key


def _headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


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
    url, key = _supabase_config()
    if url and key:
        resp = requests.get(
            f"{url}/rest/v1/users",
            headers={**_headers(key), "Accept": "application/json"},
            params={"select": "username,password_hash,display_name"},
        )
        resp.raise_for_status()
        return {u["username"]: u for u in resp.json()}
    return {u["username"]: u for u in _local_load_list()}


def load_users_list() -> list:
    url, key = _supabase_config()
    if url and key:
        resp = requests.get(
            f"{url}/rest/v1/users",
            headers={**_headers(key), "Accept": "application/json"},
            params={"select": "username,password_hash,display_name"},
        )
        resp.raise_for_status()
        return resp.json()
    return _local_load_list()


def add_user(username: str, password: str, display_name: str) -> None:
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    url, key = _supabase_config()
    if url and key:
        resp = requests.post(
            f"{url}/rest/v1/users",
            headers=_headers(key),
            json={"username": username, "password_hash": password_hash, "display_name": display_name or username},
        )
        resp.raise_for_status()
        return
    users = _local_load_list()
    users.append({"username": username, "password_hash": password_hash, "display_name": display_name or username})
    _local_save_list(users)


def delete_user(username: str) -> None:
    url, key = _supabase_config()
    if url and key:
        resp = requests.delete(
            f"{url}/rest/v1/users",
            headers=_headers(key),
            params={"username": f"eq.{username}"},
        )
        resp.raise_for_status()
        return
    users = [u for u in _local_load_list() if u["username"] != username]
    _local_save_list(users)
