import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from ai.utils.camera import Camera

MODEL_PATH = "ml/models/hand_landmarker.task"

def print_landmarks(hand_landmarks_list):
    for hand_idx, hand_landmarks in enumerate(hand_landmarks_list):
        print(f"\nHand {hand_idx + 1}")
        for lm_idx, lm in enumerate(hand_landmarks):
            print(f"  Landmark {lm_idx} : x={lm.x:.4f} y={lm.y:.4f} z={lm.z:.4f}")

def run_landmark_extraction():
    options = HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=vision.RunningMode.IMAGE
    )

    cam = Camera()
    print("Landmark extraction started. Press Q to quit.")

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
                print_landmarks(result.hand_landmarks)
                cv2.putText(frame, f"Hands: {len(result.hand_landmarks)}",
                           (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "No Hand Detected",
                           (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            cv2.imshow("Landmark Extraction", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cam.release()

if __name__ == "__main__":
    run_landmark_extraction()