from fastapi import APIRouter
from pydantic import BaseModel
from services.assessment_service import AssessmentService

router = APIRouter()
assessment_service = AssessmentService()

class StartAssessmentRequest(BaseModel):
    student_id: str
    letter: str = "A"

class AttemptRequest(BaseModel):
    session_id: str
    predicted: str
    confidence: float
    inference_time: float

@router.post("/assessment/start")
def start_assessment(request: StartAssessmentRequest):
    return assessment_service.start_assessment(
        request.student_id,
        request.letter
    )

@router.post("/assessment/attempt")
def submit_attempt(request: AttemptRequest):
    return assessment_service.submit_attempt(
        request.session_id,
        request.predicted,
        request.confidence,
        request.inference_time
    )

@router.post("/assessment/next/{session_id}")
def next_letter(session_id: str):
    return assessment_service.next_letter(session_id)

@router.get("/assessment/stats/{session_id}")
def get_stats(session_id: str):
    return assessment_service.get_session_stats(session_id)