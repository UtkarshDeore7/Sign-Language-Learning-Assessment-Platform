# Experiment 001 — Baseline Random Forest

## Objective
Train a baseline Random Forest classifier on normalized ASL landmark data.

## Dataset
- Source: ASL Alphabet Dataset (Kaggle)
- Total images: 87,000
- Successful extractions: 63,580 (73% success rate)
- Features: 63 (21 landmarks x 3 coordinates)
- Classes: 28 ASL signs
- Split: 70% train / 15% validation / 15% test (stratified)

## Normalization Strategy
Wrist-relative coordinates scaled by maximum hand distance.
- Subtract wrist (landmark 0) from all 21 landmarks
- Scale by max distance from wrist to any landmark
- Makes model invariant to hand position and size in frame

## Model
Random Forest with 100 estimators, random_state=42

## Results
- Validation Accuracy: 98.64%
- Validation F1 Score: 98.64%
- Training Time: 65.46 seconds
- Inference Time: 4.94ms average
- Throughput: 202 predictions/second
- Model Size: 72MB

## Hyperparameter Study
| Trees | Accuracy | Training Time |
|-------|---------|--------------|
| 50 | 98.55% | 21s |
| 100 | 98.64% | 73s |
| 200 | 98.65% | 146s |

**Conclusion:** 100 trees is optimal. 200 trees gains only 0.01% but doubles training time.

## Error Analysis
Most confused pairs:
- N → M: 17 times (similar finger positions)
- M → N: 4 times
- O → D: 4 times (similar curved shapes)
- D → O: 3 times
- E → S: 3 times (similar curled fingers)

Worst performing class: N (F1=0.93) — still excellent.

## Benchmark
- Average inference: 4.94ms
- Real-time threshold: 33ms (30 FPS)
- Status: ✅ Suitable for real-time webcam recognition

## Next Steps
- Connect live webcam to predict endpoint
- Implement LSTM/GRU for continuous sign recognition
- Build React frontend
- Deploy with Docker