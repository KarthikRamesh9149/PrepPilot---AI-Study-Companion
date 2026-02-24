from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable

from pydantic import ValidationError

from exam_helper.config import DEFAULT_STUDY_HOURS_PER_DAY
from exam_helper.models import StudyPlan
from exam_helper.retrieval.retriever import context_as_prompt_text
from exam_helper.services.topic_service import profile_topic_weights

ADMIN_TOPIC_TERMS = {
    "canvas",
    "academic integrity",
    "plagiarism",
    "discussion board",
    "submission",
    "attendance",
    "deadline policy",
}


def _build_plan_prompt(
    context_chunks: list[dict],
    today: date,
    exam_date: date,
    student_profile: dict[str, Any],
) -> tuple[str, str]:
    context_text = context_as_prompt_text(context_chunks)
    days_remaining = (exam_date - today).days

    system_prompt = (
        "You are a practical AI study coach for students. "
        "Use only module evidence. Keep plan specific, realistic, and exam-oriented. "
        "Return JSON only."
    )

    topic_conf = student_profile.get("topic_confidence", [])

    user_prompt = f"""
Create a complete personalized study plan JSON.

Dates:
- today: {today.isoformat()}
- exam_date: {exam_date.isoformat()}
- days_remaining: {days_remaining}

Student profile:
- hours_per_day: {student_profile.get('hours_per_day', DEFAULT_STUDY_HOURS_PER_DAY)}
- preferred_study_window: {student_profile.get('preferred_study_window', 'Evening')}
- topic_confidence: {topic_conf}

Required JSON keys:
- title
- today
- exam_date
- countdown_days
- cadence_recommendation
- prioritized_topics: list of {{topic, priority(High/Medium/Low), rationale, citations[]}}
- daily_schedule: include EVERY date from today to exam_date inclusive.
  each: {{date, topics[], method, timebox}}
- how_to_study: list of {{tactic, tailored_guidance, citations[]}}
- important_questions: list of {{topic, question_type(MCQ/ShortAnswer/Conceptual/Application), prompt, citations[]}}

Rules:
- Do not include admin/logistics topics (Canvas, policy, submission instructions).
- Keep recommendations exam-focused and actionable.
- Use citations tied to context evidence.
- If evidence is insufficient for a claim, avoid fabricated detail and keep wording cautious.
- Be detailed and structured:
  - `cadence_recommendation`: 4-6 sentences with weekly pacing + revision checkpoints.
  - each `prioritized_topics[].rationale`: 3-5 sentences with what to master, why exam-relevant, and common mistakes.
  - each `daily_schedule[].method`: a step-by-step plan in one string (e.g., "Step 1 ...; Step 2 ...; Step 3 ...; Step 4 ...").
  - each `timebox`: specific split (e.g., "30m concept review + 45m problem solving + 30m recall + 15m error log").
  - each `how_to_study[].tailored_guidance`: 4-6 sentences with concrete examples tied to module topics.
  - each `important_questions[].prompt`: detailed practice prompt with expected depth.

Context:
{context_text}
""".strip()

    return system_prompt, user_prompt


def _repair_prompt(original_json: dict, validation_error: Exception, context_chunks: list[dict], today: date, exam_date: date) -> tuple[str, str]:
    system_prompt = "Repair invalid study plan JSON. Keep it grounded, student-friendly, and exam-focused. JSON only."
    user_prompt = f"""
Validation error:
{validation_error}

Repair this JSON:
{original_json}

Dates must remain:
- today: {today.isoformat()}
- exam_date: {exam_date.isoformat()}

Context:
{context_as_prompt_text(context_chunks)}
""".strip()
    return system_prompt, user_prompt


def _normalize_citations(value: Any) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            file_name = str(item.get("file", "")).strip()
            snippet = str(item.get("snippet_reference", "")).strip()
            page_or_slide = int(item.get("page_or_slide", 1) or 1)
            if not file_name:
                continue
            citations.append(
                {
                    "file": file_name,
                    "page_or_slide": max(1, page_or_slide),
                    "snippet_reference": snippet or "Module reference",
                }
            )
    return citations


def _clean_text(value: Any, fallback: str, min_chars: int = 0) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        return fallback
    # suppress raw fallback clutter
    if "not found in your module" in text.lower():
        return fallback
    if min_chars and len(text) < min_chars:
        return fallback
    return text


def _is_admin_meta_text(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in ADMIN_TOPIC_TERMS)


def _priority_from_topic(topic: str, topic_weights: dict[str, float], idx: int) -> str:
    weight = topic_weights.get(topic, 1.0)
    base = "High" if idx < 2 else ("Medium" if idx < 5 else "Low")
    if weight > 1.15 and base != "High":
        return "High"
    if weight < 0.9 and base == "High":
        return "Medium"
    return base


def _default_detailed_method(hours: int, window: str, topic_hint: str) -> str:
    return (
        f"Step 1 ({max(20, hours * 10)} min): Review core theory for {topic_hint} and write a one-page summary; "
        f"Step 2 ({max(30, hours * 20)} min): Solve practice questions from easy to medium; "
        f"Step 3 ({max(20, hours * 10)} min): Active recall without notes and explain answers aloud; "
        f"Step 4 ({max(10, hours * 5)} min): Log mistakes, mark weak points, and plan next-session fixes during your {window.lower()} block."
    )


def _default_timebox(hours: int, window: str) -> str:
    total = max(60, hours * 60)
    part1 = int(total * 0.25)
    part2 = int(total * 0.4)
    part3 = int(total * 0.25)
    part4 = total - part1 - part2 - part3
    return (
        f"{hours} hours total ({window}): {part1}m concept review + {part2}m worked problems + "
        f"{part3}m active recall + {part4}m error-log revision"
    )


def _normalize_study_plan_payload(
    payload: Any,
    today: date,
    exam_date: date,
    student_profile: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {}

    topic_weights = profile_topic_weights(student_profile.get("topic_confidence", []))

    prioritized_topics_raw = payload.get("prioritized_topics", [])
    if not isinstance(prioritized_topics_raw, list):
        prioritized_topics_raw = []

    prioritized_topics: list[dict[str, Any]] = []
    for idx, row in enumerate(prioritized_topics_raw):
        if not isinstance(row, dict):
            continue
        topic = _clean_text(row.get("topic"), f"Core Topic {idx+1}")
        if _is_admin_meta_text(topic):
            continue
        pr = row.get("priority")
        if pr not in {"High", "Medium", "Low"}:
            pr = _priority_from_topic(topic, topic_weights, idx)
        citations = _normalize_citations(row.get("citations"))
        if not citations:
            continue
        prioritized_topics.append(
            {
                "topic": topic,
                "priority": pr,
                "rationale": _clean_text(
                    row.get("rationale"),
                    (
                        "This topic appears repeatedly across your module and underpins several downstream concepts. "
                        "Mastering definitions, assumptions, and common problem patterns here will improve both speed and accuracy in the exam. "
                        "Prioritize concept clarity first, then move to application-style questions and error correction."
                    ),
                    min_chars=140,
                ),
                "citations": citations,
            }
        )

    if not prioritized_topics:
        prioritized_topics = [
            {
                "topic": "Core module concepts",
                "priority": "High",
                "rationale": (
                    "Focus on the most repeated technical concepts in your module and build strong fundamentals before advanced variations. "
                    "Spend early sessions on definitions and problem setup, then shift to mixed practice and timed attempts. "
                    "Track recurring mistakes to prevent repeat errors in exam conditions."
                ),
                "citations": [{"file": "Module content", "page_or_slide": 1, "snippet_reference": "Core concept references"}],
            }
        ]

    fallback_topic = prioritized_topics[0]["topic"]

    schedule_raw = payload.get("daily_schedule", [])
    if not isinstance(schedule_raw, list):
        schedule_raw = []

    daily_schedule: list[dict[str, Any]] = []
    expected_dates = []
    d = today
    while d <= exam_date:
        expected_dates.append(d)
        d += timedelta(days=1)

    raw_by_date: dict[str, dict] = {}
    for item in schedule_raw:
        if isinstance(item, dict):
            raw_by_date[str(item.get("date", ""))] = item

    hours = int(student_profile.get("hours_per_day", DEFAULT_STUDY_HOURS_PER_DAY))
    window = str(student_profile.get("preferred_study_window", "Evening"))

    for dt in expected_dates:
        key = dt.isoformat()
        row = raw_by_date.get(key, {})
        topics = row.get("topics", [fallback_topic])
        if not isinstance(topics, list) or not topics:
            topics = [fallback_topic]
        daily_schedule.append(
            {
                "date": dt,
                "topics": [str(t) for t in topics],
                "method": _clean_text(
                    row.get("method"),
                    _default_detailed_method(hours, window, str(topics[0])),
                    min_chars=120,
                ),
                "timebox": _clean_text(
                    row.get("timebox"),
                    _default_timebox(hours, window),
                    min_chars=45,
                ),
            }
        )

    how_raw = payload.get("how_to_study", [])
    if not isinstance(how_raw, list):
        how_raw = []
    how_to_study: list[dict[str, Any]] = []
    for item in how_raw:
        if not isinstance(item, dict):
            continue
        citations = _normalize_citations(item.get("citations"))
        if not citations:
            continue
        how_to_study.append(
            {
                "tactic": _clean_text(item.get("tactic"), "Active recall"),
                "tailored_guidance": _clean_text(
                    item.get("tailored_guidance"),
                    (
                        "Use active recall after every study block: close your notes and write the key definitions, assumptions, and solution steps from memory. "
                        "Then compare with the module content and highlight gaps. Convert each weak area into two short self-test questions and revisit them within 24 hours. "
                        "End each session by correcting one mistake pattern so your next practice set improves measurably."
                    ),
                    min_chars=170,
                ),
                "citations": citations,
            }
        )

    if not how_to_study:
        how_to_study = [
            {
                "tactic": "Active recall",
                "tailored_guidance": (
                    "Turn each core topic into self-test questions and review mistakes daily. "
                    "After reading a concept, write an explanation from memory and solve one related problem without notes. "
                    "Use a mistake log to track recurring errors and schedule a focused correction block the next day."
                ),
                "citations": prioritized_topics[0]["citations"],
            }
        ]

    important_raw = payload.get("important_questions", [])
    if isinstance(important_raw, dict):
        tmp = []
        for topic, val in important_raw.items():
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        item.setdefault("topic", topic)
                        tmp.append(item)
            elif isinstance(val, dict):
                val.setdefault("topic", topic)
                tmp.append(val)
        important_raw = tmp

    if not isinstance(important_raw, list):
        important_raw = []

    important_questions: list[dict[str, Any]] = []
    for item in important_raw:
        if not isinstance(item, dict):
            continue
        citations = _normalize_citations(item.get("citations"))
        if not citations:
            continue
        qtype = str(item.get("question_type", "Conceptual"))
        if qtype not in {"MCQ", "ShortAnswer", "Conceptual", "Application"}:
            qtype = "Conceptual"
        important_questions.append(
            {
                "topic": _clean_text(item.get("topic"), fallback_topic),
                "question_type": qtype,
                "prompt": _clean_text(
                    item.get("prompt", item.get("question")),
                    (
                        "Explain the concept clearly, state assumptions, compare with one alternative method, "
                        "and solve a short applied example step by step."
                    ),
                    min_chars=90,
                ),
                "citations": citations,
            }
        )
    important_questions = [
        q for q in important_questions if not _is_admin_meta_text(q["topic"]) and not _is_admin_meta_text(q["prompt"])
    ]

    if not important_questions:
        important_questions = [
            {
                "topic": fallback_topic,
                "question_type": "Conceptual",
                "prompt": (
                    "Explain the key idea, list assumptions, show how it differs from a similar method, "
                    "and walk through one practical use case step by step."
                ),
                "citations": prioritized_topics[0]["citations"],
            }
        ]

    # Evidence quality scoring.
    def _quality(section_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        total = max(1, len(rows))
        grounded = 0
        for r in rows:
            if r.get("citations"):
                grounded += 1
        score = grounded / total
        return {
            "section": section_name,
            "score": round(score, 3),
            "status": "ok" if score >= 0.7 else "weak",
            "note": "Grounding confidence is high." if score >= 0.7 else "Some recommendations are weakly grounded.",
        }

    evidence_quality = [
        _quality("prioritized_topics", prioritized_topics),
        _quality("how_to_study", how_to_study),
        _quality("important_questions", important_questions),
    ]

    return {
        "title": _clean_text(payload.get("title"), "Your Personalized Exam Study Plan"),
        "today": today,
        "exam_date": exam_date,
        "countdown_days": (exam_date - today).days,
        "cadence_recommendation": _clean_text(
            payload.get("cadence_recommendation"),
            (
                f"Study {hours} hours/day in your {window.lower()} window, and follow a repeating cycle of concept build-up, guided practice, and mistake-driven revision. "
                "Use the first half of your schedule to build depth in high-priority topics and the second half to increase mixed-question practice under light time pressure. "
                "Reserve every third day for cumulative revision so older topics are not forgotten. "
                "In the final week, reduce new content and focus on weak areas, error-log review, and exam-style question sets."
            ),
            min_chars=180,
        ),
        "prioritized_topics": prioritized_topics,
        "daily_schedule": daily_schedule,
        "how_to_study": how_to_study,
        "important_questions": important_questions,
        "evidence_quality": evidence_quality,
    }


def generate_study_plan(
    groq_client,
    context_chunks: list[dict],
    today: date,
    exam_date: date,
    model_chain: list[str],
    student_profile: dict[str, Any],
    status_callback: Callable[[str], None] | None = None,
) -> tuple[StudyPlan, str]:
    system_prompt, user_prompt = _build_plan_prompt(
        context_chunks=context_chunks,
        today=today,
        exam_date=exam_date,
        student_profile=student_profile,
    )
    raw_json, used_model = groq_client.chat_json_with_fallback(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model_chain=model_chain,
        temperature=0.2,
        max_tokens=9000,
        status_callback=status_callback,
    )

    try:
        normalized = _normalize_study_plan_payload(raw_json, today=today, exam_date=exam_date, student_profile=student_profile)
        plan = StudyPlan.model_validate(normalized)
    except ValidationError as exc:
        repair_system, repair_user = _repair_prompt(raw_json, exc, context_chunks, today, exam_date)
        repaired_json, repaired_model = groq_client.chat_json_with_fallback(
            system_prompt=repair_system,
            user_prompt=repair_user,
            model_chain=model_chain,
            temperature=0.0,
            max_tokens=7000,
            status_callback=status_callback,
        )
        normalized = _normalize_study_plan_payload(repaired_json, today=today, exam_date=exam_date, student_profile=student_profile)
        plan = StudyPlan.model_validate(normalized)
        used_model = repaired_model

    return plan, used_model
