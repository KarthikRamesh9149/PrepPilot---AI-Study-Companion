from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save_json(path: Path, data: Any) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def cache_key(parts: list[str]) -> str:
    return "|".join(parts)


def get_cached(cache_path: Path, key: str) -> Any | None:
    store = load_json(cache_path, default={})
    return store.get(key)


def set_cached(cache_path: Path, key: str, value: Any) -> None:
    store = load_json(cache_path, default={})
    store[key] = value
    save_json(cache_path, store)
