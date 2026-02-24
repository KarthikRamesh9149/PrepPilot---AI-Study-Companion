from datetime import date

from exam_helper.services.study_plan_service import _normalize_study_plan_payload


def test_student_profile_schedule():
    normalized = _normalize_study_plan_payload(
        {
            "prioritized_topics": [
                {
                    "topic": "Search",
                    "priority": "High",
                    "rationale": "Important",
                    "citations": [{"file": "slides.pdf", "page_or_slide": 1, "snippet_reference": "s"}],
                }
            ]
        },
        today=date(2026, 2, 24),
        exam_date=date(2026, 2, 26),
        student_profile={"hours_per_day": 3, "preferred_study_window": "Morning", "topic_confidence": []},
    )
    assert len(normalized["daily_schedule"]) == 3
    assert "3 hours" in normalized["daily_schedule"][0]["timebox"]
    assert "Morning" in normalized["daily_schedule"][0]["timebox"]
