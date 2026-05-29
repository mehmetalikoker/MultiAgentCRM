# -*- coding: utf-8 -*-
import hashlib
from user.mongo import get_db


def _col():
    return get_db()["users"]


def load_users() -> dict:
    return {u["username"]: u for u in _col().find({}, {"_id": 0})}


def load_users_list() -> list:
    return list(_col().find({}, {"_id": 0}))


def add_user(username: str, password: str, display_name: str, email: str = "", role: str = "user") -> None:
    entry = {
        "username": username,
        "password_hash": hashlib.sha256(password.encode()).hexdigest(),
        "display_name": display_name or username,
        "role": role,
    }
    if email:
        entry["email"] = email.strip().lower()
    _col().insert_one(entry)


def set_user_role(username: str, role: str) -> None:
    _col().update_one({"username": username}, {"$set": {"role": role}})


def update_password(username: str, new_password: str) -> None:
    _col().update_one(
        {"username": username},
        {"$set": {"password_hash": hashlib.sha256(new_password.encode()).hexdigest()}},
    )


def get_user_by_email(email: str) -> dict | None:
    return _col().find_one({"email": email.strip().lower()}, {"_id": 0})


def set_user_email(username: str, email: str) -> None:
    _col().update_one({"username": username}, {"$set": {"email": email.strip().lower()}})


def delete_user(username: str) -> None:
    _col().delete_one({"username": username})


def lock_user(username: str) -> None:
    _col().update_one({"username": username}, {"$set": {"locked": True}})


def unlock_user(username: str) -> None:
    _col().update_one({"username": username}, {"$unset": {"locked": ""}})


def set_active_token(username: str, token_id: str) -> None:
    _col().update_one({"username": username}, {"$set": {"active_token_id": token_id}})


def get_active_token(username: str) -> str | None:
    user = _col().find_one({"username": username}, {"active_token_id": 1, "_id": 0})
    return user.get("active_token_id") if user else None


def clear_active_token(username: str) -> None:
    _col().update_one({"username": username}, {"$unset": {"active_token_id": ""}})
