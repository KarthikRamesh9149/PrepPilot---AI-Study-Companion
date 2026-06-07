from __future__ import annotations

import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from exam_helper.config import CHUNK_OVERLAP, CHUNK_SIZE
from exam_helper.utils.cache import load_json, save_json

SNIPPET_LENGTH = 180


def chunk_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    split_docs = splitter.split_documents(documents)

    enriched: list[Document] = []
    for idx, chunk in enumerate(split_docs, start=1):
        snippet = re.sub(r"\s+", " ", chunk.page_content).strip()[:SNIPPET_LENGTH]
        metadata = dict(chunk.metadata)
        metadata["chunk_id"] = f"chunk-{idx}"
        metadata["snippet_reference"] = snippet
        enriched.append(Document(page_content=chunk.page_content, metadata=metadata))
    return enriched


def save_chunks(path: Path, chunks: list[Document]) -> None:
    payload = [
        {
            "page_content": chunk.page_content,
            "metadata": chunk.metadata,
        }
        for chunk in chunks
    ]
    save_json(path, payload)


def load_chunks(path: Path) -> list[Document]:
    payload = load_json(path, default=[])
    return [Document(page_content=item["page_content"], metadata=item["metadata"]) for item in payload]
