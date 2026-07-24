from sklearn.neighbors import KNeighborsClassifier
import pandas as pd
import numpy as np
import json
import pickle
import time
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRAIN_CSV = PROJECT_ROOT / "ml" / "training" / "train.csv"
VAL_CSV = PROJECT_ROOT / "ml" / "training" / "validation.csv"
EXPERIMENT_DIR = Path(__file__).resolve().parent
MODEL_DIR = PROJECT_ROOT / "ml" / "models"

def train_and_evaluate():
    print("Loading data...")
    train_df = pd.read_csv(TRAIN_CSV)
    val_df = pd.read_csv(VAL_CSV)

    X_train = train_df.drop("label", axis=1).values
    y_train = train_df["label"].values
    X_val = val_df.drop("label", axis=1).values
    y_val = val_df["label"].values

    classifiers = {
    "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
    "DecisionTree": DecisionTreeClassifier(random_state=42),
    "KNN": KNeighborsClassifier(n_neighbors=5)
}

    results = []
    best_model = None
    best_accuracy = 0
    best_name = ""

    for name, clf in classifiers.items():
        print(f"\nTraining {name}...")
        start = time.time()
        clf.fit(X_train, y_train)
        train_time = round(time.time() - start, 2)

        y_pred = clf.predict(X_val)
        accuracy = round(accuracy_score(y_val, y_pred), 4)
        precision = round(precision_score(y_val, y_pred, average='weighted', zero_division=0), 4)
        recall = round(recall_score(y_val, y_pred, average='weighted', zero_division=0), 4)
        f1 = round(f1_score(y_val, y_pred, average='weighted', zero_division=0), 4)

        print(f"  Training Time: {train_time}s")
        print(f"  Accuracy: {accuracy}")
        print(f"  F1 Score: {f1}")

        results.append({
            "Algorithm": name,
            "Training Time": train_time,
            "Accuracy": accuracy,
            "Precision": precision,
            "Recall": recall,
            "F1 Score": f1
        })

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_model = clf
            best_name = name

    # Save comparison report
    comparison_df = pd.DataFrame(results)
    comparison_df.to_csv(EXPERIMENT_DIR / "comparison_report.csv", index=False)
    print(f"\nComparison report saved.")

    # Save best model
    model_path = MODEL_DIR / "gesture_classifier.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(best_model, f)
    print(f"Best model: {best_name} (accuracy={best_accuracy})")
    print(f"Model saved to: {model_path}")

    # Save results
    results_data = {
        "best_model": best_name,
        "best_accuracy": best_accuracy,
        "comparison": results
    }
    with open(EXPERIMENT_DIR / "results.json", 'w') as f:
        json.dump(results_data, f, indent=2)

    print("\nDone!")

if __name__ == "__main__":
    train_and_evaluate()