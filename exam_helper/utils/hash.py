from __future__ import annotations

import hashlib
from pathlib import Path


def compute_module_hash(uploaded_files: list) -> str:
    """Deterministic hash from uploaded file names and content bytes."""
    hasher = hashlib.sha256()
    for uploaded in sorted(uploaded_files, key=lambda f: f.name.lower()):
        hasher.update(uploaded.name.encode("utf-8"))
        hasher.update(uploaded.getvalue())
    return hasher.hexdigest()


def hash_files_on_disk(paths: list[Path]) -> str:
    hasher = hashlib.sha256()
    for path in sorted(paths, key=lambda p: p.name.lower()):
        hasher.update(path.name.encode("utf-8"))
        hasher.update(path.read_bytes())
    return hasher.hexdigest()
