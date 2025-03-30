import threading
import subprocess
from flask import Flask
from flask_socketio import SocketIO

# Flask & SocketIO Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Quiz Questions
questions = [
    "What is the core of a wand made of?",
    "Who was the Half-Blood Prince?",
    "What is the name of Harry Potter’s owl?"
]
current_question_index = 0
selected_option = None

def start_hand_tracking():
    """Start hand tracking."""
    subprocess.Popen(["python", "hand_tracking.py"])

@socketio.on('connect')
def handle_connect():
    print("✅ Client Connected!")

@socketio.on('gesture_detected')
def handle_gesture(data):
    """Handles gestures for navigation, answer selection, and confirmation."""
    global current_question_index, selected_option
    gesture = data['gesture']
    print(f"📡 Received Gesture: {gesture}")

    # 🔹 Next Question (Palm Open)
    if gesture == "palm_open" and current_question_index < len(questions) - 1:
        current_question_index += 1
        print(f"➡️ Moving to Next Question: {questions[current_question_index]}")
        socketio.emit('update_question', {'question': questions[current_question_index]})

    # 🔹 Previous Question (Fist)
    elif gesture == "fist" and current_question_index > 0:
        current_question_index -= 1
        print(f"⬅️ Moving to Previous Question: {questions[current_question_index]}")
        socketio.emit('update_question', {'question': questions[current_question_index]})

    # 🔹 Answer Selection (One, Two, or Three Fingers)
    elif gesture in ["one_finger", "two_fingers", "three_fingers"]:
        option_mapping = {"one_finger": 1, "two_fingers": 2, "three_fingers": 3}
        selected_option = option_mapping.get(gesture, None)

        if selected_option:
            print(f"✅ Selected Option: {selected_option}")
            socketio.emit('answer_selected', {'answer': selected_option})

    # 🔹 Confirm Answer (OK Sign)
    elif gesture == "ok_sign":
        if selected_option is not None:
            print(f"✅ Confirming Answer: {selected_option}")
            socketio.emit('confirm_answer', {'selected_option': selected_option})
        else:
            print("⚠️ No Option Selected. Cannot Confirm.")

    # ❌ Cancel Answer (Thumbs Down)
    elif gesture == "thumbs_down":
        print("❌ Answer Cancelled!")
        selected_option = None
        socketio.emit('cancel_answer')

if __name__ == '__main__':
    threading.Thread(target=start_hand_tracking, daemon=True).start()
    socketio.run(app, debug=True, host="127.0.0.1", port=9000)
