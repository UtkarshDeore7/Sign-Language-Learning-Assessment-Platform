from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import AssessmentAttempt
from services.error_analysis_service import ErrorAnalysisService

router = APIRouter()
error_analysis_service = ErrorAnalysisService()


@router.get("/error-analysis/{student_id}")
def get_error_analysis(student_id: str, db: Session = Depends(get_db)):
    rows = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.student_id == str(student_id)
    ).all()

    # Convert ORM rows to the dict format analyze() expects
    attempts = [
        {
            "student_id":      a.student_id,
            "target_letter":   a.target_letter,
            "predicted_letter":a.predicted_letter,
            "is_correct":      a.is_correct,
            "confidence":      a.confidence
        }
        for a in rows
    ]

    return error_analysis_service.analyze(attempts)