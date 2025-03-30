import cv2
import mediapipe as mp
import socketio
import time
import numpy as np

# Initialize SocketIO client
sio = socketio.Client()

def connect_to_socket():
    """Ensure connection is established before sending events."""
    while True:
        try:
            sio.connect('http://127.0.0.1:9000')
            print("✅ Face Module Connected to Server")
            break
        except Exception as e:
            print(f"🔄 Retrying Face Module Connection... {e}")
            time.sleep(2)

connect_to_socket()

# Initialize MediaPipe Face Mesh module
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.8, min_tracking_confidence=0.8)

# Start webcam
cap = cv2.VideoCapture(0)

# Track head movements
previous_y = None
previous_x = None
y_movements = []
x_movements = []
BUFFER_SIZE = 5  # Smoothens detection

last_nod_time = 0  # Time of last nod detection
NOD_DELAY = 2  # Min seconds between nod confirmations

def detect_head_movement(face_landmarks):
    """Detects head nods (downward movement for confirmation) and shakes (left-right for cancel)."""
    global previous_x, previous_y, y_movements, x_movements, last_nod_time

    nose_tip = face_landmarks.landmark[1]  # Nose tip landmark
    forehead = face_landmarks.landmark[10]  # Forehead landmark
    chin = face_landmarks.landmark[152]  # Chin landmark

    # Get Y position changes (Vertical for nods)
    y_nose = nose_tip.y
    y_forehead = forehead.y
    y_chin = chin.y

    # Get X position changes (Horizontal for shakes)
    x_nose = nose_tip.x

    # Store recent movements
    y_movements.append(y_nose)
    x_movements.append(x_nose)

    # Keep only last N values for smoothing
    if len(y_movements) > BUFFER_SIZE:
        y_movements.pop(0)
    if len(x_movements) > BUFFER_SIZE:
        x_movements.pop(0)

    # Compute movement averages
    avg_y_movement = np.mean(y_movements)
    avg_x_movement = np.mean(x_movements)

    if previous_y is not None:
        # Detect **nodding (head moves down)**
        if avg_y_movement - previous_y > 0.05 and (time.time() - last_nod_time) > NOD_DELAY:
            print("✅ Head Nod Detected → Confirming Answer")
            sio.emit('confirm_answer')
            last_nod_time = time.time()  # Update last nod detection time

        # Detect **shaking (head moves left-right)**
        elif abs(avg_x_movement - previous_x) > 0.05:
            print("❌ Head Shake Detected → Cancelling Selection")
            sio.emit('cancel_answer')

    previous_y = avg_y_movement
    previous_x = avg_x_movement

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("❌ Error: Could not read frame from webcam for face.")
        break

    frame = cv2.flip(frame, 1)  # Flip for mirror effect
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            detect_head_movement(face_landmarks)

    cv2.imshow("Head Movement Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
