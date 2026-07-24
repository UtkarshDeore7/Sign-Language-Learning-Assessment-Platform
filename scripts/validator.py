import json
import csv
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "ml" / "training" / "landmarks.csv"
REPORT_PATH = PROJECT_ROOT / "ml" / "training" / "dataset_report.json"

def validate_dataset():
    print("Validating dataset...")

    total = 0
    successful = 0
    failed = 0
    corrupted = 0
    class_counts = {}

    with open(CSV_PATH, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)  # skip header

        for row in reader:
            total += 1
            try:
                label = row[-1]
                values = row[:-1]

                # Check if all 63 values are valid numbers
                floats = [float(v) for v in values]

                if len(floats) != 63:
                    corrupted += 1
                    continue

                successful += 1
                class_counts[label] = class_counts.get(label, 0) + 1

            except Exception:
                corrupted += 1

    failed = total - successful - corrupted
    success_rate = round((successful / total) * 100, 2) if total > 0 else 0

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_samples": total,
        "successful": successful,
        "failed": failed,
        "corrupted": corrupted,
        "success_percentage": f"{success_rate}%",
        "num_classes": len(class_counts),
        "samples_per_class": class_counts
    }

    with open(REPORT_PATH, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Total Samples    : {total}")
    print(f"Successful       : {successful}")
    print(f"Failed           : {failed}")
    print(f"Corrupted        : {corrupted}")
    print(f"Success Rate     : {success_rate}%")
    print(f"Classes          : {len(class_counts)}")
    print(f"Report saved to  : {REPORT_PATH}")

    return report

if __name__ == "__main__":
    validate_dataset()