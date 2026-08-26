import os
import json
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASL_PATH = PROJECT_ROOT / "ml" / "datasets" / "asl-alphabet" / "asl_alphabet_train" / "asl_alphabet_train"
WLASL_JSON = PROJECT_ROOT / "ml" / "datasets" / "wlasl" / "wlasl-complete" / "WLASL_v0.3.json"
CSV_OUTPUT = PROJECT_ROOT / "scripts" / "asl_dataset_report.csv"

def explore_asl():
    print("=" * 50)
    print("ASL ALPHABET DATASET")
    print("=" * 50)

    classes = sorted(os.listdir(ASL_PATH))
    total_images = 0
    class_counts = {}

    for cls in classes:
        count = len(os.listdir(ASL_PATH / cls))
        class_counts[cls] = count
        total_images += count

    largest_class = max(class_counts, key=class_counts.get)
    smallest_class = min(class_counts, key=class_counts.get)

    print(f"Total Classes: {len(classes)}")
    print(f"Total Images: {total_images}")
    print(f"Images per class: {list(class_counts.values())[0]}")
    print(f"Largest Class: {largest_class} ({class_counts[largest_class]} images)")
    print(f"Smallest Class: {smallest_class} ({class_counts[smallest_class]} images)")

    # Export to CSV
    with open(CSV_OUTPUT, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Class", "Image Count", "Percentage"])
        for cls, count in class_counts.items():
            percentage = round((count / total_images) * 100, 2)
            writer.writerow([cls, count, f"{percentage}%"])
        writer.writerow(["TOTAL", total_images, "100%"])

    print(f"\nCSV exported to: {CSV_OUTPUT}")
    return class_counts

def explore_wlasl():
    print("\n" + "=" * 50)
    print("WLASL DATASET")
    print("=" * 50)

    with open(WLASL_JSON, "r") as f:
        data = json.load(f)

    print(f"Annotation File: {WLASL_JSON}")
    print(f"Unique Signs: {len(data)}")
    print("\n5 Sample Entries:")
    for entry in data[:5]:
        print(f"  Sign: {entry['gloss']} | Instances: {len(entry['instances'])}")

if __name__ == "__main__":
    explore_asl()
    explore_wlasl()