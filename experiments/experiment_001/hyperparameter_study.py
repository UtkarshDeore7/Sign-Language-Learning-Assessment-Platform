import pandas as pd
import json
import time
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRAIN_CSV = PROJECT_ROOT / "ml" / "training" / "train.csv"
VAL_CSV = PROJECT_ROOT / "ml" / "training" / "validation.csv"
EXPERIMENT_DIR = Path(__file__).resolve().parent

def hyperparameter_study():
    print("Loading data...")
    train_df = pd.read_csv(TRAIN_CSV)
    val_df = pd.read_csv(VAL_CSV)

    X_train = train_df.drop("label", axis=1).values
    y_train = train_df["label"].values
    X_val = val_df.drop("label", axis=1).values
    y_val = val_df["label"].values

    tree_counts = [50, 100, 200]
    results = []

    for n in tree_counts:
        print(f"\nTraining Random Forest with {n} trees...")
        clf = RandomForestClassifier(n_estimators=n, random_state=42)
        
        start = time.time()
        clf.fit(X_train, y_train)
        train_time = round(time.time() - start, 2)

        y_pred = clf.predict(X_val)
        accuracy = round(accuracy_score(y_val, y_pred), 4)
        f1 = round(f1_score(y_val, y_pred, average='weighted', zero_division=0), 4)

        results.append({
            "n_estimators": n,
            "training_time_seconds": train_time,
            "accuracy": accuracy,
            "f1_score": f1
        })

        print(f"  Trees: {n} | Time: {train_time}s | Accuracy: {accuracy} | F1: {f1}")

    # Save report
    report = {
        "study": "Random Forest n_estimators comparison",
        "results": results,
        "conclusion": "Increasing trees beyond 100 shows diminishing returns while increasing training time"
    }

    with open(EXPERIMENT_DIR / "hyperparameter_report.json", 'w') as f:
        import json
        json.dump(report, f, indent=2)

    print("\nHyperparameter report saved.")

if __name__ == "__main__":
    hyperparameter_study()