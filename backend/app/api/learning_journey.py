from fastapi import APIRouter
from pydantic import BaseModel
from services.learning_journey_service import LearningJourneyService

router = APIRouter()
journey_service = LearningJourneyService()

class UpdateProfileRequest(BaseModel):
    student_id: str
    target_letter: str
    predicted_letter: str
    is_correct: bool
    confidence: float

@router.post("/journey/update")
def update_profile(request: UpdateProfileRequest):
    return journey_service.update_profile(
        request.student_id,
        request.target_letter,
        request.predicted_letter,
        request.is_correct,
        request.confidence
    )

@router.get("/journey/profile/{student_id}")
def get_profile(student_id: str):
    return journey_service.get_profile(student_id)

@router.get("/journey/recommendations/{student_id}")
def get_recommendations(student_id: str):
    return journey_service.generate_recommendations(student_id)