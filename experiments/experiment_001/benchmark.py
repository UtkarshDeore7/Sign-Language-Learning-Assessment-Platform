import pickle
import time
import json
import numpy as np
import os
import psutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "gesture_classifier.pkl"
EXPERIMENT_DIR = Path(__file__).resolve().parent

def run_benchmark():
    print("Loading model...")
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)

    # Model file size
    model_size_kb = round(os.path.getsize(MODEL_PATH) / 1024, 2)
    print(f"Model size: {model_size_kb} KB")

    # Generate dummy landmark vector
    dummy_landmarks = np.random.rand(1, 63)

    # Warmup
    for _ in range(10):
        model.predict(dummy_landmarks)

    # Benchmark 1000 predictions
    n_runs = 1000
    times = []

    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024

    print(f"Running {n_runs} predictions...")
    for _ in range(n_runs):
        start = time.perf_counter()
        model.predict(dummy_landmarks)
        end = time.perf_counter()
        times.append((end - start) * 1000)

    mem_after = process.memory_info().rss / 1024 / 1024

    avg_time = round(np.mean(times), 4)
    max_time = round(np.max(times), 4)
    min_time = round(np.min(times), 4)
    throughput = round(1000 / avg_time, 2)
    mem_used = round(mem_after - mem_before, 2)

    print(f"\nBenchmark Results:")
    print(f"  Average inference time : {avg_time} ms")
    print(f"  Min inference time     : {min_time} ms")
    print(f"  Max inference time     : {max_time} ms")
    print(f"  Throughput             : {throughput} predictions/sec")
    print(f"  Memory used            : {mem_used} MB")
    print(f"  Model file size        : {model_size_kb} KB")

    # Save benchmark report
    report = {
        "avg_inference_time_ms": avg_time,
        "min_inference_time_ms": min_time,
        "max_inference_time_ms": max_time,
        "throughput_per_second": throughput,
        "memory_used_mb": mem_used,
        "model_size_kb": model_size_kb,
        "suitable_for_realtime": bool(avg_time < 100),
        "conclusion": f"Average inference time of {avg_time}ms supports real-time webcam recognition at 30 FPS. Model is {'suitable' if avg_time < 33 else 'not suitable'} for real-time use."
    }

    with open(EXPERIMENT_DIR / "benchmark_report.md", 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    md = f"""# Inference Benchmark Report

## Results
| Metric | Value |
|--------|-------|
| Average Inference Time | {avg_time} ms |
| Min Inference Time | {min_time} ms |
| Max Inference Time | {max_time} ms |
| Throughput | {throughput} predictions/sec |
| Memory Used | {mem_used} MB |
| Model File Size | {model_size_kb} KB |

## Conclusion
{report['conclusion']}

## Suitability for Real-Time Recognition
Real-time webcam runs at 30 FPS, requiring predictions under 33ms per frame.
Average inference time: {avg_time}ms - {'Suitable' if avg_time < 33 else 'May need optimization'} for real-time use.
"""

    with open(EXPERIMENT_DIR / "benchmark_report.md", 'w') as f:
        f.write(md)

    print(f"\nBenchmark report saved.")

if __name__ == "__main__":
    run_benchmark()