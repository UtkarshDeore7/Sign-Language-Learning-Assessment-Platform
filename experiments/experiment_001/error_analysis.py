import pandas as pd
import numpy as np
import json
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, classification_report
import pickle

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_CSV = PROJECT_ROOT / "ml" / "training" / "test.csv"
MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "gesture_classifier.pkl"
EXPERIMENT_DIR = Path(__file__).resolve().parent

def run_error_analysis():
    print("Loading test data and model...")
    test_df = pd.read_csv(TEST_CSV)
    X_test = test_df.drop("label", axis=1).values
    y_test = test_df["label"].values

    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)

    y_pred = model.predict(X_test)

    # Confusion matrix
    classes = sorted(list(set(y_test)))
    cm = confusion_matrix(y_test, y_pred, labels=classes)

    # Find top 5 most confused pairs
    confused_pairs = []
    for i, true_class in enumerate(classes):
        for j, pred_class in enumerate(classes):
            if i != j and cm[i][j] > 0:
                confused_pairs.append({
                    "true": true_class,
                    "predicted": pred_class,
                    "count": int(cm[i][j])
                })

    confused_pairs = sorted(confused_pairs, key=lambda x: x["count"], reverse=True)[:5]

    print("\nTop 5 Most Confused Gesture Pairs:")
    for pair in confused_pairs:
        print(f"  {pair['true']} → {pair['predicted']}: {pair['count']} times")

    # Classification report
    report = classification_report(y_test, y_pred, output_dict=True)

    # Find worst performing classes
    class_f1 = {cls: report[cls]['f1-score'] for cls in classes if cls in report}
    worst_classes = sorted(class_f1.items(), key=lambda x: x[1])[:5]

    print("\nWorst Performing Classes:")
    for cls, f1 in worst_classes:
        print(f"  {cls}: F1={round(f1, 4)}")

    # Save analysis
    analysis = {
        "top_confused_pairs": confused_pairs,
        "worst_performing_classes": [
            {"class": cls, "f1_score": round(f1, 4)} 
            for cls, f1 in worst_classes
        ],
        "possible_reasons": [
            "Similar finger positions between certain letters",
            "Background noise in dataset images",
            "Lighting variations affecting landmark detection",
            "Occlusion of certain fingers in similar poses"
        ]
    }

    with open(EXPERIMENT_DIR / "error_analysis.json", 'w') as f:
        json.dump(analysis, f, indent=2)

    # Save markdown report
    md_content = f"""# Error Analysis Report

## Top 5 Most Confused Gesture Pairs
| True Label | Predicted | Count |
|-----------|-----------|-------|
"""
    for pair in confused_pairs:
        md_content += f"| {pair['true']} | {pair['predicted']} | {pair['count']} |\n"

    md_content += f"""
## Worst Performing Classes
| Class | F1 Score |
|-------|---------|
"""
    for cls, f1 in worst_classes:
        md_content += f"| {cls} | {round(f1, 4)} |\n"

    md_content += """
## Possible Reasons for Confusion
- Similar finger positions between certain letters
- Background noise in dataset images  
- Lighting variations affecting landmark detection
- Occlusion of certain fingers in similar poses
"""

    with open(EXPERIMENT_DIR / "error_analysis.md", 'w') as f:
        f.write(md_content)

    print("\nError analysis saved to error_analysis.json and error_analysis.md")

if __name__ == "__main__":
    run_error_analysis()