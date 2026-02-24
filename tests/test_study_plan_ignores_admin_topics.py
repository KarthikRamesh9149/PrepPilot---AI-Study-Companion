from datetime import date

from exam_helper.services.study_plan_service import _normalize_study_plan_payload


def test_study_plan_ignores_admin_topics():
    payload = {
        "prioritized_topics": [
            {
                "topic": "Canvas Discussion Board",
                "priority": "High",
                "rationale": "admin",
                "citations": [{"file": "slides.pdf", "page_or_slide": 1, "snippet_reference": "x"}],
            },
            {
                "topic": "Search Algorithms",
                "priority": "High",
                "rationale": "exam",
                "citations": [{"file": "slides.pdf", "page_or_slide": 3, "snippet_reference": "y"}],
            },
        ]
    }
    normalized = _normalize_study_plan_payload(
        payload,
        today=date(2026, 2, 24),
        exam_date=date(2026, 2, 27),
        student_profile={"hours_per_day": 2, "preferred_study_window": "Evening", "topic_confidence": []},
    )
    topics = [t["topic"].lower() for t in normalized["prioritized_topics"]]
    assert all("canvas" not in t for t in topics)
