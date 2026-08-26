import pickle
import time
import logging
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "gesture_classifier.pkl"

@dataclass
class PredictionResult:
    prediction: str
    confidence: float
    inference_time_ms: float
    model_version: str
    landmarks_detected: bool
    error: Optional[str] = None

class GestureEngine:
    def __init__(self, model_path: str = None, confidence_threshold: float = 0.5):
        self.model_path = Path(model_path) if model_path else MODEL_PATH
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.model_version = self.model_path.stem
        self._load_model()

    def _load_model(self):
        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            logger.info(f"Model loaded: {self.model_version}")
            print(f"Model loaded: {self.model_version}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def _normalize(self, landmarks: list) -> np.ndarray:
        coords = np.array(landmarks).reshape(21, 3)
        wrist = coords[0].copy()
        coords = coords - wrist
        distances = np.sqrt(np.sum(coords**2, axis=1))
        max_dist = np.max(distances)
        if max_dist > 0:
            coords = coords / max_dist
        return coords.flatten()

    def _validate_features(self, features: np.ndarray) -> bool:
        if len(features) != 63:
            return False
        if np.any(np.isnan(features)):
            return False
        return True

    def predict(self, landmarks: list) -> PredictionResult:
        start_time = time.time()
        try:
            features = self._normalize(landmarks)
            if not self._validate_features(features):
                return PredictionResult(
                    prediction="unknown",
                    confidence=0.0,
                    inference_time_ms=0.0,
                    model_version=self.model_version,
                    landmarks_detected=False,
                    error="Invalid feature vector"
                )
            features_2d = features.reshape(1, -1)
            prediction = self.model.predict(features_2d)[0]
            probabilities = self.model.predict_proba(features_2d)[0]
            confidence = float(np.max(probabilities))
            inference_time = round((time.time() - start_time) * 1000, 2)
            logger.info(f"Prediction: {prediction} | Confidence: {confidence:.2f} | Time: {inference_time}ms")
            if confidence < self.confidence_threshold:
                prediction = "uncertain"
            return PredictionResult(
                prediction=prediction,
                confidence=round(confidence, 4),
                inference_time_ms=inference_time,
                model_version=self.model_version,
                landmarks_detected=True
            )
        except Exception as e:
            inference_time = round((time.time() - start_time) * 1000, 2)
            return PredictionResult(
                prediction="error",
                confidence=0.0,
                inference_time_ms=inference_time,
                model_version=self.model_version,
                landmarks_detected=False,
                error=str(e)
            )