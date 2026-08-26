"""
Learner State API
=================
GET  /api/state/{student_id}                — all 26 letter states + summary
GET  /api/state/{student_id}/{letter}       — single letter state
GET  /api/state/{student_id}/{letter}/history — full transition history
GET  /api/state/{student_id}/recommendations — prioritised practice queue
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.learner_state_service import LearnerStateService

router = APIRouter()
state_service = LearnerStateService()


@router.get("/state/{student_id}")
def get_all_states(student_id: str, db: Session = Depends(get_db)):
    return state_service.get_all_states(db, student_id)


@router.get("/state/{student_id}/recommendations")
def get_recommendations(student_id: str, db: Session = Depends(get_db)):
    return state_service.get_recommendations(db, student_id)


@router.get("/state/{student_id}/{letter}/history")
def get_history(student_id: str, letter: str, db: Session = Depends(get_db)):
    return state_service.get_state_history(db, student_id, letter)


@router.get("/state/{student_id}/{letter}")
def get_state(student_id: str, letter: str, db: Session = Depends(get_db)):
    return state_service.get_state(db, student_id, letter)