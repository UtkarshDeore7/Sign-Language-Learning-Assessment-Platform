import cv2
import sys
from pathlib import Path

def load_and_display_image(image_path: str):
    img = cv2.imread(image_path)

    if img is None:
        print(f"Error: Could not read image at {image_path}")
        return

    height, width, channels = img.shape

    print(f"Height: {height}")
    print(f"Width: {width}")
    print(f"Channels: {channels}")
    print(f"Image Size: {height * width * channels} bytes")

    cv2.imshow("Image Loader", img)
    print("Press any key to close the image window...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default to first image in ASL dataset if no path given
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        asl_path = PROJECT_ROOT / "ml" / "datasets" / "asl-alphabet" / "asl_alphabet_train" / "asl_alphabet_train" / "A"
        first_image = list(asl_path.iterdir())[0]
        image_path = str(first_image)
        print(f"No path given. Using default: {image_path}")
    else:
        image_path = sys.argv[1]

    load_and_display_image(image_path)