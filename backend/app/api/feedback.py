from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from services.feedback_service import FeedbackEngine

router = APIRouter()
feedback_engine = FeedbackEngine()

class FeedbackRequest(BaseModel):
    expected: str
    predicted: str
    confidence: float

class RecommendationRequest(BaseModel):
    weak_letters: List[str]

@router.post("/feedback/generate")
def generate_feedback(request: FeedbackRequest):
    return feedback_engine.generate_feedback(
        request.expected,
        request.predicted,
        request.confidence
    )

@router.post("/feedback/recommendations")
def get_recommendations(request: RecommendationRequest):
    return feedback_engine.get_practice_recommendations(request.weak_letters)