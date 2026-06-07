from __future__ import annotations

from datetime import date

from exam_helper.utils.guards import generation_allowed


def test_generation_requires_processed_materials() -> None:
    allowed, reason = generation_allowed(
        ingestion_ready=False,
        today=date(2026, 6, 7),
        exam_date=date(2026, 6, 8),
        api_key="key",
    )

    assert allowed is False
    assert "Process files" in reason


def test_generation_blocks_past_exam_date() -> None:
    allowed, reason = generation_allowed(
        ingestion_ready=True,
        today=date(2026, 6, 8),
        exam_date=date(2026, 6, 7),
        api_key="key",
    )

    assert allowed is False
    assert "Exam date" in reason


def test_generation_allows_ready_state_with_key() -> None:
    allowed, reason = generation_allowed(
        ingestion_ready=True,
        today=date(2026, 6, 7),
        exam_date=date(2026, 6, 7),
        api_key="key",
    )

    assert allowed is True
    assert reason == ""
