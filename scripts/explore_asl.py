import os
from PIL import Image

DATASET_PATH = "ml/datasets/asl-alphabet/asl_alphabet_train/asl_alphabet_train"

classes = sorted(os.listdir(DATASET_PATH))
print(f"1. Number of classes: {len(classes)}")
print(f"2. Classes (each = one hand sign): {classes}")

counts = []
for cls in classes:
    count = len(os.listdir(os.path.join(DATASET_PATH, cls)))
    counts.append(count)
    print(f"   {cls}: {count} images")

print(f"\n3. Images per class: min={min(counts)}, max={max(counts)}")
print(f"4. Dataset balanced: {len(set(counts)) == 1}")

# Check resolution of first image
first_class = classes[0]
first_image_path = os.path.join(DATASET_PATH, first_class, 
                   os.listdir(os.path.join(DATASET_PATH, first_class))[0])
img = Image.open(first_image_path)
print(f"\n5. Image resolution: {img.size}")
print(f"6. Image format: {img.format}")
print(f"7. Image mode: {img.mode}")
print(f"\n8. Total images: {sum(counts)}")
print(f"9. Label format: folder name = label")
print(f"10. Directory structure: datasets/asl-alphabet/asl_alphabet_train/asl_alphabet_train/<label>/<image>")