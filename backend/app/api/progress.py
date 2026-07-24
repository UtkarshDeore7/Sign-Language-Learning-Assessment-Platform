from fastapi import APIRouter
from pydantic import BaseModel
from services.progress_service import ProgressService

router = APIRouter()
progress_service = ProgressService()

class StoreAttemptRequest(BaseModel):
    student_id: str
    target_letter: str
    predicted_letter: str
    is_correct: bool
    confidence: float
    inference_time: float

@router.post("/progress/attempt")
def store_attempt(request: StoreAttemptRequest):
    attempt = progress_service.store_attempt(
        request.student_id,
        request.target_letter,
        request.predicted_letter,
        request.is_correct,
        request.confidence,
        request.inference_time
    )
    return {
        "success": True,
        "message": "Attempt stored successfully",
        "data": attempt,
        "timestamp": attempt["timestamp"]
    }

@router.get("/progress/dashboard/{student_id}")
def get_dashboard(student_id: str):
    return progress_service.get_dashboard(student_id)