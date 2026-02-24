from exam_helper.services.quality_guard import deduplicate_questions


def _q(text: str):
    return {
        "question_id": text[:5],
        "topic_tag": "Search",
        "question": text,
        "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
        "correct_option": "A",
        "explanation": "exp",
        "citations": [{"file": "m.pdf", "page_or_slide": 1, "snippet_reference": "s"}],
    }


def test_quiz_deduplication():
    candidates = [
        _q("What is Uniform Cost Search?"),
        _q("What is uniform-cost search?"),
        _q("Explain A* algorithm."),
    ]
    deduped = deduplicate_questions(candidates)
    stems = [x["question"].lower() for x in deduped]
    assert len(deduped) == 2
    assert any("uniform cost" in s for s in stems)
    assert any("a*" in s for s in stems)
