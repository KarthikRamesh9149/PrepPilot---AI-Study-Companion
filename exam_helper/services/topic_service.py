from __future__ import annotations

import re
from collections import Counter

from langchain_core.documents import Document
from sklearn.feature_extraction.text import TfidfVectorizer

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "your",
    "have",
    "are",
    "was",
    "were",
    "into",
    "use",
    "using",
    "what",
    "when",
    "where",
    "how",
    "why",
    "can",
    "could",
    "would",
    "should",
    "not",
    "you",
}

ADMIN_META_TERMS = {
    "canvas",
    "integrity",
    "academic integrity",
    "plagiarism",
    "discussion board",
    "submission",
    "attendance",
    "deadline policy",
    "course outline",
    "grading policy",
}

GENERIC_NOISE = {
    "session",
    "lecture",
    "slides",
    "slide",
    "week",
    "module",
    "course",
    "exam",
    "test",
}

LOW_SIGNAL_TOKENS = {
    "node",
    "nodes",
    "frontier",
    "expand",
    "expnd",
    "expanded",
    "tested",
    "list",
}

STRONG_CONCEPT_TOKENS = {
    "search",
    "agent",
    "agents",
    "environment",
    "environments",
    "heuristic",
    "heuristics",
    "algorithm",
    "algorithms",
    "state",
    "states",
    "path",
    "paths",
    "cost",
    "informed",
    "uninformed",
    "evaluation",
    "strategy",
    "strategies",
    "knowledge",
    "reasoning",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())).strip()


def _to_title_case(phrase: str) -> str:
    words = phrase.split()
    out: list[str] = []
    for word in words:
        if word.upper() in {"AI", "UCS", "BFS", "DFS", "A*"}:
            out.append(word.upper())
        else:
            out.append(word.capitalize())
    return " ".join(out)


def _is_good_topic_label(topic: str) -> bool:
    normalized = _normalize(topic)
    if not normalized:
        return False
    if any(term in normalized for term in ADMIN_META_TERMS):
        return False

    words = normalized.split()
    if len(words) < 2 or len(words) > 6:
        return False
    if words[0].isdigit():
        return False
    if all(w.isdigit() for w in words):
        return False
    if sum(w.isdigit() for w in words) > 1:
        return False
    if any(len(w) == 1 and w not in {"a", "i"} for w in words):
        return False
    if sum(1 for w in words if w in GENERIC_NOISE) >= 2:
        return False
    if all(w in LOW_SIGNAL_TOKENS for w in words):
        return False
    if any(w in LOW_SIGNAL_TOKENS for w in words) and not any(w in STRONG_CONCEPT_TOKENS for w in words):
        return False
    return True


def sanitize_topic_candidates(topics: list[str], max_topics: int = 8) -> list[str]:
    cleaned: list[str] = []
    seen = set()
    for topic in topics:
        normalized = _normalize(str(topic))
        if not _is_good_topic_label(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(_to_title_case(normalized))
        if len(cleaned) >= max_topics:
            break
    return cleaned


def _heading_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:8]:
        normalized = _normalize(line)
        if not normalized:
            continue
        words = normalized.split()
        if 2 <= len(words) <= 6 and _is_good_topic_label(normalized):
            candidates.append(normalized)
    return candidates


def extract_topic_candidates(chunks: list[Document], max_topics: int = 8) -> list[str]:
    if not chunks:
        return []

    texts = [chunk.page_content for chunk in chunks if chunk.page_content.strip()]
    if not texts:
        return []

    topics: list[str] = []
    seen = set()

    # First pass: heading-like lines tend to be cleaner topic names.
    heading_counter = Counter()
    for text in texts:
        for heading in _heading_candidates(text):
            heading_counter[heading] += 1

    for heading, _ in heading_counter.most_common(max_topics * 2):
        if heading in seen:
            continue
        seen.add(heading)
        topics.append(_to_title_case(heading))
        if len(topics) >= max_topics:
            return topics

    # Second pass: TF-IDF phrases.
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 3), max_features=1200)
    matrix = vectorizer.fit_transform(texts)
    weights = matrix.sum(axis=0).A1
    vocab = vectorizer.get_feature_names_out()

    pairs = sorted(zip(vocab, weights), key=lambda x: x[1], reverse=True)
    for term, _ in pairs:
        normalized = _normalize(term)
        if not normalized:
            continue
        words = normalized.split()
        if len(words) < 2:
            continue
        if any(w in STOPWORDS for w in words):
            continue
        if not _is_good_topic_label(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        topics.append(_to_title_case(normalized))
        if len(topics) >= max_topics:
            break

    cleaned = sanitize_topic_candidates(topics, max_topics=max_topics)
    if cleaned:
        return cleaned

    # Fallback: frequent adjacent-word phrases.
    counter = Counter()
    for text in texts:
        words = [w for w in _normalize(text).split() if len(w) > 3 and w not in STOPWORDS]
        for i in range(len(words) - 1):
            counter[f"{words[i]} {words[i + 1]}"] += 1

    fallback = [_to_title_case(k) for k, _ in counter.most_common(max_topics * 3)]
    cleaned = sanitize_topic_candidates(fallback, max_topics=max_topics)
    if cleaned:
        return cleaned
    return ["Core Concepts", "Methods And Applications"]


def infer_topic_for_text(text: str, topics: list[str]) -> str:
    if not topics:
        return "General"
    text_n = _normalize(text)
    for topic in topics:
        t = _normalize(topic)
        if t and t in text_n:
            return topic
    return topics[0]


def profile_topic_weights(topic_confidence: list[dict] | None) -> dict[str, float]:
    if not topic_confidence:
        return {}
    mapv = {"Low": 1.25, "Medium": 1.0, "High": 0.8}
    out: dict[str, float] = {}
    for item in topic_confidence:
        topic = str(item.get("topic", "")).strip()
        conf = str(item.get("confidence", "Medium"))
        if topic:
            out[topic] = mapv.get(conf, 1.0)
    return out
