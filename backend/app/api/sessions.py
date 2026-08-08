"""
Sessions API
============
POST   /api/sessions/start            — start a new practice session
POST   /api/sessions/attempt          — record one prediction attempt
PUT    /api/sessions/end/{session_id} — end session, get summary
GET    /api/sessions/{session_id}     — fetch session details
GET    /api/sessions/student/{student_id} — all sessions for a student
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from services.session_service import SessionService

router = APIRouter()
session_service = SessionService()


# ─── Request models ───────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    student_id: str


class AttemptRequest(BaseModel):
    session_id:        str
    student_id:        str
    target_letter:     str
    predicted_letter:  str
    is_correct:        bool
    confidence:        float
    inference_time_ms: float
    hand_detected:     bool = True
    frame_valid:       bool = True


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/sessions/start")
def start_session(request: StartSessionRequest, db: Session = Depends(get_db)):
    return session_service.start_session(db, request.student_id)


@router.post("/sessions/attempt")
def record_attempt(request: AttemptRequest, db: Session = Depends(get_db)):
    return session_service.record_attempt(
        db,
        session_id        = request.session_id,
        student_id        = request.student_id,
        target_letter     = request.target_letter,
        predicted_letter  = request.predicted_letter,
        is_correct        = request.is_correct,
        confidence        = request.confidence,
        inference_time_ms = request.inference_time_ms,
        hand_detected     = request.hand_detected,
        frame_valid       = request.frame_valid
    )


@router.put("/sessions/end/{session_id}")
def end_session(session_id: str, db: Session = Depends(get_db)):
    return session_service.end_session(db, session_id)


@router.get("/sessions/student/{student_id}")
def get_student_sessions(student_id: str, db: Session = Depends(get_db)):
    return session_service.get_student_sessions(db, student_id)


@router.get("/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    return session_service.get_session(db, session_id)