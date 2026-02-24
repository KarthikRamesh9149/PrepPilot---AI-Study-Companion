from datetime import date
from io import BytesIO

from pypdf import PdfReader

from exam_helper.models import StudyPlan
from exam_helper.services.pdf_export import build_study_plan_pdf


def _citation():
    return {"file": "module.pdf", "page_or_slide": 2, "snippet_reference": "snippet"}


def test_pdf_export_contains_sections():
    payload = {
        "title": "Study Plan",
        "today": date(2026, 2, 23),
        "exam_date": date(2026, 2, 25),
        "countdown_days": 2,
        "cadence_recommendation": "2 hours/day",
        "prioritized_topics": [{"topic": "Topic A", "priority": "High", "rationale": "Dense", "citations": [_citation()]}],
        "daily_schedule": [{"date": date(2026, 2, 23), "topics": ["Topic A"], "method": "Read -> summarize -> quiz -> review mistakes", "timebox": "2 hours"}],
        "how_to_study": [{"tactic": "Active recall", "tailored_guidance": "Ask questions", "citations": [_citation()]}],
        "important_questions": [{"topic": "Topic A", "question_type": "MCQ", "prompt": "What is A?", "citations": [_citation()]}],
    }

    plan = StudyPlan.model_validate(payload)
    pdf_bytes = build_study_plan_pdf(plan)

    assert pdf_bytes.startswith(b"%PDF")
    reader = PdfReader(BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Prioritized Topics" in text
    assert "Day-by-Day Schedule" in text
    assert "Important Questions" in text
