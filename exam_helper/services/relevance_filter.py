from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

ADMIN_KEYWORDS = {
    "academic integrity", "plagiarism", "canvas", "discussion board", "submit", "submission", "deadline", "attendance",
    "policy", "announcement", "grading rubric", "assessment portal", "enrollment", "office hour", "welcome", "syllabus logistics",
}

EXAM_SIGNAL_WORDS = {
    "algorithm", "search", "agent", "knowledge", "logic", "reasoning", "state space", "heuristic", "inference",
    "complexity", "model", "optimization", "proof", "theorem", "classification", "learning", "probability", "planning",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())).strip()


def _score_text(text: str, topic_terms: list[str]) -> tuple[float, list[str], float, float]:
    norm = _normalize(text)
    reasons: list[str] = []

    admin_hits = sum(1 for kw in ADMIN_KEYWORDS if kw in norm)
    if admin_hits:
        reasons.append("contains_lms_or_policy_terms")

    exam_hits = sum(1 for kw in EXAM_SIGNAL_WORDS if kw in norm)
    topic_hits = sum(1 for t in topic_terms if t and t in norm)

    admin_score = min(1.0, admin_hits / 3.0)
    exam_score = min(1.0, (exam_hits + topic_hits) / 6.0)

    combined = max(0.0, min(1.0, 0.65 * exam_score + 0.35 * (1 - admin_score)))
    return combined, reasons, admin_score, exam_score


def classify_chunks(chunks: list[Document], topics: list[str]) -> dict[str, dict[str, Any]]:
    topic_terms = [_normalize(t) for t in topics]
    labels: dict[str, dict[str, Any]] = {}

    for chunk in chunks:
        cid = str(chunk.metadata.get("chunk_id", ""))
        if not cid:
            continue

        score, reasons, admin_score, exam_score = _score_text(chunk.page_content, topic_terms)
        if admin_score >= 0.45 and exam_score < 0.35:
            label = "admin_meta"
            if "contains_lms_or_policy_terms" not in reasons:
                reasons.append("policy_language")
        elif score >= 0.5:
            label = "core_exam_content"
        else:
            label = "uncertain"

        labels[cid] = {
            "label": label,
            "score": round(score, 3),
            "reason_codes": reasons,
        }

    return labels


def apply_relevance_labels(chunks: list[Document], labels: dict[str, dict], overrides: dict[str, bool] | None = None) -> list[Document]:
    overrides = overrides or {}
    out: list[Document] = []
    for chunk in chunks:
        cid = str(chunk.metadata.get("chunk_id", ""))
        label_info = labels.get(cid, {"label": "uncertain", "score": 0.5, "reason_codes": []})
        restored = bool(overrides.get(cid, False))
        chunk.metadata["relevance_label"] = label_info.get("label", "uncertain")
        chunk.metadata["relevance_score"] = float(label_info.get("score", 0.5))
        chunk.metadata["relevance_reason_codes"] = label_info.get("reason_codes", [])
        chunk.metadata["is_restored"] = restored
        out.append(chunk)
    return out


def allowed_chunk_ids(chunks: list[Document]) -> set[str]:
    allowed: set[str] = set()
    for chunk in chunks:
        cid = str(chunk.metadata.get("chunk_id", ""))
        if not cid:
            continue
        label = str(chunk.metadata.get("relevance_label", "uncertain"))
        restored = bool(chunk.metadata.get("is_restored", False))
        if restored or label in {"core_exam_content", "uncertain"}:
            allowed.add(cid)
    return allowed


def excluded_preview(chunks: list[Document], max_items: int = 5) -> list[dict[str, Any]]:
    items = []
    for chunk in chunks:
        label = str(chunk.metadata.get("relevance_label", "uncertain"))
        if label != "admin_meta" or bool(chunk.metadata.get("is_restored", False)):
            continue
        items.append(
            {
                "chunk_id": chunk.metadata.get("chunk_id", ""),
                "file": chunk.metadata.get("source_file", "unknown"),
                "page_or_slide": int(chunk.metadata.get("page_or_slide_number", 1)),
                "reason_codes": chunk.metadata.get("relevance_reason_codes", []),
                "snippet_reference": chunk.metadata.get("snippet_reference", "")[:140],
            }
        )
        if len(items) >= max_items:
            break
    return items


def overrides_hash(overrides: dict[str, bool]) -> str:
    payload = json.dumps(overrides, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
