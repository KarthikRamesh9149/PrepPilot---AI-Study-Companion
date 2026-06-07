from __future__ import annotations

import pytest
from pydantic import ValidationError

from exam_helper.models import QuizQuestion, QuizSet


def _question(idx: int) -> QuizQuestion:
    return QuizQuestion(
        question_id=f"q{idx}",
        topic_tag="Search",
        question=f"What is the best answer for item {idx}?",
        options={"A": "Alpha", "B": "Beta", "C": "Gamma", "D": "Delta"},
        correct_option="A",
        explanation="Alpha is correct because it matches the cited concept.",
        citations=[{"file": "lecture.pdf", "page_or_slide": 1, "snippet_reference": "Relevant content"}],
    )


def test_quiz_set_requires_exactly_15_questions() -> None:
    quiz = QuizSet(difficulty="Medium", questions=[_question(idx) for idx in range(1, 16)])

    assert len(quiz.questions) == 15


def test_quiz_set_rejects_short_question_sets() -> None:
    with pytest.raises(ValidationError, match="exactly 15"):
        QuizSet(difficulty="Medium", questions=[_question(idx) for idx in range(1, 15)])
