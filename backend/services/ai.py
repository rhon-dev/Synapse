"""OpenAI client wrapper. Handles chat completion + JSON-mode quiz generation."""
import json
import os
from typing import Optional

from fastapi import HTTPException, status
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    """Lazy-init singleton OpenAI async client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OPENAI_API_KEY not configured on server.",
            )
        _client = AsyncOpenAI(api_key=api_key, timeout=30.0, max_retries=1)
    return _client


def _map_openai_error(exc: Exception) -> HTTPException:
    """Convert openai SDK errors → HTTPException with correct status."""
    if isinstance(exc, AuthenticationError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OpenAI authentication failed. Check OPENAI_API_KEY.",
        )
    if isinstance(exc, RateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="OpenAI rate limit exceeded. Try again shortly.",
        )
    if isinstance(exc, APITimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="OpenAI request timed out.",
        )
    if isinstance(exc, APIConnectionError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach OpenAI.",
        )
    if isinstance(exc, APIError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI API error: {exc}",
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unexpected AI error: {exc}",
    )


CHAT_SYSTEM_PROMPT = (
    "You are Synapse, an expert study partner. The user is studying {subject}. "
    "Answer clearly, accurately, and concisely. If the question is off-topic, "
    "redirect them."
)


async def chat_answer(subject: str, question: str) -> str:
    """Return AI answer for a single user question scoped to subject."""
    client = get_client()
    try:
        resp = await client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": CHAT_SYSTEM_PROMPT.format(subject=subject)},
                {"role": "user", "content": question},
            ],
            temperature=0.4,
        )
    except Exception as exc:
        raise _map_openai_error(exc) from exc

    content = resp.choices[0].message.content
    if not content:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI returned an empty response.",
        )
    return content.strip()


QUIZ_SYSTEM_PROMPT = (
    "You are Synapse, a quiz generator. Generate exactly 5 multiple-choice "
    "questions for the subject '{subject}' at '{difficulty}' difficulty. "
    "Return ONLY valid JSON matching this schema:\n"
    '{{"questions": [{{"question": "...", "options": ["A text","B text","C text","D text"], '
    '"answer": "A|B|C|D", "explanation": "..."}}]}}\n'
    "Rules:\n"
    "- Exactly 5 questions.\n"
    "- options array must have exactly 4 strings (no leading 'A) ' prefixes — pure choice text).\n"
    "- answer is one of 'A','B','C','D' indicating index 0,1,2,3.\n"
    "- explanation explains why the answer is correct in 1–2 sentences.\n"
    "- No commentary outside JSON."
)


async def generate_quiz(subject: str, difficulty: str) -> list[dict]:
    """Generate 5-question quiz via OpenAI JSON mode. Returns list of question dicts."""
    client = get_client()
    try:
        resp = await client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": QUIZ_SYSTEM_PROMPT.format(
                        subject=subject, difficulty=difficulty
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Generate 5 {difficulty}-level multiple-choice questions "
                        f"about {subject}."
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
    except Exception as exc:
        raise _map_openai_error(exc) from exc

    raw = resp.choices[0].message.content
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI returned empty quiz payload.",
        )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI returned invalid JSON: {exc}",
        ) from exc

    questions = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(questions, list) or len(questions) != 5:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI did not return exactly 5 questions.",
        )

    # Per-question structural validation — fail loud rather than serve bad quiz
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Question {i} is not an object.",
            )
        opts = q.get("options")
        if (
            not isinstance(q.get("question"), str)
            or not isinstance(opts, list)
            or len(opts) != 4
            or not all(isinstance(o, str) for o in opts)
            or q.get("answer") not in ("A", "B", "C", "D")
            or not isinstance(q.get("explanation"), str)
        ):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Question {i} failed schema validation.",
            )

    return questions
