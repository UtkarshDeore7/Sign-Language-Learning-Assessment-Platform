from fastapi import APIRouter
from pydantic import BaseModel
from services.adaptive_learning_service import AdaptiveLearningService

router = APIRouter()
adaptive_service = AdaptiveLearningService()

class AttemptRequest(BaseModel):
    session_id: str
    student_id: str
    predicted: str
    confidence: float
    time_taken_ms: float

@router.post("/adaptive/attempt")
def process_attempt(request: AttemptRequest):
    return adaptive_service.process_attempt(
        request.session_id,
        request.student_id,
        request.predicted,
        request.confidence,
        request.time_taken_ms
    )