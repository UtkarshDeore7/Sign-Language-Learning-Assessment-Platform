from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from services.review_service import ReviewService

router = APIRouter()
review_service = ReviewService()

class AttemptRecord(BaseModel):
    expected_gesture: str
    predicted_gesture: str
    is_correct: bool
    confidence: float

class ReviewRequest(BaseModel):
    session_id: str
    attempts: List[AttemptRecord]

@router.post("/review/generate")
def generate_review(request: ReviewRequest):
    attempts = [a.dict() for a in request.attempts]
    return review_service.generate_review(request.session_id, attempts)