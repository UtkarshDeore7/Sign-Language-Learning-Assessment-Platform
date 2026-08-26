import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from ai.utils.camera import Camera

MODEL_PATH = "ml/models/hand_landmarker.task"

def euclidean_distance(lm1, lm2):
    return math.sqrt(
        (lm1.x - lm2.x) ** 2 +
        (lm1.y - lm2.y) ** 2 +
        (lm1.z - lm2.z) ** 2
    )

def run_distance_tracker():
    options = HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=vision.RunningMode.IMAGE
    )

    cam = Camera()
    print("Distance tracker started. Press Q to quit.")

    with HandLandmarker.create_from_options(options) as landmarker:
        while True:
            frame = cam.get_frame()
            if frame is None:
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            result = landmarker.detect(mp_image)

            if result.hand_landmarks:
                hand = result.hand_landmarks[0]
                thumb_tip = hand[4]
                index_tip = hand[8]

                dist = euclidean_distance(thumb_tip, index_tip)

                # Draw dots on thumb and index tips
                h, w, _ = frame.shape
                tx, ty = int(thumb_tip.x * w), int(thumb_tip.y * h)
                ix, iy = int(index_tip.x * w), int(index_tip.y * h)
                cv2.circle(frame, (tx, ty), 8, (0, 255, 0), -1)
                cv2.circle(frame, (ix, iy), 8, (0, 0, 255), -1)
                cv2.line(frame, (tx, ty), (ix, iy), (255, 255, 0), 2)

                cv2.putText(frame, f"Distance: {dist:.4f}",
                           (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
            else:
                cv2.putText(frame, "No Hand Detected",
                           (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            cv2.imshow("Distance Tracker", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cam.release()

if __name__ == "__main__":
    run_distance_tracker()