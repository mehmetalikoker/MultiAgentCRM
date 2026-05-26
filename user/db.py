# -*- coding: utf-8 -*-
import os
import json
import hashlib

_USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")


def load_users() -> dict:
    if not os.path.exists(_USERS_FILE):
        return {}
    with open(_USERS_FILE, "r", encoding="utf-8") as f:
        return {u["username"]: u for u in json.load(f).get("users", [])}


def load_users_list() -> list:
    if not os.path.exists(_USERS_FILE):
        return []
    with open(_USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("users", [])


def _save(users: list):
    with open(_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": users}, f, ensure_ascii=False, indent=2)


def add_user(username: str, password: str, display_name: str, email: str = "") -> None:
    users = load_users_list()
    entry = {
        "username": username,
        "password_hash": hashlib.sha256(password.encode()).hexdigest(),
        "display_name": display_name or username,
    }
    if email:
        entry["email"] = email.strip().lower()
    users.append(entry)
    _save(users)


def update_password(username: str, new_password: str) -> None:
    users = load_users_list()
    for u in users:
        if u["username"] == username:
            u["password_hash"] = hashlib.sha256(new_password.encode()).hexdigest()
            break
    _save(users)


def get_user_by_email(email: str) -> dict | None:
    for u in load_users_list():
        if u.get("email", "").lower() == email.strip().lower():
            return u
    return None


def set_user_email(username: str, email: str) -> None:
    users = load_users_list()
    for u in users:
        if u["username"] == username:
            u["email"] = email.strip().lower()
            break
    _save(users)


def delete_user(username: str) -> None:
    _save([u for u in load_users_list() if u["username"] != username])


def lock_user(username: str) -> None:
    users = load_users_list()
    for u in users:
        if u["username"] == username:
            u["locked"] = True
            break
    _save(users)


def unlock_user(username: str) -> None:
    users = load_users_list()
    for u in users:
        if u["username"] == username:
            u.pop("locked", None)
            break
    _save(users)


def set_active_token(username: str, token_id: str) -> None:
    users = load_users_list()
    for u in users:
        if u["username"] == username:
            u["active_token_id"] = token_id
            break
    _save(users)


def get_active_token(username: str) -> str | None:
    return load_users().get(username, {}).get("active_token_id")


def clear_active_token(username: str) -> None:
    users = load_users_list()
    for u in users:
        if u["username"] == username:
            u.pop("active_token_id", None)
            break
    _save(users)
