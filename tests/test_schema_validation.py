from datetime import date

import pytest

from exam_helper.models import QuizSet, StudyPlan


def _citation():
    return {"file": "module.pdf", "page_or_slide": 2, "snippet_reference": "snippet"}


def _quiz_question(i: int):
    return {
        "question_id": f"q{i}",
        "question": f"Question {i}",
        "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
        "correct_option": "A",
        "explanation": "Because grounded.",
        "citations": [_citation()],
    }


def test_quiz_schema_validation_accepts_exact_15():
    payload = {"difficulty": "Medium", "questions": [_quiz_question(i) for i in range(15)]}
    parsed = QuizSet.model_validate(payload)
    assert len(parsed.questions) == 15


def test_quiz_schema_validation_rejects_non_15():
    payload = {"difficulty": "Medium", "questions": [_quiz_question(i) for i in range(14)]}
    with pytest.raises(Exception):
        QuizSet.model_validate(payload)


def test_quiz_schema_validation_rejects_bad_options():
    payload = {"difficulty": "Medium", "questions": [_quiz_question(i) for i in range(15)]}
    payload["questions"][0]["options"] = {"A": "a", "B": "b", "C": "c"}
    with pytest.raises(Exception):
        QuizSet.model_validate(payload)


def test_study_plan_schema_validation_rejects_missing_citations():
    payload = {
        "title": "Plan",
        "today": date(2026, 2, 23),
        "exam_date": date(2026, 2, 28),
        "countdown_days": 5,
        "cadence_recommendation": "2 hours/day",
        "prioritized_topics": [{"topic": "A", "priority": "High", "rationale": "Important", "citations": []}],
        "daily_schedule": [{"date": date(2026, 2, 23), "topics": ["A"], "method": "Read -> summarize -> quiz -> review mistakes", "timebox": "2 hours"}],
        "how_to_study": [{"tactic": "Active recall", "tailored_guidance": "Use cards", "citations": [_citation()]}],
        "important_questions": [{"topic": "A", "question_type": "MCQ", "prompt": "What is A?", "citations": [_citation()]}],
    }
    with pytest.raises(Exception):
        StudyPlan.model_validate(payload)
