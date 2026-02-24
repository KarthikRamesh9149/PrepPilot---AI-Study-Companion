from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exam_helper.runtime_warnings import suppress_runtime_warnings

suppress_runtime_warnings()

from exam_helper.ingestion.chunking import chunk_documents
from exam_helper.ingestion.index_store import build_vectorstore, load_vectorstore
from exam_helper.ingestion.loaders import load_documents_from_paths
from exam_helper.retrieval.retriever import retrieve_diverse_context
from exam_helper.services.groq_client import GroqClient
from exam_helper.services.quiz_service import generate_quiz
from exam_helper.services.topic_service import extract_topic_candidates


def run_smoke(pdf_path: Path, with_llm: bool) -> None:
    if not pdf_path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

    docs = load_documents_from_paths([pdf_path])
    if not docs:
        raise RuntimeError("No pages extracted from PDF")

    chunks = chunk_documents(docs)
    if not chunks:
        raise RuntimeError("No chunks generated from extracted pages")

    smoke_dir = Path(".exam_helper_data") / "smoke_run"
    vs_dir = smoke_dir / "vectorstore"
    topic_index = smoke_dir / "topic_index.joblib"
    smoke_dir.mkdir(parents=True, exist_ok=True)

    build_vectorstore(chunks, vs_dir, collection_name="smoke")
    vectorstore = load_vectorstore(vs_dir, collection_name="smoke")
    topics = extract_topic_candidates(chunks)

    context = retrieve_diverse_context(
        vectorstore=vectorstore,
        seed_query="module exam preparation",
        difficulty="Medium",
        k=8,
        topic_index_path=topic_index,
        topics=topics,
    )

    print(f"pages_loaded={len(docs)}")
    print(f"chunks_created={len(chunks)}")
    print(f"retrieved_context_chunks={len(context)}")
    if context:
        first = context[0]
        print(
            "first_citation="
            f"{first['source_file']}|{first['page_or_slide_number']}|{first['chunk_id']}"
        )

    if with_llm:
        api_key = os.getenv("GROQ_API_KEY_1") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("LLM smoke test requested but GROQ_API_KEY_1/GROQ_API_KEY is missing")

        primary = os.getenv("PRIMARY_MODEL", "llama-3.1-8b-instant")
        fallback = os.getenv("FALLBACK_MODEL_1", "openai/gpt-oss-20b")
        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        max_retries = int(os.getenv("MAX_RETRIES", "1"))
        timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

        client = GroqClient(
            api_key=api_key,
            base_url=base_url,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )

        quiz, model_used = generate_quiz(
            groq_client=client,
            context_chunks=context,
            difficulty="Easy",
            model_chain=[primary, fallback],
            topics=topics,
        )
        print(f"quiz_questions={len(quiz.questions)}")
        print(f"quiz_model_used={model_used}")


if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Smoke test PrepPilot with a real PDF.")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--with-llm", action="store_true", help="Also run one Groq quiz generation call")
    args = parser.parse_args()

    run_smoke(pdf_path=Path(args.pdf), with_llm=args.with_llm)
