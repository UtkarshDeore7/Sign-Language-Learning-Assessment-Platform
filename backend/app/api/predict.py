from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from services.gesture_service import GestureService

router = APIRouter()
gesture_service = GestureService()

class PredictRequest(BaseModel):
    landmarks: Optional[List[float]] = None

@router.post("/predict")
def predict(request: PredictRequest = None):
    landmarks = request.landmarks if request else None
    result = gesture_service.predict(landmarks)
    return result