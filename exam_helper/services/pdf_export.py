from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from exam_helper.models import StudyPlan


def _citation_line(citations: list[dict]) -> str:
    parts = [f"{c['file']} p/s {c['page_or_slide']}" for c in citations]
    return ", ".join(parts)


def build_study_plan_pdf(plan: StudyPlan) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    flow = []
    flow.append(Paragraph("PrepPilot Study Plan", styles["Title"]))
    flow.append(Spacer(1, 8))
    flow.append(Paragraph(f"Today: {plan.today.isoformat()}", styles["Normal"]))
    flow.append(Paragraph(f"Exam Date: {plan.exam_date.isoformat()}", styles["Normal"]))
    flow.append(Paragraph(f"Countdown Days: {plan.countdown_days}", styles["Normal"]))
    flow.append(Paragraph(f"Cadence: {plan.cadence_recommendation}", styles["Normal"]))
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("Prioritized Topics", styles["Heading2"]))
    for topic in plan.prioritized_topics:
        flow.append(Paragraph(f"- {topic.topic} ({topic.priority}): {topic.rationale}", styles["Normal"]))
        flow.append(Paragraph(f"  Citations: {_citation_line([c.model_dump() for c in topic.citations])}", styles["Normal"]))
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("Day-by-Day Schedule", styles["Heading2"]))
    for day in plan.daily_schedule:
        flow.append(Paragraph(f"- {day.date.isoformat()}: {', '.join(day.topics)}", styles["Normal"]))
        flow.append(Paragraph(f"  Method: {day.method}", styles["Normal"]))
        flow.append(Paragraph(f"  Timebox: {day.timebox}", styles["Normal"]))
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("How To Study", styles["Heading2"]))
    for item in plan.how_to_study:
        flow.append(Paragraph(f"- {item.tactic}: {item.tailored_guidance}", styles["Normal"]))
        flow.append(Paragraph(f"  Citations: {_citation_line([c.model_dump() for c in item.citations])}", styles["Normal"]))
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("Important Questions", styles["Heading2"]))
    for question in plan.important_questions:
        flow.append(Paragraph(f"- [{question.question_type}] {question.topic}: {question.prompt}", styles["Normal"]))
        flow.append(Paragraph(f"  Citations: {_citation_line([c.model_dump() for c in question.citations])}", styles["Normal"]))

    if plan.evidence_quality:
        flow.append(Spacer(1, 12))
        flow.append(Paragraph("Evidence Quality", styles["Heading2"]))
        for ev in plan.evidence_quality:
            flow.append(Paragraph(f"- {ev.section}: {ev.status.upper()} ({ev.score:.2f}) - {ev.note}", styles["Normal"]))

    doc.build(flow)
    return buffer.getvalue()
