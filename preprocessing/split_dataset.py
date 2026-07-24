import pandas as pd
import json
from pathlib import Path
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV = PROJECT_ROOT / "ml" / "training" / "normalized_landmarks.csv"
TRAIN_CSV = PROJECT_ROOT / "ml" / "training" / "train.csv"
VAL_CSV = PROJECT_ROOT / "ml" / "training" / "validation.csv"
TEST_CSV = PROJECT_ROOT / "ml" / "training" / "test.csv"
REPORT_PATH = PROJECT_ROOT / "ml" / "training" / "training_report.json"

def split_dataset():
    print("Reading normalized_landmarks.csv...")
    df = pd.read_csv(INPUT_CSV)

    class_counts = df["label"].value_counts()
    valid_classes = class_counts[class_counts >= 2].index
    df = df[df["label"].isin(valid_classes)]
    print(f"Total samples after filtering: {len(df)}")

    X = df.drop("label", axis=1)
    y = df["label"]

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.3, stratify=y, random_state=42
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=42
    )

    train_df = pd.concat([X_train, y_train], axis=1)
    val_df = pd.concat([X_val, y_val], axis=1)
    test_df = pd.concat([X_test, y_test], axis=1)

    train_df.to_csv(TRAIN_CSV, index=False)
    val_df.to_csv(VAL_CSV, index=False)
    test_df.to_csv(TEST_CSV, index=False)

    print(f"Train: {len(train_df)} samples")
    print(f"Validation: {len(val_df)} samples")
    print(f"Test: {len(test_df)} samples")

    print("\nClass distribution verification:")
    for cls in sorted(y.unique()):
        t = len(train_df[train_df["label"] == cls])
        v = len(val_df[val_df["label"] == cls])
        te = len(test_df[test_df["label"] == cls])
        print(f"  {cls}: train={t}, val={v}, test={te}")

    report = {
        "total_samples": len(df),
        "num_classes": int(y.nunique()),
        "num_features": int(X.shape[1]),
        "samples_per_class": y.value_counts().to_dict(),
        "train_size": len(train_df),
        "validation_size": len(val_df),
        "test_size": len(test_df),
        "failed_extractions": 87000 - len(df),
        "split_strategy": "Stratified 70/15/15"
    }

    with open(REPORT_PATH, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nTraining report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    split_dataset()