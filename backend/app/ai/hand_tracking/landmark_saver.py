import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from ai.utils.camera import Camera

MODEL_PATH = "ml/models/hand_landmarker.task"
CAPTURES_DIR = "captures"

def save_landmarks(hand_landmarks_list):
    os.makedirs(CAPTURES_DIR, exist_ok=True)
    existing = [f for f in os.listdir(CAPTURES_DIR) if f.endswith('.json')]
    capture_num = len(existing) + 1
    filename = f"capture_{capture_num:03d}.json"
    filepath = os.path.join(CAPTURES_DIR, filename)

    data = {
        "timestamp": datetime.now().isoformat(),
        "hands": []
    }

    for hand_idx, hand_landmarks in enumerate(hand_landmarks_list):
        hand_data = {
            "hand_number": hand_idx + 1,
            "landmarks": []
        }
        for lm_idx, lm in enumerate(hand_landmarks):
            hand_data["landmarks"].append({
                "landmark_id": lm_idx,
                "x": round(lm.x, 4),
                "y": round(lm.y, 4),
                "z": round(lm.z, 4)
            })
        data["hands"].append(hand_data)

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Saved: {filepath}")

def run_landmark_saver():
    options = HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=vision.RunningMode.IMAGE
    )

    cam = Camera()
    print("Landmark saver started. Press S to save, Q to quit.")
    current_landmarks = None

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
                current_landmarks = result.hand_landmarks
                cv2.putText(frame, f"Hands: {len(result.hand_landmarks)} | Press S to save",
                           (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            else:
                current_landmarks = None
                cv2.putText(frame, "No Hand Detected",
                           (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            cv2.imshow("Landmark Saver", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('s') and current_landmarks:
                save_landmarks(current_landmarks)
            elif key == ord('q'):
                break

    cam.release()

if __name__ == "__main__":
    run_landmark_saver()