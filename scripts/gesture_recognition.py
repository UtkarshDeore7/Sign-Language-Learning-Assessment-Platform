import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions

MODEL_PATH = "ml/models/hand_landmarker.task"

def get_finger_states(hand_landmarks):
    """Returns which fingers are up (True) or down (False)"""
    fingers = []
    
    # Thumb
    fingers.append(hand_landmarks[4].x < hand_landmarks[3].x)
    
    # 4 fingers (index, middle, ring, pinky)
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    for tip, pip in zip(tips, pips):
        fingers.append(hand_landmarks[tip].y < hand_landmarks[pip].y)
    
    return fingers

def classify_gesture(fingers):
    """Classify gesture based on finger states"""
    if fingers == [False, False, False, False, False]:
        return "FIST"
    elif fingers == [False, True, True, True, True]:
        return "OPEN HAND"
    elif fingers == [False, True, False, False, False]:
        return "POINTING"
    elif fingers == [False, True, True, False, False]:
        return "PEACE / V"
    elif fingers == [True, True, True, True, True]:
        return "FIVE"
    elif fingers == [True, False, False, False, False]:
        return "THUMBS UP"
    elif fingers == [False, False, False, False, True]:
        return "PINKY UP"
    else:
        return "UNKNOWN"

def run_gesture_recognition():
    options = HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=vision.RunningMode.IMAGE
    )

    cap = cv2.VideoCapture(0)
    print("Gesture recognition started. Press Q to quit.")

    with HandLandmarker.create_from_options(options) as landmarker:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            result = landmarker.detect(mp_image)

            if result.hand_landmarks:
                h, w, _ = frame.shape
                for hand_landmarks in result.hand_landmarks:
                    # Draw landmarks
                    connections = [
                        (0,1),(1,2),(2,3),(3,4),
                        (0,5),(5,6),(6,7),(7,8),
                        (0,9),(9,10),(10,11),(11,12),
                        (0,13),(13,14),(14,15),(15,16),
                        (0,17),(17,18),(18,19),(19,20),
                        (5,9),(9,13),(13,17)
                    ]
                    for lm in hand_landmarks:
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                    for start, end in connections:
                        x1 = int(hand_landmarks[start].x * w)
                        y1 = int(hand_landmarks[start].y * h)
                        x2 = int(hand_landmarks[end].x * w)
                        y2 = int(hand_landmarks[end].y * h)
                        cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

                    # Classify gesture
                    fingers = get_finger_states(hand_landmarks)
                    gesture = classify_gesture(fingers)

                    # Display gesture
                    cv2.putText(frame, f"Gesture: {gesture}",
                               (10, 50), cv2.FONT_HERSHEY_SIMPLEX,
                               1, (255, 255, 0), 2)
                    print(f"Gesture: {gesture}")

            cv2.imshow("Gesture Recognition", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_gesture_recognition()