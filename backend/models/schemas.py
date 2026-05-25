"""Pydantic v2 request/response schemas."""
from datetime import datetime
from enum import Enum
from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


class Difficulty(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


# ---------- Chat ----------

class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    subject: str = Field(..., min_length=1, max_length=64)
    question: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    session_id: str
    subject: str
    question: str
    answer: str
    timestamp: datetime


# ---------- Quiz ----------

class QuizGenerateRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    subject: str = Field(..., min_length=1, max_length=64)
    difficulty: Difficulty


class QuizQuestion(BaseModel):
    question: str
    options: List[str] = Field(..., min_length=4, max_length=4)
    answer: Literal["A", "B", "C", "D"]
    explanation: str


class QuizGenerateResponse(BaseModel):
    quiz_id: str
    session_id: str
    subject: str
    difficulty: Difficulty
    questions: List[QuizQuestion]


class QuizSubmitRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    quiz_id: str = Field(..., min_length=1, max_length=128)
    answers: List[Literal["A", "B", "C", "D"]] = Field(..., min_length=1, max_length=50)

    @field_validator("answers")
    @classmethod
    def _non_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("answers cannot be empty")
        return v


class QuestionResult(BaseModel):
    question: str
    your_answer: str
    correct_answer: str
    correct: bool
    explanation: str


class QuizSubmitResponse(BaseModel):
    quiz_id: str
    session_id: str
    score: int
    total: int
    results: List[QuestionResult]


# ---------- Session ----------

class SessionEvent(BaseModel):
    session_id: str
    timestamp: datetime
    type: Literal["chat", "quiz_generated", "quiz_submitted"]
    payload: dict


class SessionHistoryResponse(BaseModel):
    session_id: str
    count: int
    events: List[SessionEvent]


class DeleteResponse(BaseModel):
    session_id: str
    deleted: int
