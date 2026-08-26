from pydantic import BaseModel

class PredictionResponse(BaseModel):
    prediction: str
    confidence: float
    processing_time: float