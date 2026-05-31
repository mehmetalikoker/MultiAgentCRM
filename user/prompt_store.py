# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
from user.mongo import get_db

_MAX_HISTORY = 10
_BASE = Path(__file__).parent.parent


def _col():
    return get_db()["prompts"]


def get_prompt(key: str, fallback_path: str) -> str:
    doc = _col().find_one({"key": key}, {"_id": 0, "content": 1})
    if doc:
        return doc["content"]
    return (_BASE / fallback_path).read_text(encoding="utf-8")


def save_prompt(key: str, content: str, updated_by: str) -> None:
    col = _col()
    existing = col.find_one({"key": key}, {"_id": 0})

    history = []
    if existing:
        history = existing.get("history", [])
        history.insert(0, {
            "content": existing["content"],
            "updated_at": existing.get("updated_at", ""),
            "updated_by": existing.get("updated_by", ""),
        })
        history = history[:_MAX_HISTORY]

    col.update_one(
        {"key": key},
        {"$set": {
            "key": key,
            "content": content,
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "updated_by": updated_by,
            "history": history,
        }},
        upsert=True,
    )


def get_prompt_meta(key: str) -> dict | None:
    return _col().find_one({"key": key}, {"_id": 0, "content": 0, "history": 0})


def get_history(key: str) -> list[dict]:
    doc = _col().find_one({"key": key}, {"history": 1, "_id": 0})
    return doc.get("history", []) if doc else []


def rollback_prompt(key: str, version_index: int, updated_by: str) -> None:
    history = get_history(key)
    if 0 <= version_index < len(history):
        save_prompt(key, history[version_index]["content"], updated_by)
