from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

from exam_helper.services.topic_service import infer_topic_for_text

ADMIN_META_TERMS = {
    "canvas",
    "academic integrity",
    "integrity expected",
    "plagiarism",
    "submission",
    "attendance",
    "thank you",
    "session date details",
    "course logistics",
}

BANNED_STEM_PATTERNS = [
    r"which statement is best supported by this module excerpt",
    r"directly supported by the cited excerpt",
    r"\bnot discussed at all in the module\b",
]


def _normalize_stem(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _is_duplicate(a: str, b: str, ratio_threshold: float = 0.86) -> bool:
    a_n = _normalize_stem(a)
    b_n = _normalize_stem(b)
    if a_n == b_n:
        return True
    if len(a_n) >= 40 and len(b_n) >= 40 and (a_n.startswith(b_n[:40]) or b_n.startswith(a_n[:40])):
        return True
    return SequenceMatcher(None, a_n, b_n).ratio() >= ratio_threshold


def _is_admin_meta_text(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in ADMIN_META_TERMS)


def _looks_template_question(question: str) -> bool:
    q = _normalize_stem(question)
    if len(q) < 24:
        return True
    if re.fullmatch(r"[\d\s]+", q):
        return True
    return any(re.search(pattern, q) for pattern in BANNED_STEM_PATTERNS)


def _clean_citations(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        file_name = str(item.get("file", "")).strip()
        snippet = str(item.get("snippet_reference", "")).strip()
        if not file_name:
            continue
        if _is_admin_meta_text(f"{file_name} {snippet}"):
            continue
        page_or_slide = int(item.get("page_or_slide", 1) or 1)
        cleaned.append(
            {
                "file": file_name,
                "page_or_slide": max(1, page_or_slide),
                "snippet_reference": snippet[:180],
            }
        )
    return cleaned


def _valid_question(item: dict[str, Any]) -> bool:
    if not isinstance(item, dict):
        return False
    question = str(item.get("question", "")).strip()
    if not question or _looks_template_question(question):
        return False
    citations = _clean_citations(item.get("citations", []))
    if not citations:
        return False
    return True


def _normalize_options(options: Any) -> dict[str, str] | None:
    if isinstance(options, dict):
        if set(options.keys()) == {"A", "B", "C", "D"}:
            casted = {k: str(v).strip() for k, v in options.items()}
            if all(casted[k] for k in {"A", "B", "C", "D"}):
                return casted
        return None
    if isinstance(options, list):
        vals: list[str] = []
        for item in options:
            if isinstance(item, str):
                vals.append(item.strip())
            elif isinstance(item, dict):
                if "text" in item:
                    vals.append(str(item["text"]).strip())
                elif "option_text" in item:
                    vals.append(str(item["option_text"]).strip())
                elif "value" in item:
                    vals.append(str(item["value"]).strip())
        if len(vals) >= 4 and all(vals[:4]):
            return {"A": vals[0], "B": vals[1], "C": vals[2], "D": vals[3]}
    return None


def normalize_candidate_pool(raw_json: dict, topics: list[str]) -> list[dict[str, Any]]:
    source: Any
    if isinstance(raw_json, list):
        source = raw_json
    elif isinstance(raw_json, dict):
        source = raw_json.get("candidate_questions")
        if not isinstance(source, list):
            source = raw_json.get("questions", [])
    else:
        source = []
    if not isinstance(source, list):
        return []

    normalized: list[dict[str, Any]] = []
    for i, item in enumerate(source, start=1):
        if not _valid_question(item):
            continue
        options = _normalize_options(item.get("options", {}))
        if not options:
            continue
        q = str(item.get("question", "")).strip()
        topic_tag = str(item.get("topic_tag", "")).strip() or infer_topic_for_text(q, topics)
        correct_option = str(item.get("correct_option", "A")).strip().upper()
        if correct_option not in {"A", "B", "C", "D"}:
            correct_option = "A"

        normalized.append(
            {
                "question_id": str(item.get("question_id", f"q{i}")),
                "topic_tag": topic_tag,
                "question": q,
                "options": options,
                "correct_option": correct_option,
                "explanation": str(item.get("explanation", "Based on your module content.")).strip(),
                "citations": _clean_citations(item.get("citations", [])),
            }
        )
    return normalized


def deduplicate_questions(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for item in candidates:
        if any(_is_duplicate(item["question"], prior["question"]) for prior in kept):
            continue
        kept.append(item)
    return kept


def enforce_topic_quota(candidates: list[dict[str, Any]], topics: list[str], final_count: int = 15) -> list[dict[str, Any]]:
    if not candidates:
        return []

    by_topic: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        by_topic.setdefault(c.get("topic_tag", "General"), []).append(c)

    selected: list[dict[str, Any]] = []
    required_topics = [t for t in topics[:6] if t in by_topic]

    for topic in required_topics:
        if by_topic.get(topic):
            selected.append(by_topic[topic].pop(0))

    pools = list(by_topic.items())
    idx = 0
    while len(selected) < final_count and pools:
        topic, items = pools[idx % len(pools)]
        if items:
            selected.append(items.pop(0))
        pools = [(t, it) for t, it in pools if it]
        if not pools:
            break
        idx += 1

    if len(selected) < final_count:
        for c in candidates:
            if c in selected:
                continue
            selected.append(c)
            if len(selected) >= final_count:
                break

    return selected[:final_count]


def coverage_summary(questions: list[dict[str, Any]]) -> list[str]:
    counts = Counter([q.get("topic_tag", "General") for q in questions])
    return [f"{topic} ({count})" for topic, count in counts.most_common(8)]
