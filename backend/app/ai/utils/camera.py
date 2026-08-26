import cv2

class Camera:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("Failed to open camera. Check if webcam is connected.")
    
    def get_frame(self):
        success, frame = self.cap.read()
        if not success:
            return None
        return frame
    
    def release(self):
        self.cap.release()
        cv2.destroyAllWindows()


def run_webcam():
    cam = Camera()
    print("Webcam started. Press Q to quit.")

    while True:
        frame = cam.get_frame()
        if frame is None:
            print("Error: Could not read frame.")
            break

        cv2.imshow("Webcam Feed", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    print("Webcam closed.")


if __name__ == "__main__":
    run_webcam()