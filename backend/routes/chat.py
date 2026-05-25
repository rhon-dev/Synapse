"""Chat + quiz endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter

from backend.db.mongo import get_db
from backend.models.schemas import (
    ChatRequest,
    ChatResponse,
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizQuestion,
    QuizSubmitRequest,
    QuizSubmitResponse,
)
from backend.services.ai import chat_answer, generate_quiz
from backend.services.quiz import grade, load_quiz, store_generated_quiz, store_submission

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def post_chat(req: ChatRequest) -> ChatResponse:
    answer = await chat_answer(req.subject, req.question)
    ts = datetime.now(timezone.utc)

    db = get_db()
    await db.events.insert_one(
        {
            "session_id": req.session_id,
            "timestamp": ts,
            "type": "chat",
            "payload": {
                "subject": req.subject,
                "question": req.question,
                "answer": answer,
            },
        }
    )
    return ChatResponse(
        session_id=req.session_id,
        subject=req.subject,
        question=req.question,
        answer=answer,
        timestamp=ts,
    )


@router.post("/quiz/generate", response_model=QuizGenerateResponse)
async def post_quiz_generate(req: QuizGenerateRequest) -> QuizGenerateResponse:
    raw_questions = await generate_quiz(req.subject, req.difficulty.value)
    questions = [QuizQuestion(**q) for q in raw_questions]
    quiz_id = await store_generated_quiz(
        req.session_id, req.subject, req.difficulty.value, questions
    )
    return QuizGenerateResponse(
        quiz_id=quiz_id,
        session_id=req.session_id,
        subject=req.subject,
        difficulty=req.difficulty,
        questions=questions,
    )


@router.post("/quiz/submit", response_model=QuizSubmitResponse)
async def post_quiz_submit(req: QuizSubmitRequest) -> QuizSubmitResponse:
    payload = await load_quiz(req.session_id, req.quiz_id)
    questions = payload["questions"]
    score, results = grade(questions, req.answers)
    await store_submission(req.session_id, req.quiz_id, score, len(questions), results)
    return QuizSubmitResponse(
        quiz_id=req.quiz_id,
        session_id=req.session_id,
        score=score,
        total=len(questions),
        results=results,
    )
