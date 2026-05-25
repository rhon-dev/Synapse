"""Session history endpoints."""
from fastapi import APIRouter, HTTPException, Path, status

from backend.db.mongo import get_db
from backend.models.schemas import DeleteResponse, SessionEvent, SessionHistoryResponse

router = APIRouter()


@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
async def get_session(
    session_id: str = Path(..., min_length=1, max_length=128),
) -> SessionHistoryResponse:
    db = get_db()
    cursor = db.events.find({"session_id": session_id}).sort("timestamp", 1)
    docs = await cursor.to_list(length=1000)

    events = [
        SessionEvent(
            session_id=d["session_id"],
            timestamp=d["timestamp"],
            type=d["type"],
            payload=d["payload"],
        )
        for d in docs
    ]
    return SessionHistoryResponse(
        session_id=session_id, count=len(events), events=events
    )


@router.delete("/sessions/{session_id}", response_model=DeleteResponse)
async def delete_session(
    session_id: str = Path(..., min_length=1, max_length=128),
) -> DeleteResponse:
    db = get_db()
    result = await db.events.delete_many({"session_id": session_id})
    if result.deleted_count == 0:
        # Idempotent delete — 200 with deleted:0 is fine, but signal no-op clearly
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No events found for this session.",
        )
    return DeleteResponse(session_id=session_id, deleted=result.deleted_count)
