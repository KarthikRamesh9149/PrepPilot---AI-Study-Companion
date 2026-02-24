from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Citation(BaseModel):
    file: str = Field(min_length=1)
    page_or_slide: int = Field(ge=1)
    snippet_reference: str = Field(min_length=1)


class CitationDisplay(BaseModel):
    file: str
    page_or_slide: int
    snippet_reference: str
    valid: bool


class QuizQuestion(BaseModel):
    question_id: str = Field(min_length=1)
    topic_tag: str = Field(default="General", min_length=1)
    question: str = Field(min_length=1)
    options: dict[str, str]
    correct_option: Literal["A", "B", "C", "D"]
    explanation: str = Field(min_length=1)
    citations: list[Citation] = Field(min_length=1)

    @field_validator("options")
    @classmethod
    def validate_options(cls, value: dict[str, str]) -> dict[str, str]:
        expected_keys = {"A", "B", "C", "D"}
        if set(value.keys()) != expected_keys:
            raise ValueError("Options must contain exactly A, B, C, D")
        for key, option_text in value.items():
            if not option_text or not option_text.strip():
                raise ValueError(f"Option {key} cannot be empty")
        return value


class QuizSet(BaseModel):
    difficulty: Literal["Easy", "Medium", "Hard"]
    coverage_summary: list[str] = Field(default_factory=list)
    questions: list[QuizQuestion]

    @field_validator("questions")
    @classmethod
    def validate_question_count(cls, value: list[QuizQuestion]) -> list[QuizQuestion]:
        if len(value) != 15:
            raise ValueError("Quiz must contain exactly 15 questions")
        return value


class PrioritizedTopic(BaseModel):
    topic: str = Field(min_length=1)
    priority: Literal["High", "Medium", "Low"]
    rationale: str = Field(min_length=1)
    citations: list[Citation] = Field(min_length=1)


class DailyScheduleItem(BaseModel):
    date: date
    topics: list[str] = Field(min_length=1)
    method: str = Field(min_length=1)
    timebox: str = Field(min_length=1)


class StudyGuidanceItem(BaseModel):
    tactic: str = Field(min_length=1)
    tailored_guidance: str = Field(min_length=1)
    citations: list[Citation] = Field(min_length=1)


class ImportantQuestion(BaseModel):
    topic: str = Field(min_length=1)
    question_type: Literal["MCQ", "ShortAnswer", "Conceptual", "Application"]
    prompt: str = Field(min_length=1)
    citations: list[Citation] = Field(min_length=1)


class EvidenceQuality(BaseModel):
    section: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)
    status: Literal["ok", "weak"]
    note: str = Field(min_length=1)


class TopicConfidence(BaseModel):
    topic: str = Field(min_length=1)
    confidence: Literal["Low", "Medium", "High"]


class StudentProfile(BaseModel):
    hours_per_day: int = Field(ge=1, le=12)
    preferred_study_window: Literal["Morning", "Afternoon", "Evening"]
    topic_confidence: list[TopicConfidence] = Field(default_factory=list)


class StudyPlan(BaseModel):
    title: str = Field(min_length=1)
    today: date
    exam_date: date
    countdown_days: int = Field(ge=0)
    cadence_recommendation: str = Field(min_length=1)
    prioritized_topics: list[PrioritizedTopic] = Field(min_length=1)
    daily_schedule: list[DailyScheduleItem] = Field(min_length=1)
    how_to_study: list[StudyGuidanceItem] = Field(min_length=1)
    important_questions: list[ImportantQuestion] = Field(min_length=1)
    evidence_quality: list[EvidenceQuality] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> "StudyPlan":
        if self.exam_date < self.today:
            raise ValueError("exam_date cannot be earlier than today")
        return self
