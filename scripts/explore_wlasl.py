import os
import json

BASE_PATH = "ml/datasets/wlasl/wlasl-complete"
JSON_PATH = os.path.join(BASE_PATH, "WLASL_v0.3.json")
VIDEO_PATH = os.path.join(BASE_PATH, "videos")

with open(JSON_PATH, "r") as f:
    data = json.load(f)

print(f"1. Total words/classes: {len(data)}")

total_videos = 0
signers = set()
durations = []

for entry in data[:50]:
    word = entry["gloss"]
    instances = entry["instances"]
    total_videos += len(instances)
    for inst in instances:
        signers.add(inst.get("signer_id", "unknown"))

print(f"2. Sample words: {[d['gloss'] for d in data[:10]]}")
print(f"3. Total video instances (first 50 words): {total_videos}")
print(f"4. Unique signers (first 50 words): {len(signers)}")
print(f"5. Label format: JSON gloss field = word label")
print(f"6. Video format: MP4")
print(f"7. Metadata available: signer_id, bbox, fps, frame_start, frame_end, split")
print(f"8. Dataset subsets available: 100, 300, 1000, 2000 words")

# Sample instance structure
print(f"\n9. Sample instance structure:")
print(json.dumps(data[0]["instances"][0], indent=2))