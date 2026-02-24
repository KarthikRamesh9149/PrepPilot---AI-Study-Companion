from exam_helper.services.quality_guard import enforce_topic_quota


def _make(topic: str, idx: int):
    return {
        "question_id": f"q{topic}{idx}",
        "topic_tag": topic,
        "question": f"Q {topic} {idx}",
        "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
        "correct_option": "A",
        "explanation": "exp",
        "citations": [{"file": "m.pdf", "page_or_slide": 1, "snippet_reference": "s"}],
    }


def test_quiz_topic_quota():
    topics = ["Search", "Logic", "Agents"]
    pool = [_make("Search", i) for i in range(8)] + [_make("Logic", i) for i in range(8)] + [_make("Agents", i) for i in range(8)]
    selected = enforce_topic_quota(pool, topics=topics, final_count=15)
    covered = {q["topic_tag"] for q in selected}
    assert len(selected) == 15
    assert "Search" in covered and "Logic" in covered and "Agents" in covered
