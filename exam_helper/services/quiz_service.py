from __future__ import annotations

from typing import Callable

from pydantic import ValidationError

from exam_helper.models import QuizSet
from exam_helper.retrieval.retriever import context_as_prompt_text
from exam_helper.services.quality_guard import (
    coverage_summary,
    deduplicate_questions,
    enforce_topic_quota,
    normalize_candidate_pool,
)

ADMIN_META_TERMS = {
    "canvas",
    "academic integrity",
    "integrity expected",
    "submission",
    "attendance",
    "discussion",
    "thank you",
    "session date details",
}


def _difficulty_rules(difficulty: str) -> str:
    if difficulty == "Easy":
        return "Easy: direct recall and definition from explicit module facts."
    if difficulty == "Hard":
        return "Hard: multi-step or scenario-based questions with tricky but fair distractors, still grounded in retrieved evidence."
    return "Medium: application and comparison questions with plausible distractors and concept linking."


def _is_admin_meta_text(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in ADMIN_META_TERMS)


def _clean_chunk_text_for_prompt(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    kept: list[str] = []
    for line in lines:
        lower = line.lower()
        if _is_admin_meta_text(lower):
            continue
        if "http://" in lower or "https://" in lower:
            continue
        alpha = sum(ch.isalpha() for ch in line)
        digits = sum(ch.isdigit() for ch in line)
        if alpha < 8:
            continue
        if digits > alpha:
            continue
        if len(line.split()) < 3:
            continue
        kept.append(line)
        if len(kept) >= 7:
            break
    return "\n".join(kept).strip()


def _filter_context_for_quiz(context_chunks: list[dict]) -> list[dict]:
    filtered: list[dict] = []
    for chunk in context_chunks:
        text = str(chunk.get("text", ""))
        snippet = str(chunk.get("snippet_reference", ""))
        combined = f"{text} {snippet}".strip()
        if len(combined) < 80:
            continue
        if _is_admin_meta_text(combined):
            continue
        cleaned_text = _clean_chunk_text_for_prompt(text)
        if len(cleaned_text) < 80:
            continue
        cleaned_chunk = dict(chunk)
        cleaned_chunk["text"] = cleaned_text
        cleaned_chunk["snippet_reference"] = cleaned_text.splitlines()[0][:140]
        filtered.append(cleaned_chunk)
    return filtered or context_chunks


def _build_quiz_prompt(context_chunks: list[dict], difficulty: str, topics: list[str], candidate_count: int = 18) -> tuple[str, str]:
    context_text = context_as_prompt_text(context_chunks)
    topics_text = ", ".join(topics[:8]) if topics else "General module concepts"

    system_prompt = (
        "You are an exam coach generating grounded MCQs from module evidence. "
        "Return JSON only. Use only provided context. Do not repeat question stems. "
        "Every question must include valid citations to provided material."
    )

    user_prompt = f"""
Generate candidate MCQs for a student quiz.

Requirements:
- Return a JSON object with keys: difficulty, candidate_questions.
- candidate_questions must contain exactly {candidate_count} items.
- Each item fields:
  - question_id
  - topic_tag (must match one of the suggested topics where possible)
  - question
  - options (object with keys A,B,C,D)
  - correct_option (A/B/C/D)
  - explanation (detailed, at least 4-6 sentences, include: concept reasoning, why correct option is right, why other options are wrong, and one exam tip)
  - citations (non-empty list of {{file, page_or_slide, snippet_reference}})
- Do NOT repeat or paraphrase near-identical question stems.
- Keep the set diverse across these topics: {topics_text}
- Difficulty policy: {_difficulty_rules(difficulty)}
- Avoid admin/logistics content (Canvas, integrity policy, schedules, thank-you slides).
- Do not output meta-template questions such as "Which statement is best supported by this module excerpt...".
- Keep language clear and student-friendly; no placeholders or generic filler.

Context:
{context_text}
""".strip()

    return system_prompt, user_prompt


def _build_refill_prompt(
    context_chunks: list[dict],
    difficulty: str,
    topics: list[str],
    missing_count: int,
    banned_stems: list[str],
) -> tuple[str, str]:
    system_prompt = "Generate additional grounded MCQ candidates only. JSON only."
    user_prompt = f"""
Generate exactly {missing_count} additional candidate questions.

Rules:
- Return JSON with key candidate_questions only.
- Do not duplicate or paraphrase these stems: {banned_stems[:15]}
- Cover these topics if possible: {topics[:8]}
- Difficulty: {difficulty}
- Avoid admin/logistics content.
- Explanations must be detailed (4-6 sentences) and include why wrong options are wrong.
- Include citations for each question.

Context:
{context_as_prompt_text(context_chunks)}
""".strip()
    return system_prompt, user_prompt


def _finalize_quiz_payload(
    raw_json: dict,
    difficulty: str,
    topics: list[str],
) -> dict:
    candidates = normalize_candidate_pool(raw_json, topics=topics)
    unique = deduplicate_questions(candidates)
    selected = enforce_topic_quota(unique, topics=topics, final_count=15)

    return {
        "difficulty": difficulty,
        "coverage_summary": coverage_summary(selected),
        "questions": selected,
    }


def _generate_candidates_once(
    groq_client,
    context_chunks: list[dict],
    difficulty: str,
    model_chain: list[str],
    topics: list[str],
    candidate_count: int,
    max_tokens: int,
    status_callback: Callable[[str], None] | None = None,
) -> tuple[dict, str]:
    system_prompt, user_prompt = _build_quiz_prompt(
        context_chunks=context_chunks,
        difficulty=difficulty,
        topics=topics,
        candidate_count=candidate_count,
    )
    return groq_client.chat_json_with_fallback(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model_chain=model_chain,
        temperature=0.15,
        max_tokens=max_tokens,
        status_callback=status_callback,
    )


def generate_quiz(
    groq_client,
    context_chunks: list[dict],
    difficulty: str,
    model_chain: list[str],
    topics: list[str],
    status_callback: Callable[[str], None] | None = None,
) -> tuple[QuizSet, str]:
    filtered_context = _filter_context_for_quiz(context_chunks)
    last_error: Exception | None = None

    for candidate_count, max_tokens in [(18, 7000), (16, 6200), (15, 5600)]:
        try:
            raw_json, used_model = _generate_candidates_once(
                groq_client=groq_client,
                context_chunks=filtered_context,
                difficulty=difficulty,
                model_chain=model_chain,
                topics=topics,
                candidate_count=candidate_count,
                max_tokens=max_tokens,
                status_callback=status_callback,
            )
            payload = _finalize_quiz_payload(raw_json=raw_json, difficulty=difficulty, topics=topics)
            if len(payload["questions"]) >= 15:
                return QuizSet.model_validate(payload), used_model
        except Exception as exc:  # pragma: no cover - runtime transport failures
            last_error = exc

    # Refill pass for any missing questions after filtering.
    try:
        raw_json, used_model = _generate_candidates_once(
            groq_client=groq_client,
            context_chunks=filtered_context,
            difficulty=difficulty,
            model_chain=model_chain,
            topics=topics,
            candidate_count=15,
            max_tokens=5200,
            status_callback=status_callback,
        )
        payload = _finalize_quiz_payload(raw_json=raw_json, difficulty=difficulty, topics=topics)
    except Exception as exc:  # pragma: no cover - runtime transport failures
        last_error = exc
        payload = {"difficulty": difficulty, "questions": [], "coverage_summary": []}
        used_model = model_chain[0] if model_chain else "unknown"

    if len(payload["questions"]) < 15:
        missing = 15 - len(payload["questions"])
        banned = [q["question"] for q in payload["questions"]]
        refill_system, refill_user = _build_refill_prompt(
            context_chunks=filtered_context,
            difficulty=difficulty,
            topics=topics,
            missing_count=missing + 12,
            banned_stems=banned,
        )
        refill_json, refill_model = groq_client.chat_json_with_fallback(
            system_prompt=refill_system,
            user_prompt=refill_user,
            model_chain=model_chain,
            temperature=0.1,
            max_tokens=4200,
            status_callback=status_callback,
        )
        used_model = refill_model
        merged = {
            "candidate_questions": payload["questions"] + normalize_candidate_pool(refill_json, topics=topics)
        }
        payload = _finalize_quiz_payload(raw_json=merged, difficulty=difficulty, topics=topics)

    if len(payload["questions"]) < 15 and len(model_chain) > 1:
        raw_json, used_model = _generate_candidates_once(
            groq_client=groq_client,
            context_chunks=filtered_context,
            difficulty=difficulty,
            model_chain=list(reversed(model_chain)),
            topics=topics,
            candidate_count=22,
            max_tokens=7000,
            status_callback=status_callback,
        )
        payload = _finalize_quiz_payload(raw_json=raw_json, difficulty=difficulty, topics=topics)

    if len(payload["questions"]) < 15:
        raise ValueError(
            "Could not generate 15 high-quality grounded questions. Please click regenerate."
        ) from last_error

    try:
        return QuizSet.model_validate(payload), used_model
    except ValidationError as exc:
        repair_system = "Repair quiz JSON to valid schema exactly 15 grounded questions."
        repair_user = f"""
Validation error:
{exc}

Fix this JSON and return valid JSON with 15 non-duplicate questions:
{payload}
""".strip()
        repaired_json, repaired_model = groq_client.chat_json_with_fallback(
            system_prompt=repair_system,
            user_prompt=repair_user,
            model_chain=model_chain,
            temperature=0.0,
            max_tokens=5200,
            status_callback=status_callback,
        )
        repaired_payload = _finalize_quiz_payload(raw_json=repaired_json, difficulty=difficulty, topics=topics)
        if len(repaired_payload.get("questions", [])) < 15:
            raise ValueError("Quiz response remained low quality after repair. Please regenerate.")
        return QuizSet.model_validate(repaired_payload), repaired_model


def score_quiz(quiz: QuizSet, answers: dict[str, str]) -> tuple[int, list[dict]]:
    details: list[dict] = []
    score = 0

    for question in quiz.questions:
        user_answer = answers.get(question.question_id)
        is_correct = user_answer == question.correct_option
        if is_correct:
            score += 1
        details.append(
            {
                "question_id": question.question_id,
                "topic_tag": question.topic_tag,
                "user_answer": user_answer,
                "correct_option": question.correct_option,
                "is_correct": is_correct,
                "explanation": question.explanation,
                "citations": [citation.model_dump() for citation in question.citations],
            }
        )

    return score, details
