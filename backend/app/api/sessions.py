from fastapi import APIRouter
from services.session_service import SessionService

router = APIRouter()
session_service = SessionService()

@router.post("/sessions/start/{lesson_id}")
def start_session(lesson_id: int):
    return session_service.start_session(lesson_id)

@router.put("/sessions/end/{session_id}")
def end_session(session_id: str):
    return session_service.end_session(session_id)

@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    return session_service.get_session(session_id)