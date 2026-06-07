from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import SKLearnVectorStore
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from exam_helper.config import EMBEDDING_MODEL_NAME

BACKEND_MARKER = "vectorstore_backend.txt"
SKLEARN_STORE_FILE = "sklearn_store.json"


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def vectorstore_exists(vectorstore_dir: Path) -> bool:
    return vectorstore_dir.exists() and any(vectorstore_dir.iterdir())


def _marker_path(vectorstore_dir: Path) -> Path:
    return vectorstore_dir / BACKEND_MARKER


def _set_backend(vectorstore_dir: Path, backend: str) -> None:
    _marker_path(vectorstore_dir).write_text(backend, encoding="utf-8")


def _get_backend(vectorstore_dir: Path) -> str | None:
    marker = _marker_path(vectorstore_dir)
    if marker.exists():
        return marker.read_text(encoding="utf-8").strip()
    return None


def _load_chroma_class():
    try:
        from langchain_chroma import Chroma
    except Exception:
        return None
    return Chroma


def _build_sklearn(chunks: list[Document], vectorstore_dir: Path):
    persist_path = vectorstore_dir / SKLEARN_STORE_FILE
    vectorstore = SKLearnVectorStore.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_path=str(persist_path),
        serializer="json",
    )
    vectorstore.persist()
    _set_backend(vectorstore_dir, "sklearn")
    return vectorstore


def _load_sklearn(vectorstore_dir: Path):
    persist_path = vectorstore_dir / SKLEARN_STORE_FILE
    return SKLearnVectorStore(
        embedding=get_embeddings(),
        persist_path=str(persist_path),
        serializer="json",
    )


def build_vectorstore(chunks: list[Document], vectorstore_dir: Path, collection_name: str = "module_chunks") -> Any:
    vectorstore_dir.mkdir(parents=True, exist_ok=True)

    chroma_cls = _load_chroma_class()
    if chroma_cls is not None:
        try:
            vectorstore = chroma_cls.from_documents(
                documents=chunks,
                embedding=get_embeddings(),
                persist_directory=str(vectorstore_dir),
                collection_name=collection_name,
            )
            _set_backend(vectorstore_dir, "chroma")
            return vectorstore
        except Exception:
            pass

    return _build_sklearn(chunks=chunks, vectorstore_dir=vectorstore_dir)


def load_vectorstore(vectorstore_dir: Path, collection_name: str = "module_chunks") -> Any:
    backend = _get_backend(vectorstore_dir)

    if backend == "chroma":
        chroma_cls = _load_chroma_class()
        if chroma_cls is not None:
            try:
                return chroma_cls(
                    persist_directory=str(vectorstore_dir),
                    embedding_function=get_embeddings(),
                    collection_name=collection_name,
                )
            except Exception:
                pass

    if backend == "sklearn":
        return _load_sklearn(vectorstore_dir)

    if (vectorstore_dir / SKLEARN_STORE_FILE).exists():
        return _load_sklearn(vectorstore_dir)

    chroma_cls = _load_chroma_class()
    if chroma_cls is not None:
        try:
            return chroma_cls(
                persist_directory=str(vectorstore_dir),
                embedding_function=get_embeddings(),
                collection_name=collection_name,
            )
        except Exception:
            pass

    return _load_sklearn(vectorstore_dir)
