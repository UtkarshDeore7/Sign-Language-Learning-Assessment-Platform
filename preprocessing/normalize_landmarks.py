import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV = PROJECT_ROOT / "ml" / "training" / "landmarks.csv"
OUTPUT_CSV = PROJECT_ROOT / "ml" / "training" / "normalized_landmarks.csv"

def normalize_landmarks(values):
    coords = values[:-1].astype(float)
    label = values[-1]

    landmarks = coords.reshape(21, 3)
    wrist = landmarks[0].copy()
    landmarks = landmarks - wrist

    distances = np.sqrt(np.sum(landmarks**2, axis=1))
    max_dist = np.max(distances)

    if max_dist > 0:
        landmarks = landmarks / max_dist

    normalized = landmarks.flatten()
    return list(normalized) + [label]

def run_normalization():
    try:
        print("Reading landmarks.csv...")
        df = pd.read_csv(INPUT_CSV)
        print(f"Total samples: {len(df)}")
        print("Normalizing landmarks...")

        normalized_rows = []
        for i, row in df.iterrows():
            if i % 5000 == 0:
                print(f"Processing row {i}...")
            normalized_rows.append(normalize_landmarks(row.values))

        cols = [f"{a}{i}" for i in range(21) for a in ['x','y','z']]
        cols.append("label")

        normalized_df = pd.DataFrame(normalized_rows, columns=cols)
        normalized_df.to_csv(OUTPUT_CSV, index=False)

        print(f"Done! Saved to: {OUTPUT_CSV}")
        print(f"Shape: {normalized_df.shape}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_normalization()