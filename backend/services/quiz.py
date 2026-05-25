"""Quiz domain logic: persistence + grading."""
import uuid
from datetime import datetime, timezone
from typing import List, Sequence

from fastapi import HTTPException, status

from backend.db.mongo import get_db
from backend.models.schemas import QuestionResult, QuizQuestion


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def store_generated_quiz(
    session_id: str,
    subject: str,
    difficulty: str,
    questions: List[QuizQuestion],
) -> str:
    """Persist generated quiz, return quiz_id."""
    db = get_db()
    quiz_id = str(uuid.uuid4())
    doc = {
        "session_id": session_id,
        "timestamp": _utcnow(),
        "type": "quiz_generated",
        "payload": {
            "quiz_id": quiz_id,
            "subject": subject,
            "difficulty": difficulty,
            "questions": [q.model_dump() for q in questions],
        },
    }
    await db.events.insert_one(doc)
    return quiz_id


async def load_quiz(session_id: str, quiz_id: str) -> dict:
    """Load a previously generated quiz by session+quiz id."""
    db = get_db()
    doc = await db.events.find_one(
        {
            "session_id": session_id,
            "type": "quiz_generated",
            "payload.quiz_id": quiz_id,
        }
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found for this session.",
        )
    return doc["payload"]


def grade(
    questions: List[dict], answers: Sequence[str]
) -> tuple[int, List[QuestionResult]]:
    """Score answers against correct ones. Returns (score, per-question results)."""
    if len(answers) != len(questions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Expected {len(questions)} answers, got {len(answers)}."
            ),
        )

    results: List[QuestionResult] = []
    score = 0
    for q, given in zip(questions, answers):
        correct_letter = q["answer"]
        is_correct = given == correct_letter
        if is_correct:
            score += 1
        results.append(
            QuestionResult(
                question=q["question"],
                your_answer=given,
                correct_answer=correct_letter,
                correct=is_correct,
                explanation=q["explanation"],
            )
        )
    return score, results


async def store_submission(
    session_id: str,
    quiz_id: str,
    score: int,
    total: int,
    results: List[QuestionResult],
) -> None:
    """Persist quiz submission result."""
    db = get_db()
    doc = {
        "session_id": session_id,
        "timestamp": _utcnow(),
        "type": "quiz_submitted",
        "payload": {
            "quiz_id": quiz_id,
            "score": score,
            "total": total,
            "results": [r.model_dump() for r in results],
        },
    }
    await db.events.insert_one(doc)
