from fastapi import APIRouter
from services.preprocessing_service import PreprocessingService

router = APIRouter()
preprocessing_service = PreprocessingService()

@router.post("/preprocess")
def preprocess():
    return preprocessing_service.run()