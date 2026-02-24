from exam_helper.services.quality_guard import normalize_candidate_pool


def test_quiz_no_admin_questions():
    data = {
        "candidate_questions": [
            {
                "question_id": "q1",
                "question": "What is Uniform Cost Search?",
                "topic_tag": "Search",
                "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
                "correct_option": "A",
                "explanation": "e",
                "citations": [{"file": "slides.pdf", "page_or_slide": 3, "snippet_reference": "ucs"}],
            }
        ]
    }
    normalized = normalize_candidate_pool(data, topics=["Search"])
    assert normalized
    assert "canvas" not in normalized[0]["question"].lower()
