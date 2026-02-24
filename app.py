from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from streamlit.errors import StreamlitSecretNotFoundError

from exam_helper.runtime_warnings import suppress_runtime_warnings

suppress_runtime_warnings()

from exam_helper.config import (
    APP_NAME,
    CACHE_SCHEMA_VERSION,
    DEFAULT_GROQ_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_PLAN_MODEL,
    DEFAULT_QUIZ_DIFFICULTY,
    DEFAULT_QUIZ_MODEL,
    DEFAULT_RETRIEVAL_K,
    DEFAULT_STUDY_HOURS_PER_DAY,
    DEFAULT_TIMEOUT_SECONDS,
    PLAN_MODEL_FALLBACK,
    QUIZ_MODEL_FALLBACK,
    ensure_data_dirs,
    module_chunks_path,
    module_dir,
    module_manifest_path,
    module_plan_cache_path,
    module_quiz_cache_path,
    module_relevance_labels_path,
    module_relevance_overrides_path,
    module_topic_index_path,
    module_vectorstore_dir,
)
from exam_helper.ingestion.chunking import chunk_documents, load_chunks, save_chunks
from exam_helper.ingestion.index_store import build_vectorstore, load_vectorstore, vectorstore_exists
from exam_helper.ingestion.loaders import load_documents_from_paths, save_uploaded_files
from exam_helper.retrieval.retriever import build_topic_index_if_large, retrieve_diverse_context
from exam_helper.services.groq_client import GroqClient
from exam_helper.services.pdf_export import build_study_plan_pdf
from exam_helper.services.quiz_service import generate_quiz, score_quiz
from exam_helper.services.relevance_filter import (
    allowed_chunk_ids,
    apply_relevance_labels,
    classify_chunks,
    excluded_preview,
    overrides_hash,
)
from exam_helper.services.study_plan_service import generate_study_plan
from exam_helper.services.topic_service import extract_topic_candidates, sanitize_topic_candidates
from exam_helper.ui.components import (
    card_end,
    card_start,
    coverage_pills,
    empty_state,
    evidence_warning,
    hero,
    section_intro,
    status_strip,
    topic_row,
)
from exam_helper.ui.styles import apply_global_styles
from exam_helper.utils.cache import cache_key, get_cached, load_json, save_json, set_cached
from exam_helper.utils.guards import generation_allowed
from exam_helper.utils.hash import compute_module_hash

load_dotenv()
ensure_data_dirs()

st.set_page_config(page_title=APP_NAME, layout="wide")
apply_global_styles()


STATE_DEFAULTS = {
    "module_id": "",
    "ingestion_ready": False,
    "chunk_count": 0,
    "last_processed": "-",
    "module_topics": [],
    "quiz_set": None,
    "quiz_model_used": "",
    "quiz_score": None,
    "quiz_details": None,
    "study_plan": None,
    "plan_model_used": "",
}
for key, value in STATE_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

if st.session_state.get("module_topics"):
    cleaned_topics = sanitize_topic_candidates(st.session_state["module_topics"], max_topics=8)
    if cleaned_topics:
        st.session_state["module_topics"] = cleaned_topics


@st.cache_resource(show_spinner=False)
def get_groq_client(api_key: str, base_url: str, max_retries: int, timeout_seconds: float) -> GroqClient:
    return GroqClient(
        api_key=api_key,
        base_url=base_url,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    )


@st.cache_resource(show_spinner=False)
def get_vectorstore(module_id_value: str):
    return load_vectorstore(module_vectorstore_dir(module_id_value))


def _safe_secret(name: str) -> str:
    try:
        return st.secrets.get(name, "")
    except StreamlitSecretNotFoundError:
        return ""
    except Exception:
        return ""


def _file_signature(path: Path) -> str:
    if not path.exists():
        return "missing"
    stat = path.stat()
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def _build_model_chain(preferred: str, fallback: list[str]) -> list[str]:
    chain = [preferred] + fallback
    seen = set()
    out: list[str] = []
    for item in chain:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _validate_citations(citations: list[Any]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for c in citations:
        if hasattr(c, "model_dump"):
            c = c.model_dump()
        if not isinstance(c, dict):
            continue
        file_name = str(c.get("file", "")).strip()
        if not file_name or "not found in your module" in file_name.lower():
            continue
        valid.append(
            {
                "file": file_name,
                "page_or_slide": int(c.get("page_or_slide", 1) or 1),
                "snippet_reference": str(c.get("snippet_reference", "")).strip(),
            }
        )
    return valid


@st.cache_resource(show_spinner=False)
def _load_chunk_bundle_cached(
    module_id_value: str,
    labels_sig: str,
    overrides_sig: str,
) -> tuple[list, dict[str, bool], list[dict], set[str]]:
    del labels_sig, overrides_sig
    chunks = load_chunks(module_chunks_path(module_id_value))
    labels = load_json(module_relevance_labels_path(module_id_value), default={})
    if not labels:
        topics = extract_topic_candidates(chunks)
        labels = classify_chunks(chunks, topics)
        save_json(module_relevance_labels_path(module_id_value), labels)
    overrides = load_json(module_relevance_overrides_path(module_id_value), default={})
    chunks = apply_relevance_labels(chunks, labels, overrides)
    preview = excluded_preview(chunks, max_items=5)
    allowed_ids = allowed_chunk_ids(chunks)
    return chunks, overrides, preview, allowed_ids


def _load_chunk_bundle(module_id_value: str) -> tuple[list, dict[str, bool], list[dict], set[str]]:
    labels_path = module_relevance_labels_path(module_id_value)
    overrides_path = module_relevance_overrides_path(module_id_value)
    return _load_chunk_bundle_cached(
        module_id_value=module_id_value,
        labels_sig=_file_signature(labels_path),
        overrides_sig=_file_signature(overrides_path),
    )


def _topic_confidence_input(topics: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    clean_topics = sanitize_topic_candidates(topics, max_topics=4)
    if not clean_topics:
        return rows
    st.markdown("#### Confidence on key topics")
    st.caption("Quickly mark weak areas so your plan prioritizes them.")
    for topic in clean_topics:
        key = f"conf_{topic}"
        default_conf = st.session_state.get(key, "Medium")
        if default_conf not in {"Low", "Medium", "High"}:
            default_conf = "Medium"
        confidence = st.select_slider(
            topic,
            options=["Low", "Medium", "High"],
            value=default_conf,
            key=key,
        )
        rows.append({"topic": topic, "confidence": confidence})
    return rows


def _process_files(uploaded_files: list) -> tuple[str, int, str, list[str]]:
    module_id_value = compute_module_hash(uploaded_files)
    mdir = module_dir(module_id_value)
    mdir.mkdir(parents=True, exist_ok=True)

    manifest_path = module_manifest_path(module_id_value)
    chunks_path = module_chunks_path(module_id_value)
    vector_dir = module_vectorstore_dir(module_id_value)
    labels_path = module_relevance_labels_path(module_id_value)

    cached_ready = manifest_path.exists() and chunks_path.exists() and vectorstore_exists(vector_dir)
    if cached_ready:
        manifest = load_json(manifest_path, default={})
        chunks = load_chunks(chunks_path)
        topics = sanitize_topic_candidates(manifest.get("module_topics") or [], max_topics=8)
        if not topics:
            topics = extract_topic_candidates(chunks)
            manifest["module_topics"] = topics
            save_json(manifest_path, manifest)
        if not labels_path.exists():
            labels = classify_chunks(chunks, topics)
            save_json(labels_path, labels)
        return (
            module_id_value,
            len(chunks),
            manifest.get("last_processed", datetime.now().isoformat(timespec="seconds")),
            topics,
        )

    file_paths = save_uploaded_files(uploaded_files=uploaded_files, module_dir=mdir)
    documents = load_documents_from_paths(file_paths)
    if not documents:
        raise ValueError("We couldn't read meaningful text from the uploaded materials.")

    chunks = chunk_documents(documents)
    if not chunks:
        raise ValueError("We couldn't split your materials into study sections.")

    topics = extract_topic_candidates(chunks)
    labels = classify_chunks(chunks, topics)
    chunks = apply_relevance_labels(chunks, labels, overrides={})

    save_chunks(chunks_path, chunks)
    save_json(labels_path, labels)
    save_json(module_relevance_overrides_path(module_id_value), {})

    build_vectorstore(chunks=chunks, vectorstore_dir=vector_dir)
    build_topic_index_if_large(chunks=chunks, topic_index_path=module_topic_index_path(module_id_value))

    processed_at = datetime.now().isoformat(timespec="seconds")
    manifest = {
        "module_id": module_id_value,
        "files": [f.name for f in uploaded_files],
        "chunk_count": len(chunks),
        "last_processed": processed_at,
        "module_topics": topics,
        "cache_schema_version": CACHE_SCHEMA_VERSION,
    }
    save_json(manifest_path, manifest)

    return module_id_value, len(chunks), processed_at, topics


hero(
    "PrepPilot",
    "Your AI-powered personal study coach: focused quiz practice + realistic daily prep plan.",
)

api_key = (
    _safe_secret("GROQ_API_KEY_1")
    or _safe_secret("GROQ_API_KEY")
    or os.getenv("GROQ_API_KEY_1", "")
    or os.getenv("GROQ_API_KEY", "")
)
base_url = os.getenv("GROQ_BASE_URL", DEFAULT_GROQ_BASE_URL)
max_retries = int(os.getenv("MAX_RETRIES", str(DEFAULT_MAX_RETRIES)))
timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
groq_client = get_groq_client(api_key, base_url, max_retries, timeout_seconds) if api_key else None
selected_quiz_model = DEFAULT_QUIZ_MODEL
selected_plan_model = DEFAULT_PLAN_MODEL
retrieval_k = DEFAULT_RETRIEVAL_K

with st.sidebar:
    st.header("1) Upload Materials")
    uploaded_files = st.file_uploader(
        "Upload lecture PDFs or slides",
        type=["pdf", "ppt", "pptx"],
        accept_multiple_files=True,
    )

    st.header("2) Set Your Dates")
    today = st.date_input("Start date", value=date.today())
    exam_date = st.date_input("Exam date", value=date.today() + timedelta(days=14))

    st.header("3) Personal Study Profile")
    hours_per_day = st.slider("Hours you can study per day", 1, 6, DEFAULT_STUDY_HOURS_PER_DAY)
    preferred_window = st.selectbox("Preferred study window", ["Morning", "Afternoon", "Evening"], index=2)

    process_clicked = st.button("Start and Analyze My Materials", use_container_width=True, disabled=not uploaded_files)

if process_clicked:
    try:
        with st.spinner("Analyzing your module materials..."):
            module_id_value, chunk_count, processed_at, topics = _process_files(uploaded_files)
            st.session_state["module_id"] = module_id_value
            st.session_state["ingestion_ready"] = True
            st.session_state["chunk_count"] = chunk_count
            st.session_state["last_processed"] = processed_at
            st.session_state["module_topics"] = topics
            st.success("Your module is ready. You can now generate quiz sessions and a study plan.")
    except Exception as exc:
        st.session_state["ingestion_ready"] = False
        st.error(f"Processing failed: {exc}")

module_ready = st.session_state["ingestion_ready"]
days_remaining = (exam_date - today).days

status_strip(module_ready=module_ready, days_remaining=days_remaining, hours_per_day=hours_per_day)

allow_generation, block_reason = generation_allowed(
    ingestion_ready=module_ready,
    today=today,
    exam_date=exam_date,
    api_key=api_key,
)
if not allow_generation:
    st.info(block_reason)

current_chunks: list = []
current_overrides: dict[str, bool] = {}
excluded_items: list[dict] = []
allowed_ids: set[str] = set()

if module_ready and st.session_state.get("module_id"):
    current_chunks, current_overrides, excluded_items, allowed_ids = _load_chunk_bundle(st.session_state["module_id"])

with st.sidebar:
    if module_ready:
        st.divider()
        st.subheader("Study Personalization")
        st.session_state["student_topic_conf"] = _topic_confidence_input(st.session_state.get("module_topics", []))


student_topic_conf = st.session_state.get("student_topic_conf", [])
student_profile = {
    "hours_per_day": hours_per_day,
    "preferred_study_window": preferred_window,
    "topic_confidence": student_topic_conf,
}

live_quiz_tab, study_plan_tab = st.tabs(["Live Quiz", "Study Plan"])

with live_quiz_tab:
    section_intro(
        "Live Quiz",
        "Generate a fresh 15-question session with balanced coverage across your core exam topics.",
    )

    if not module_ready:
        empty_state(
            "Upload and process your module first",
            "Once your materials are analyzed, your quiz session will appear here.",
        )

    card_start()
    st.subheader("Quiz Session Setup")
    st.caption("Choose difficulty and create a new, grounded practice set.")

    if st.session_state.get("module_topics"):
        coverage_pills(st.session_state["module_topics"][:8], tone="brand")

    difficulty = st.selectbox(
        "Difficulty",
        options=["Easy", "Medium", "Hard"],
        index=["Easy", "Medium", "Hard"].index(DEFAULT_QUIZ_DIFFICULTY),
    )
    regenerate_quiz = st.toggle("Regenerate new questions", value=False)
    generate_quiz_clicked = st.button("Create My 15-Question Quiz", disabled=not allow_generation, use_container_width=True)
    card_end()

    if generate_quiz_clicked:
        status_box = st.empty()
        try:
            module_id_value = st.session_state["module_id"]
            vectorstore = get_vectorstore(module_id_value)
            context = retrieve_diverse_context(
                vectorstore=vectorstore,
                seed_query="exam preparation from core module concepts",
                difficulty=difficulty,
                k=retrieval_k,
                topic_index_path=module_topic_index_path(module_id_value),
                status_callback=lambda msg: status_box.info(msg),
                topics=st.session_state.get("module_topics", []),
                allowed_chunk_ids=allowed_ids,
            )
            if not context:
                raise ValueError("We couldn't gather enough exam-relevant context from your module.")

            key = cache_key(
                [
                    CACHE_SCHEMA_VERSION,
                    module_id_value,
                    "quiz",
                    difficulty,
                    selected_quiz_model,
                    str(retrieval_k),
                    overrides_hash(current_overrides),
                ]
            )
            cache_path = module_quiz_cache_path(module_id_value)

            cached = None if regenerate_quiz else get_cached(cache_path, key)
            if cached is not None:
                from exam_helper.models import QuizSet

                quiz_set = QuizSet.model_validate(cached)
                used_model = "cache"
            else:
                model_chain = _build_model_chain(selected_quiz_model, QUIZ_MODEL_FALLBACK)
                quiz_set, used_model = generate_quiz(
                    groq_client=groq_client,
                    context_chunks=context,
                    difficulty=difficulty,
                    model_chain=model_chain,
                    topics=st.session_state.get("module_topics", []),
                    status_callback=lambda msg: status_box.info(msg),
                )
                set_cached(cache_path, key, quiz_set.model_dump(mode="json"))

            st.session_state["quiz_set"] = quiz_set
            st.session_state["quiz_model_used"] = used_model
            st.session_state["quiz_score"] = None
            st.session_state["quiz_details"] = None
            status_box.empty()
        except Exception as exc:
            status_box.empty()
            st.error(f"Quiz generation failed: {exc}")

    quiz_set = st.session_state.get("quiz_set")
    if quiz_set:
        section_intro("Current Quiz", "Answer all questions, then submit to see detailed feedback.")
        card_start()
        if quiz_set.coverage_summary:
            st.markdown("#### Topic Coverage")
            coverage_pills(quiz_set.coverage_summary, tone="ok")
        card_end()

        for idx, question in enumerate(quiz_set.questions, start=1):
            card_start()
            st.markdown(f"### Q{idx}")
            st.markdown(f"**{question.question}**")
            coverage_pills([question.topic_tag], tone="brand")
            label_map = {
                f"A. {question.options['A']}": "A",
                f"B. {question.options['B']}": "B",
                f"C. {question.options['C']}": "C",
                f"D. {question.options['D']}": "D",
            }
            st.radio("Choose one", options=list(label_map.keys()), key=f"ans_{question.question_id}", index=None)

            valid_cits = _validate_citations(question.citations)
            if valid_cits:
                coverage_pills([f"{c['file']} p/s {c['page_or_slide']}" for c in valid_cits], tone="")
            else:
                evidence_warning("Insufficient module evidence for this item. Consider regenerating the quiz.")
            card_end()

        submit_quiz = st.button("Submit Quiz", use_container_width=True)
        if submit_quiz:
            answers: dict[str, str] = {}
            for question in quiz_set.questions:
                value = st.session_state.get(f"ans_{question.question_id}")
                if value:
                    answers[question.question_id] = value.split(".", 1)[0]

            score, details = score_quiz(quiz_set, answers)
            st.session_state["quiz_score"] = score
            st.session_state["quiz_details"] = details

    if st.session_state.get("quiz_score") is not None:
        section_intro("Quiz Results", "Review correctness, explanations, and supporting references.")
        st.success(f"Score: {st.session_state['quiz_score']} / 15")
        for detail in st.session_state.get("quiz_details", []):
            card_start()
            mark = "Correct" if detail["is_correct"] else "Incorrect"
            st.markdown(f"**{detail['question_id']} - {mark}**")
            st.caption(f"Topic: {detail.get('topic_tag', 'General')}")
            st.write(f"Your answer: {detail['user_answer']}")
            st.write(f"Correct answer: {detail['correct_option']}")
            st.markdown("**Detailed Explanation**")
            st.markdown(detail["explanation"])

            valid_cits = _validate_citations(detail["citations"])
            if valid_cits:
                coverage_pills([f"{c['file']} p/s {c['page_or_slide']}" for c in valid_cits])
            else:
                evidence_warning("Insufficient module evidence for this explanation.")
            card_end()

with study_plan_tab:
    section_intro(
        "Study Plan",
        "Build a realistic day-by-day plan tailored to your dates, confidence levels, and available time.",
    )

    if not module_ready:
        empty_state(
            "No study plan yet",
            "Upload and process your materials to generate your personalized plan.",
        )

    card_start()
    st.subheader("Plan Setup")
    st.caption("Generate a complete plan with priorities, daily schedule, and high-yield practice prompts.")
    st.write(f"Exam countdown: **{max(0, days_remaining)} day(s)**")
    regenerate_plan = st.toggle("Regenerate plan", value=False)
    generate_plan_clicked = st.button("Build My Study Plan", disabled=not allow_generation, use_container_width=True)
    card_end()

    if generate_plan_clicked:
        status_box = st.empty()
        try:
            module_id_value = st.session_state["module_id"]
            vectorstore = get_vectorstore(module_id_value)

            context = retrieve_diverse_context(
                vectorstore=vectorstore,
                seed_query="personalized exam study planning from core concepts",
                difficulty="Medium",
                k=retrieval_k,
                topic_index_path=module_topic_index_path(module_id_value),
                status_callback=lambda msg: status_box.info(msg),
                topics=st.session_state.get("module_topics", []),
                allowed_chunk_ids=allowed_ids,
            )
            if not context:
                raise ValueError("We couldn't find enough exam-focused material for a strong study plan.")

            key = cache_key(
                [
                    CACHE_SCHEMA_VERSION,
                    module_id_value,
                    "plan",
                    today.isoformat(),
                    exam_date.isoformat(),
                    selected_plan_model,
                    str(retrieval_k),
                    str(student_profile),
                    overrides_hash(current_overrides),
                ]
            )
            cache_path = module_plan_cache_path(module_id_value)

            cached = None if regenerate_plan else get_cached(cache_path, key)
            if cached is not None:
                from exam_helper.models import StudyPlan

                plan = StudyPlan.model_validate(cached)
                used_model = "cache"
            else:
                plan_model_chain = _build_model_chain(selected_plan_model, PLAN_MODEL_FALLBACK)
                plan, used_model = generate_study_plan(
                    groq_client=groq_client,
                    context_chunks=context,
                    today=today,
                    exam_date=exam_date,
                    model_chain=plan_model_chain,
                    student_profile=student_profile,
                    status_callback=lambda msg: status_box.info(msg),
                )
                set_cached(cache_path, key, plan.model_dump(mode="json"))

            st.session_state["study_plan"] = plan
            st.session_state["plan_model_used"] = used_model
            status_box.empty()
        except Exception as exc:
            status_box.empty()
            st.error(f"Study plan generation failed: {exc}")

    plan = st.session_state.get("study_plan")
    if plan:
        card_start()
        st.markdown("### Study Cadence Strategy")
        st.markdown(plan.cadence_recommendation)
        card_end()

        card_start()
        st.markdown("### Prioritized Topics")
        for idx, topic in enumerate(plan.prioritized_topics, start=1):
            detail = f"[{topic.priority}] {topic.rationale}"
            topic_row(f"{idx}. {topic.topic}", detail)
            valid_cits = _validate_citations(topic.citations)
            if valid_cits:
                coverage_pills([f"{c['file']} p/s {c['page_or_slide']}" for c in valid_cits])
            else:
                evidence_warning("Insufficient module evidence for this topic recommendation.")
        card_end()

        card_start()
        st.markdown("### Day-by-Day Schedule")
        show_full_schedule = st.toggle("Show full schedule", value=False, key="show_full_schedule")
        visible_schedule = plan.daily_schedule if show_full_schedule else plan.daily_schedule[:21]
        if not show_full_schedule and len(plan.daily_schedule) > len(visible_schedule):
            st.caption(f"Showing first {len(visible_schedule)} days for faster viewing. Turn on full schedule to see all days.")
        for day in visible_schedule:
            topic_row(
                day.date.isoformat(),
                f"Focus: {', '.join(day.topics)}\n\nMethod: {day.method}\nTimebox: {day.timebox}",
            )
        card_end()

        card_start()
        st.markdown("### How to Study")
        for item in plan.how_to_study:
            topic_row(item.tactic, item.tailored_guidance)
            valid_cits = _validate_citations(item.citations)
            if valid_cits:
                coverage_pills([f"{c['file']} p/s {c['page_or_slide']}" for c in valid_cits])
            else:
                evidence_warning("Insufficient module evidence for this tactic.")
        card_end()

        card_start()
        st.markdown("### Important Questions to Practice")
        for question in plan.important_questions:
            topic_row(f"[{question.question_type}] {question.topic}", question.prompt)
            valid_cits = _validate_citations(question.citations)
            if valid_cits:
                coverage_pills([f"{c['file']} p/s {c['page_or_slide']}" for c in valid_cits])
            else:
                evidence_warning("Insufficient module evidence for this practice prompt.")
        card_end()

        pdf_bytes = build_study_plan_pdf(plan)
        st.download_button(
            label="Download Study Plan (PDF)",
            data=pdf_bytes,
            file_name=f"study_plan_{today.isoformat()}_{exam_date.isoformat()}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
