import cv2
import time
import numpy as np
import pickle
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "gesture_classifier.pkl"

@dataclass
class PredictionResult:
    predicted_gesture: str
    confidence: float
    model_version: str
    inference_time_ms: float
    hand_detected: bool
    error: Optional[str] = None

class SignLanguagePipeline:
    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.model_version = MODEL_PATH.stem
        self.landmarker = None
        self._load_model()
        self._load_mediapipe()

    def _load_model(self):
        with open(MODEL_PATH, 'rb') as f:
            self.model = pickle.load(f)
        print(f"Pipeline model loaded: {self.model_version}")

    def _load_mediapipe(self):
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions

        MODEL_TASK = str(PROJECT_ROOT / "ml" / "models" / "hand_landmarker.task")
        options = HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=MODEL_TASK),
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            running_mode=vision.RunningMode.IMAGE
        )
        self.landmarker = HandLandmarker.create_from_options(options)
        self.mp = mp
        print("MediaPipe loaded in pipeline.")

    def _detect_landmarks(self, frame: np.ndarray):
        """Step 1-2: MediaPipe hand detection"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = self.mp.Image(
            image_format=self.mp.ImageFormat.SRGB,
            data=rgb
        )
        result = self.landmarker.detect(mp_image)
        if result.hand_landmarks:
            return result.hand_landmarks[0]
        return None

    def _validate_landmarks(self, landmarks) -> bool:
        """Step 3: Landmark validation"""
        if landmarks is None:
            return False
        if len(landmarks) != 21:
            return False
        return True

    def _normalize(self, landmarks) -> np.ndarray:
        """Step 4: Feature normalization — wrist-relative"""
        vector = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
        wrist = vector[0].copy()
        vector = vector - wrist
        max_dist = np.max(np.sqrt(np.sum(vector**2, axis=1)))
        if max_dist > 0:
            vector = vector / max_dist
        return vector.flatten()

    def _generate_feature_vector(self, landmarks) -> np.ndarray:
        """Step 5: Generate 63-dimensional feature vector"""
        features = self._normalize(landmarks)
        assert len(features) == 63, "Feature vector must be 63 values"
        return features

    def predict(self, frame: np.ndarray) -> PredictionResult:
        """
        Main pipeline interface.
        Input: BGR image frame (numpy array)
        Output: PredictionResult
        """
        start_time = time.time()

        try:
            # Step 1-2: Detect hand
            landmarks = self._detect_landmarks(frame)

            # Step 3: Validate
            if not self._validate_landmarks(landmarks):
                return PredictionResult(
                    predicted_gesture="no_hand",
                    confidence=0.0,
                    model_version=self.model_version,
                    inference_time_ms=round((time.time()-start_time)*1000, 2),
                    hand_detected=False,
                    error="No hand detected in frame"
                )

            # Step 4-5: Normalize and generate feature vector
            features = self._generate_feature_vector(landmarks)

            # Step 6: Load model + predict
            features_2d = features.reshape(1, -1)
            prediction = self.model.predict(features_2d)[0]
            probabilities = self.model.predict_proba(features_2d)[0]
            confidence = float(np.max(probabilities))

            # Apply confidence threshold
            if confidence < self.confidence_threshold:
                prediction = "uncertain"

            inference_time = round((time.time() - start_time) * 1000, 2)

            logger.info(f"Gesture: {prediction} | Confidence: {confidence:.2f} | Time: {inference_time}ms")

            return PredictionResult(
                predicted_gesture=prediction,
                confidence=round(confidence, 4),
                model_version=self.model_version,
                inference_time_ms=inference_time,
                hand_detected=True
            )

        except Exception as e:
            return PredictionResult(
                predicted_gesture="error",
                confidence=0.0,
                model_version=self.model_version,
                inference_time_ms=round((time.time()-start_time)*1000, 2),
                hand_detected=False,
                error=str(e)
            )