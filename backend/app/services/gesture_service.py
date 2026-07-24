import time
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.ml.inference.gesture_engine import GestureEngine

class GestureService:
    def __init__(self):
        self.engine = GestureEngine()

    def predict(self, landmarks: list = None):
        start_time = time.time()

        if landmarks is None:
            # Stub response when no landmarks provided
            return {
                "prediction": "A",
                "confidence": 0.95,
                "processing_time": round(time.time() - start_time, 4),
                "hands_detected": 0,
                "landmarks": None,
                "model_version": "gesture_classifier"
            }

        result = self.engine.predict(landmarks)

        return {
            "prediction": result.prediction,
            "confidence": result.confidence,
            "processing_time": round(result.inference_time_ms / 1000, 4),
            "hands_detected": 1 if result.landmarks_detected else 0,
            "landmarks": None,
            "model_version": result.model_version
        }