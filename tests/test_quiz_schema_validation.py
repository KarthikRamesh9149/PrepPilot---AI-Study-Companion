import pytest

from exam_helper.models import QuizSet


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


def test_quiz_schema_validation_rejects_non_15():
    payload = {"difficulty": "Medium", "questions": [_quiz_question(i) for i in range(14)]}
    with pytest.raises(Exception):
        QuizSet.model_validate(payload)


def test_quiz_schema_validation_rejects_bad_options():
    payload = {"difficulty": "Medium", "questions": [_quiz_question(i) for i in range(15)]}
    payload["questions"][0]["options"] = {"A": "a", "B": "b", "C": "c"}
    with pytest.raises(Exception):
        QuizSet.model_validate(payload)
