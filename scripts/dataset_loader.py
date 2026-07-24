import os

DATASET_PATH = os.path.join(os.path.dirname(__file__), 
               "datasets/asl-alphabet/asl_alphabet_train/asl_alphabet_train")

def get_dataset_info():
    classes = sorted(os.listdir(DATASET_PATH))
    total_images = 0
    class_counts = {}
    
    for cls in classes:
        cls_path = os.path.join(DATASET_PATH, cls)
        count = len(os.listdir(cls_path))
        class_counts[cls] = count
        total_images += count
    
    return {
        "total_classes": len(classes),
        "classes": classes,
        "total_images": total_images,
        "class_counts": class_counts
    }

if __name__ == "__main__":
    info = get_dataset_info()
    print(f"Total Classes: {info['total_classes']}")
    print(f"Total Images: {info['total_images']}")
    print(f"Classes: {info['classes']}")