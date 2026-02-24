from datetime import date

from exam_helper.services.study_plan_service import _normalize_study_plan_payload


def test_study_plan_evidence_quality():
    payload = {
        "title": "Plan",
        "prioritized_topics": [
            {
                "topic": "Search",
                "priority": "High",
                "rationale": "Important",
                "citations": [{"file": "slides.pdf", "page_or_slide": 3, "snippet_reference": "ucs"}],
            }
        ],
        "daily_schedule": [],
        "how_to_study": [
            {
                "tactic": "Active recall",
                "tailored_guidance": "Do recall",
                "citations": [{"file": "slides.pdf", "page_or_slide": 4, "snippet_reference": "recall"}],
            }
        ],
        "important_questions": [
            {
                "topic": "Search",
                "question_type": "MCQ",
                "prompt": "What is UCS?",
                "citations": [{"file": "slides.pdf", "page_or_slide": 5, "snippet_reference": "ucs"}],
            }
        ],
    }

    normalized = _normalize_study_plan_payload(
        payload,
        today=date(2026, 2, 24),
        exam_date=date(2026, 2, 28),
        student_profile={"hours_per_day": 2, "preferred_study_window": "Evening", "topic_confidence": []},
    )
    assert "evidence_quality" in normalized
    assert len(normalized["evidence_quality"]) >= 3
    assert all(item["status"] in {"ok", "weak"} for item in normalized["evidence_quality"])
