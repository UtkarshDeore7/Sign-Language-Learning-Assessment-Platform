import json
import csv
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ASL_PATH = PROJECT_ROOT / "ml" / "datasets" / "asl-alphabet" / "asl_alphabet_train" / "asl_alphabet_train"
MODEL_PATH = str(PROJECT_ROOT / "ml" / "models" / "hand_landmarker.task")
OUTPUT_CSV = PROJECT_ROOT / "ml" / "training" / "landmarks.csv"
REPORT_PATH = PROJECT_ROOT / "ml" / "training" / "dataset_report.json"

class PreprocessingService:
    def run(self):
        # If CSV already exists return existing report
        if OUTPUT_CSV.exists() and REPORT_PATH.exists():
            with open(REPORT_PATH, 'r') as f:
                report = json.load(f)
            return {
                "success": True,
                "message": "Dataset preprocessing already completed.",
                "data": {
                    "images_processed": report["total_samples"],
                    "successful": report["successful"],
                    "failed": report["failed"],
                    "csv_file": "landmarks.csv"
                },
                "timestamp": datetime.now().isoformat()
            }

        options = HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            running_mode=vision.RunningMode.IMAGE
        )

        classes = sorted(os.listdir(ASL_PATH))
        header = [f"{a}{i}" for i in range(21) for a in ['x','y','z']]
        header.append("label")

        total = 0
        successful = 0
        failed = 0

        os.makedirs(PROJECT_ROOT / "ml" / "training", exist_ok=True)

        with HandLandmarker.create_from_options(options) as landmarker:
            with open(OUTPUT_CSV, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header)

                for cls in classes:
                    cls_path = ASL_PATH / cls
                    for img_file in os.listdir(cls_path):
                        total += 1
                        try:
                            img = cv2.imread(str(cls_path / img_file))
                            if img is None:
                                failed += 1
                                continue
                            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                            mp_image = mp.Image(
                                image_format=mp.ImageFormat.SRGB, data=rgb)
                            result = landmarker.detect(mp_image)
                            if result.hand_landmarks:
                                lms = result.hand_landmarks[0]
                                row = [v for lm in lms
                                       for v in [round(lm.x,4),
                                                 round(lm.y,4),
                                                 round(lm.z,4)]]
                                row.append(cls)
                                writer.writerow(row)
                                successful += 1
                            else:
                                failed += 1
                        except Exception:
                            failed += 1

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_samples": total,
            "successful": successful,
            "failed": failed,
            "success_percentage": f"{round((successful/total)*100,2)}%"
        }

        with open(REPORT_PATH, 'w') as f:
            json.dump(report, f, indent=2)

        return {
            "success": True,
            "message": "Dataset preprocessing completed.",
            "data": {
                "images_processed": total,
                "successful": successful,
                "failed": failed,
                "csv_file": "landmarks.csv"
            },
            "timestamp": datetime.now().isoformat()
        }