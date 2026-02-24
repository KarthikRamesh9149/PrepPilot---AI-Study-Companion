from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np
from langchain_core.documents import Document
from sklearn.feature_extraction.text import TfidfVectorizer

from exam_helper.config import LARGE_CHUNK_THRESHOLD


def build_topic_index_if_large(chunks: list[Document], topic_index_path: Path) -> None:
    if len(chunks) <= LARGE_CHUNK_THRESHOLD:
        return

    texts = [chunk.page_content for chunk in chunks]
    metas = [chunk.metadata for chunk in chunks]

    vectorizer = TfidfVectorizer(max_features=20000, stop_words="english")
    matrix = vectorizer.fit_transform(texts)
    payload = {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "texts": texts,
        "metas": metas,
    }
    topic_index_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, topic_index_path)


def _build_queries(seed: str, difficulty: str, topics: list[str] | None = None) -> list[str]:
    base = [
        f"Overview of {seed}",
        f"Core definitions and fundamentals in {seed}",
        f"Compare and contrast concepts in {seed}",
        f"Applied scenarios and exam-style reasoning for {seed} at {difficulty} level",
    ]
    if topics:
        for topic in topics[:6]:
            base.append(f"Key concepts and exam questions for {topic}")
    return base


def _to_context(doc: Document) -> dict:
    metadata = doc.metadata
    return {
        "chunk_id": metadata.get("chunk_id", "unknown"),
        "text": doc.page_content,
        "source_file": metadata.get("source_file", "unknown"),
        "source_type": metadata.get("source_type", "unknown"),
        "page_or_slide_number": int(metadata.get("page_or_slide_number", 1)),
        "snippet_reference": metadata.get("snippet_reference", doc.page_content[:180]),
    }


def _retrieve_from_topic_index(query: str, topic_index_path: Path, top_n: int = 25) -> list[dict]:
    if not topic_index_path.exists():
        return []

    payload = joblib.load(topic_index_path)
    vectorizer = payload["vectorizer"]
    matrix = payload["matrix"]
    texts = payload["texts"]
    metas = payload["metas"]

    qv = vectorizer.transform([query])
    sims = (matrix @ qv.T).toarray().reshape(-1)
    if sims.size == 0:
        return []

    top_idx = np.argpartition(-sims, min(top_n, sims.size - 1))[:top_n]
    ranked = sorted(top_idx.tolist(), key=lambda i: sims[i], reverse=True)

    contexts: list[dict] = []
    for idx in ranked:
        meta = metas[idx]
        contexts.append(
            {
                "chunk_id": meta.get("chunk_id", f"tfidf-{idx}"),
                "text": texts[idx],
                "source_file": meta.get("source_file", "unknown"),
                "source_type": meta.get("source_type", "unknown"),
                "page_or_slide_number": int(meta.get("page_or_slide_number", 1)),
                "snippet_reference": meta.get("snippet_reference", texts[idx][:180]),
            }
        )
    return contexts


def _get_docs_for_query(vectorstore: Any, query: str, k: int) -> list[Document]:
    try:
        retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": k, "fetch_k": max(40, k * 5)})
        return retriever.invoke(query)
    except Exception:
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        return retriever.invoke(query)


def retrieve_diverse_context(
    vectorstore: Any,
    seed_query: str,
    difficulty: str,
    k: int,
    topic_index_path: Path,
    status_callback: Callable[[str], None] | None = None,
    topics: list[str] | None = None,
    allowed_chunk_ids: set[str] | None = None,
) -> list[dict]:
    queries = _build_queries(seed_query, difficulty, topics)

    merged: list[dict] = []
    page_caps: defaultdict[tuple[str, int], int] = defaultdict(int)
    seen_ids: set[str] = set()

    for query in queries:
        if status_callback:
            status_callback(f"Preparing personalized context for {query}")

        docs = _get_docs_for_query(vectorstore=vectorstore, query=query, k=k)
        for doc in docs:
            context = _to_context(doc)
            chunk_id = context["chunk_id"]
            if allowed_chunk_ids is not None and chunk_id not in allowed_chunk_ids:
                continue
            key = (context["source_file"], context["page_or_slide_number"])
            if page_caps[key] >= 2:
                continue
            if chunk_id in seen_ids:
                continue
            page_caps[key] += 1
            seen_ids.add(chunk_id)
            merged.append(context)

        for context in _retrieve_from_topic_index(query, topic_index_path, top_n=max(8, k)):
            chunk_id = context["chunk_id"]
            if allowed_chunk_ids is not None and chunk_id not in allowed_chunk_ids:
                continue
            key = (context["source_file"], context["page_or_slide_number"])
            if page_caps[key] >= 2:
                continue
            if chunk_id in seen_ids:
                continue
            page_caps[key] += 1
            seen_ids.add(chunk_id)
            merged.append(context)

    # if filtering is too aggressive, fail open using already-seen diverse contexts
    if not merged and allowed_chunk_ids is not None:
        return retrieve_diverse_context(
            vectorstore=vectorstore,
            seed_query=seed_query,
            difficulty=difficulty,
            k=k,
            topic_index_path=topic_index_path,
            status_callback=status_callback,
            topics=topics,
            allowed_chunk_ids=None,
        )

    return merged[: max(k * 3, 18)]


def context_as_prompt_text(context_chunks: list[dict], max_chars: int = 18000) -> str:
    lines: list[str] = []
    current_len = 0

    for chunk in context_chunks:
        line = (
            f"chunk_id={chunk['chunk_id']} | file={chunk['source_file']} | "
            f"source={chunk['source_type']} | page_or_slide={chunk['page_or_slide_number']}\n"
            f"{chunk['text']}\n"
        )
        if current_len + len(line) > max_chars:
            break
        lines.append(line)
        current_len += len(line)

    return "\n---\n".join(lines)
