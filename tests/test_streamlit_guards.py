from datetime import date

from exam_helper.utils.guards import generation_allowed


def test_streamlit_guards_not_ready():
    allowed, reason = generation_allowed(False, date(2026, 2, 23), date(2026, 2, 25), "key")
    assert not allowed
    assert "Process files" in reason


def test_streamlit_guards_bad_date():
    allowed, reason = generation_allowed(True, date(2026, 2, 23), date(2026, 2, 22), "key")
    assert not allowed
    assert "Exam date" in reason


def test_streamlit_guards_missing_key():
    allowed, reason = generation_allowed(True, date(2026, 2, 23), date(2026, 2, 25), "")
    assert not allowed
    assert "GROQ_API_KEY" in reason
