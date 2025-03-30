import cv2
import mediapipe as mp
import socketio
import time

# Initialize SocketIO Client
sio = socketio.Client()
sio.connect('http://127.0.0.1:9000')

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)

# Start Webcam
cap = cv2.VideoCapture(0)

previous_gesture = None
previous_emit_time = time.time()
confirm_start_time = None  # Track time for confirmation gesture

# Function to detect gestures
def detect_gesture(hand_landmarks):
    """Detects hand gestures for navigation & answer selection."""
    finger_tips = [8, 12, 16, 20]  # Index, Middle, Ring, Pinky fingertips
    thumb_tip = 4
    thumb_base = 2

    # Count raised fingers
    count = sum(1 for tip in finger_tips if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[tip - 2].y)
    thumb_open = hand_landmarks.landmark[thumb_tip].x < hand_landmarks.landmark[thumb_base].x
    if thumb_open:
        count += 1  # Count thumb if open

    # Gesture Mapping
    if count == 5:
        return "palm_open"  # Next Question
    elif count == 0:
        return "fist"  # Previous Question
    elif count == 1:
        return "one_finger"  # Select Option 1
    elif count == 2:
        return "two_fingers"  # Select Option 2
    elif count == 3:
        return "three_fingers"  # Select Option 3
    elif count == 4:  # OK Gesture (Thumb + Index touching)
        return "confirm"
    elif count == 5:  # Keep hand open for cancel
        return "cancel"
    else:
        return None

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("❌ Error: Could not read frame from webcam.")
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Detect Hand Gesture
            gesture = detect_gesture(hand_landmarks)

            # Check for confirmation gesture (holding open hand for 2 sec)
            if gesture == "cancel":
                if confirm_start_time is None:
                    confirm_start_time = time.time()
                elif time.time() - confirm_start_time > 2:
                    print("❌ Answer Cancelled!")
                    sio.emit('cancel_answer')
                    confirm_start_time = None  # Reset timer
            else:
                confirm_start_time = None  # Reset if hand is moved

            # Emit gesture only if it has changed
            if gesture and gesture != previous_gesture and (time.time() - previous_emit_time) > 1:
                print(f"📡 Sending Gesture: {gesture}")
                sio.emit('gesture_detected', {'gesture': gesture})
                previous_gesture = gesture
                previous_emit_time = time.time()

    # Display Webcam Feed
    cv2.imshow("Hand Gesture Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
