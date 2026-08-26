import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions
import os
import csv
import json
from pathlib import Path
from datetime import datetime

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASL_PATH = PROJECT_ROOT / "ml" / "datasets" / "asl-alphabet" / "asl_alphabet_train" / "asl_alphabet_train"
MODEL_PATH = str(PROJECT_ROOT / "ml" / "models" / "hand_landmarker.task")
OUTPUT_CSV = PROJECT_ROOT / "ml" / "training" / "landmarks.csv"
REPORT_PATH = PROJECT_ROOT / "ml" / "training" / "extraction_report.json"
SKIPPED_LOG = PROJECT_ROOT / "ml" / "training" / "skipped_images.txt"

os.makedirs(PROJECT_ROOT / "ml" / "training", exist_ok=True)

def extract_landmarks():
    options = HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=vision.RunningMode.IMAGE
    )

    classes = sorted(os.listdir(ASL_PATH))
    total_processed = 0
    total_success = 0
    total_skipped = 0
    class_counts = {}
    skipped_files = []

    print(f"Starting landmark extraction...")
    print(f"Classes: {len(classes)}")
    print(f"Output: {OUTPUT_CSV}\n")

    with HandLandmarker.create_from_options(options) as landmarker:
        with open(OUTPUT_CSV, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            # Header row
            header = []
            for i in range(21):
                header.extend([f"x{i}", f"y{i}", f"z{i}"])
            header.append("label")
            writer.writerow(header)

            for cls in classes:
                cls_path = ASL_PATH / cls
                images = os.listdir(cls_path)
                cls_success = 0

                print(f"Processing class: {cls} ({len(images)} images)...")

                for img_file in images:
                    img_path = str(cls_path / img_file)
                    total_processed += 1

                    try:
                        img = cv2.imread(img_path)
                        if img is None:
                            raise ValueError("Could not read image")

                        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        mp_image = mp.Image(
                            image_format=mp.ImageFormat.SRGB,
                            data=rgb
                        )

                        result = landmarker.detect(mp_image)

                        if result.hand_landmarks:
                            landmarks = result.hand_landmarks[0]
                            row = []
                            for lm in landmarks:
                                row.extend([
                                    round(lm.x, 4),
                                    round(lm.y, 4),
                                    round(lm.z, 4)
                                ])
                            row.append(cls)
                            writer.writerow(row)
                            total_success += 1
                            cls_success += 1
                        else:
                            total_skipped += 1
                            skipped_files.append(img_path)

                    except Exception as e:
                        total_skipped += 1
                        skipped_files.append(img_path)

                class_counts[cls] = cls_success
                print(f"  ✓ {cls}: {cls_success}/{len(images)} extracted")

    # Save skipped log
    with open(SKIPPED_LOG, 'w') as f:
        for path in skipped_files:
            f.write(path + "\n")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_processed": total_processed,
        "total_success": total_success,
        "total_skipped": total_skipped,
        "success_rate": f"{round((total_success/total_processed)*100, 2)}%",
        "num_classes": len(classes),
        "samples_per_class": class_counts
    }

    with open(REPORT_PATH, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "="*50)
    print("EXTRACTION COMPLETE")
    print("="*50)
    print(f"Total Processed  : {total_processed}")
    print(f"Successful       : {total_success}")
    print(f"Skipped          : {total_skipped}")
    print(f"Success Rate     : {report['success_rate']}")
    print(f"Classes          : {len(classes)}")
    print(f"CSV saved to     : {OUTPUT_CSV}")
    print(f"Report saved to  : {REPORT_PATH}")
    print(f"Skipped log      : {SKIPPED_LOG}")

if __name__ == "__main__":
    extract_landmarks()