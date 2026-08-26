from fastapi import APIRouter
from pydantic import BaseModel
from services.assessment_engine import AssessmentEngine

router = APIRouter()
engine = AssessmentEngine()

class StartSessionRequest(BaseModel):
    student_id: str
    target_letter: str

class EvaluateRequest(BaseModel):
    session_id: str
    predicted: str
    confidence: float
    time_taken_ms: float

@router.post("/assessment-engine/start")
def start_session(request: StartSessionRequest):
    return engine.start_session(request.student_id, request.target_letter)

@router.post("/assessment-engine/evaluate")
def evaluate(request: EvaluateRequest):
    return engine.evaluate(
        request.session_id,
        request.predicted,
        request.confidence,
        request.time_taken_ms
    )

@router.get("/assessment-engine/report/{session_id}")
def get_report(session_id: str):
    return engine.generate_report(session_id)