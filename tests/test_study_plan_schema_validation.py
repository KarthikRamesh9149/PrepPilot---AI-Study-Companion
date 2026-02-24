from datetime import date

import pytest

from exam_helper.models import StudyPlan


def _citation():
    return {"file": "module.pdf", "page_or_slide": 2, "snippet_reference": "snippet"}


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
