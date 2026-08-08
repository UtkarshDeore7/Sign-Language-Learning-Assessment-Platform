from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.progress_service import ProgressService

router = APIRouter()
progress_service = ProgressService()


@router.get("/progress/{student_id}")
def get_progress_overview(student_id: str, db: Session = Depends(get_db)):
    return progress_service.get_progress_overview(db, student_id)


@router.get("/progress/{student_id}/summary/{session_id}")
def get_session_progress(student_id: str, session_id: str, db: Session = Depends(get_db)):
    return progress_service.get_session_progress_summary(db, student_id, session_id)


@router.get("/progress/{student_id}/alphabet-trends")
def get_alphabet_trends(student_id: str, db: Session = Depends(get_db)):
    return progress_service.get_alphabet_trends(db, student_id)