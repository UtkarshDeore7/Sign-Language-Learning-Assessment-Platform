import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions
import urllib.request
import os

MODEL_PATH = "ml/models/hand_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

def download_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading hand landmarker model...")
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Model downloaded!")

def draw_landmarks(frame, hand_landmarks_list):
    h, w, _ = frame.shape
    connections = [
        (0,1),(1,2),(2,3),(3,4),
        (0,5),(5,6),(6,7),(7,8),
        (0,9),(9,10),(10,11),(11,12),
        (0,13),(13,14),(14,15),(15,16),
        (0,17),(17,18),(18,19),(19,20),
        (5,9),(9,13),(13,17)
    ]
    for hand_landmarks in hand_landmarks_list:
        for lm in hand_landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
        for start, end in connections:
            x1 = int(hand_landmarks[start].x * w)
            y1 = int(hand_landmarks[start].y * h)
            x2 = int(hand_landmarks[end].x * w)
            y2 = int(hand_landmarks[end].y * h)
            cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

def run_hand_tracking():
    download_model()

    options = HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=vision.RunningMode.IMAGE
    )

    cap = cv2.VideoCapture(0)
    print("Hand tracking started. Press Q to quit.")

    with HandLandmarker.create_from_options(options) as landmarker:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            result = landmarker.detect(mp_image)

            if result.hand_landmarks:
                draw_landmarks(frame, result.hand_landmarks)
                cv2.putText(frame, f"Hands: {len(result.hand_landmarks)}",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                print(f"Hands detected: {len(result.hand_landmarks)}")

            cv2.imshow("Hand Tracking", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_hand_tracking()