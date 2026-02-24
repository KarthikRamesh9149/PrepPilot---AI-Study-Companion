from __future__ import annotations

from datetime import date


def generation_allowed(ingestion_ready: bool, today: date, exam_date: date, api_key: str) -> tuple[bool, str]:
    if not ingestion_ready:
        return False, "Process files before generating content."
    if exam_date < today:
        return False, "Exam date must be today or later."
    if not api_key.strip():
        return False, "Set GROQ_API_KEY to generate quiz or study plans."
    return True, ""
