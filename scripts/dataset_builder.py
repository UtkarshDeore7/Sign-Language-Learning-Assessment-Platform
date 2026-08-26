import csv
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASL_PATH = PROJECT_ROOT / "ml" / "datasets" / "asl-alphabet" / "asl_alphabet_train" / "asl_alphabet_train"
MODEL_PATH = str(PROJECT_ROOT / "ml" / "models" / "hand_landmarker.task")
OUTPUT_CSV = PROJECT_ROOT / "ml" / "training" / "landmarks.csv"

os.makedirs(PROJECT_ROOT / "ml" / "training", exist_ok=True)

def extract_landmarks_from_image(landmarker, img_path):
    img = cv2.imread(str(img_path))
    if img is None:
        return None
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = landmarker.detect(mp_image)
    if result.hand_landmarks:
        landmarks = result.hand_landmarks[0]
        vector = []
        for lm in landmarks:
            vector.extend([round(lm.x, 4), round(lm.y, 4), round(lm.z, 4)])
        return vector
    return None

def build_dataset():
    options = HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=vision.RunningMode.IMAGE
    )

    classes = sorted(os.listdir(ASL_PATH))
    header = []
    for i in range(21):
        header.extend([f"x{i}", f"y{i}", f"z{i}"])
    header.append("label")

    total = 0
    success = 0
    failed = 0

    print("Building dataset...")

    with HandLandmarker.create_from_options(options) as landmarker:
        with open(OUTPUT_CSV, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)

            for cls in classes:
                cls_path = ASL_PATH / cls
                images = os.listdir(cls_path)
                print(f"Processing {cls}...")

                for img_file in images:
                    total += 1
                    vector = extract_landmarks_from_image(
                        landmarker, cls_path / img_file
                    )
                    if vector:
                        writer.writerow(vector + [cls])
                        success += 1
                    else:
                        failed += 1

    print(f"\nDone: {success}/{total} successful")
    return total, success, failed

if __name__ == "__main__":
    build_dataset()