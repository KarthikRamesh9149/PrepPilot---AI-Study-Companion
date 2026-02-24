from __future__ import annotations

import os
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
import sys

from dotenv import load_dotenv
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exam_helper.runtime_warnings import suppress_runtime_warnings

suppress_runtime_warnings()

from exam_helper.config import (
    DEFAULT_GROQ_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    FALLBACK_MODEL_1,
    PRIMARY_MODEL,
)
from exam_helper.ingestion.chunking import chunk_documents
from exam_helper.ingestion.index_store import build_vectorstore, load_vectorstore
from exam_helper.ingestion.loaders import load_documents_from_paths
from exam_helper.models import QuizSet, StudyPlan
from exam_helper.retrieval.retriever import retrieve_diverse_context
from exam_helper.services.groq_client import GroqClient
from exam_helper.services.pdf_export import build_study_plan_pdf
from exam_helper.services.quiz_service import generate_quiz, score_quiz
from exam_helper.services.topic_service import extract_topic_candidates
from exam_helper.services.study_plan_service import generate_study_plan
from exam_helper.utils.cache import cache_key, get_cached, set_cached


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_quiz(quiz: QuizSet) -> None:
    assert_true(len(quiz.questions) == 15, f"Expected 15 questions, got {len(quiz.questions)}")
    for i, q in enumerate(quiz.questions, start=1):
        assert_true(set(q.options.keys()) == {"A", "B", "C", "D"}, f"Q{i}: options keys mismatch")
        assert_true(q.correct_option in {"A", "B", "C", "D"}, f"Q{i}: invalid correct option")
        assert_true(len(q.citations) > 0, f"Q{i}: missing citations")
        for c in q.citations:
            assert_true(bool(c.file.strip()), f"Q{i}: empty citation file")
            assert_true(c.page_or_slide >= 1, f"Q{i}: invalid citation page/slide")
            assert_true(bool(c.snippet_reference.strip()), f"Q{i}: empty citation snippet")


def validate_study_plan(plan: StudyPlan, today: date, exam_date: date) -> None:
    assert_true(plan.exam_date == exam_date, "Study plan exam_date mismatch")
    assert_true(plan.today == today, "Study plan today mismatch")
    assert_true(len(plan.prioritized_topics) > 0, "No prioritized topics")
    assert_true(len(plan.how_to_study) > 0, "No how_to_study items")
    assert_true(len(plan.important_questions) > 0, "No important questions")

    expected_days = (exam_date - today).days + 1
    assert_true(len(plan.daily_schedule) == expected_days, f"Daily schedule expected {expected_days}, got {len(plan.daily_schedule)}")

    for topic in plan.prioritized_topics:
        assert_true(len(topic.citations) > 0, f"Topic '{topic.topic}' missing citations")
    for item in plan.how_to_study:
        assert_true(len(item.citations) > 0, f"How-to item '{item.tactic}' missing citations")
    for q in plan.important_questions:
        assert_true(len(q.citations) > 0, f"Important question '{q.topic}' missing citations")


def run() -> None:
    load_dotenv()

    pdf_path = Path("36121 Session 1 Lecture Slide.pdf")
    assert_true(pdf_path.exists(), f"PDF not found: {pdf_path}")

    # UI structure check
    at = AppTest.from_file("app.py").run(timeout=180)
    tabs = [t.label for t in at.tabs]
    assert_true(tabs == ["Live Quiz", "Study Plan"], f"Unexpected tabs: {tabs}")

    # Backend e2e with real PDF
    docs = load_documents_from_paths([pdf_path])
    assert_true(len(docs) > 0, "No documents loaded from PDF")

    chunks = chunk_documents(docs)
    assert_true(len(chunks) > 0, "No chunks generated")
    topics = extract_topic_candidates(chunks)

    root = Path(".exam_helper_data") / "e2e_full"
    vector_dir = root / "vectorstore"
    topic_index_path = root / "topic_index.joblib"
    cache_path = root / "cache.json"
    root.mkdir(parents=True, exist_ok=True)

    build_vectorstore(chunks=chunks, vectorstore_dir=vector_dir, collection_name="e2e")
    vectorstore = load_vectorstore(vector_dir, collection_name="e2e")

    quiz_context = retrieve_diverse_context(
        vectorstore=vectorstore,
        seed_query="module exam preparation",
        difficulty="Medium",
        k=8,
        topic_index_path=topic_index_path,
        topics=topics,
    )
    assert_true(len(quiz_context) > 0, "No retrieval context for quiz")

    api_key = os.getenv("GROQ_API_KEY_1") or os.getenv("GROQ_API_KEY")
    assert_true(bool(api_key), "Missing GROQ_API_KEY_1/GROQ_API_KEY")

    client = GroqClient(
        api_key=api_key,
        base_url=os.getenv("GROQ_BASE_URL", DEFAULT_GROQ_BASE_URL),
        max_retries=int(os.getenv("MAX_RETRIES", str(DEFAULT_MAX_RETRIES))),
        timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))),
    )

    model_chain = [
        os.getenv("PRIMARY_MODEL", PRIMARY_MODEL),
        os.getenv("FALLBACK_MODEL_1", FALLBACK_MODEL_1),
    ]

    quiz, quiz_model = generate_quiz(
        groq_client=client,
        context_chunks=quiz_context,
        difficulty="Medium",
        model_chain=model_chain,
        topics=topics,
    )
    validate_quiz(quiz)

    # Score simulation
    answers = {q.question_id: "A" for q in quiz.questions}
    score, details = score_quiz(quiz, answers)
    assert_true(0 <= score <= 15, f"Score out of range: {score}")
    assert_true(len(details) == 15, f"Expected 15 score details, got {len(details)}")

    # Cache roundtrip
    quiz_key = cache_key(["e2e", "quiz", "Medium"])
    set_cached(cache_path, quiz_key, quiz.model_dump(mode="json"))
    cached_quiz = get_cached(cache_path, quiz_key)
    assert_true(cached_quiz is not None, "Quiz cache miss after write")

    # Study plan generation
    today = date.today()
    exam_date = today + timedelta(days=7)

    plan_context = retrieve_diverse_context(
        vectorstore=vectorstore,
        seed_query="complete exam study planning based on module",
        difficulty="Medium",
        k=8,
        topic_index_path=topic_index_path,
        topics=topics,
    )
    assert_true(len(plan_context) > 0, "No retrieval context for study plan")

    plan, plan_model = generate_study_plan(
        groq_client=client,
        context_chunks=plan_context,
        today=today,
        exam_date=exam_date,
        model_chain=model_chain,
        student_profile={
            "hours_per_day": 2,
            "preferred_study_window": "Evening",
            "topic_confidence": [{"topic": t, "confidence": "Medium"} for t in topics[:5]],
        },
    )
    validate_study_plan(plan, today=today, exam_date=exam_date)

    plan_key = cache_key(["e2e", "plan", today.isoformat(), exam_date.isoformat()])
    set_cached(cache_path, plan_key, plan.model_dump(mode="json"))
    cached_plan = get_cached(cache_path, plan_key)
    assert_true(cached_plan is not None, "Plan cache miss after write")

    # PDF export validation
    pdf_bytes = build_study_plan_pdf(plan)
    assert_true(pdf_bytes.startswith(b"%PDF"), "Study plan export is not a PDF")
    reader = PdfReader(BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert_true("Prioritized Topics" in text, "PDF missing 'Prioritized Topics'")
    assert_true("Day-by-Day Schedule" in text, "PDF missing 'Day-by-Day Schedule'")
    assert_true("Important Questions" in text, "PDF missing 'Important Questions'")

    print("E2E_UI_TABS_OK=1")
    print(f"E2E_PAGES={len(docs)}")
    print(f"E2E_CHUNKS={len(chunks)}")
    print(f"E2E_QUIZ_QUESTIONS={len(quiz.questions)}")
    print(f"E2E_QUIZ_MODEL={quiz_model}")
    print(f"E2E_QUIZ_SCORE_SIM={score}")
    print(f"E2E_PLAN_DAYS={len(plan.daily_schedule)}")
    print(f"E2E_PLAN_MODEL={plan_model}")
    print("E2E_PDF_OK=1")
    print("E2E_STATUS=PASS")


if __name__ == "__main__":
    run()
