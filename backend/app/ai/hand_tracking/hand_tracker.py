import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions
import os
from pathlib import Path

MODEL_PATH = str(Path(__file__).resolve().parent.parent.parent.parent.parent / "ml" / "models" / "hand_landmarker.task")

CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17)
]

class HandTracker:
    def __init__(self):
        options = HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            running_mode=vision.RunningMode.IMAGE
        )
        self.landmarker = HandLandmarker.create_from_options(options)

    def detect(self, image_bytes: bytes):
        """Takes raw image bytes, returns landmarks or None"""
        import numpy as np
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect(mp_image)
        if result.hand_landmarks:
            return result.hand_landmarks[0]
        return None

    def get_landmarks(self, image_bytes: bytes):
        """Returns flattened landmark vector (63 values) or None"""
        landmarks = self.detect(image_bytes)
        if landmarks is None:
            return None
        vector = []
        for lm in landmarks:
            vector.extend([lm.x, lm.y, lm.z])
        return vector

    def draw(self, frame, hand_landmarks):
        """Draw landmarks on frame"""
        h, w, _ = frame.shape
        for lm in hand_landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
        for start, end in CONNECTIONS:
            x1 = int(hand_landmarks[start].x * w)
            y1 = int(hand_landmarks[start].y * h)
            x2 = int(hand_landmarks[end].x * w)
            y2 = int(hand_landmarks[end].y * h)
            cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
        return frame