from flask import Flask, request, jsonify, send_from_directory
import os
import socket
import time
import threading
import firebase_admin
from firebase_admin import credentials, db
from pynput import keyboard, mouse
import subprocess
import requests

# Initialize Firebase Admin SDK with credentials
cred = credentials.Certificate("mycroft-discord-bot-firebase-adminsdk-j8svf-c54e12e978.json")
firebase_admin.initialize_app(cred, {
    'apiKey': "AIzaSyBV7r0uBwLocb5YpD5AQgAU73DkNkC00rw",
    'authDomain': "mycroft-discord-bot.firebaseapp.com",
    'databaseURL': "https://mycroft-discord-bot-default-rtdb.europe-west1.firebasedatabase.app",
    'projectId': "mycroft-discord-bot",
    'storageBucket': "mycroft-discord-bot.appspot.com",
    'messagingSenderId': "1057247781531",
    'appId': "1:1057247781531:web:64463428543ed092625c3e",
    'measurementId': "G-6X8CBBJPHJ"
})

app = Flask(__name__)

# Token for basic authentication
AUTH_TOKEN = os.environ.get('AUTH_TOKEN')  # Replace 'your_default_token' with your preferred token

class RealtimeDB:
    def __init__(self):
        self.db = db.reference()

    # Write data to Realtime Database
    def write_data(self, path, data):
        try:
            ref = self.db.child(path)
            ref.set(data)
            print(f'Data written to Realtime Database at path: {path}')
        except Exception as e:
            print(f'Error writing to Realtime Database: {e}')

def update_active_device(device_name):
    db_instance = RealtimeDB()
    db_instance.write_data('active_device', device_name)

def update_public_url(device_name, public_url):
    db_instance = RealtimeDB()
    db_instance.write_data(f'devices/{device_name}/public_url', public_url)

def on_activity(activity_type):
    global last_activity_time, device_name, activity_detected
    last_activity_time = time.time()
    activity_detected = True
    print(f'Activity detected: {activity_type}')

def monitor_activity():
    global last_activity_time, device_name, activity_detected
    last_activity_time = time.time()
    activity_detected = False

    # Set up keyboard listener
    keyboard_listener = keyboard.Listener(on_press=lambda key: on_activity('keyboard'))
    keyboard_listener.start()

    # Set up mouse listener
    mouse_listener = mouse.Listener(
        on_move=lambda x, y: on_activity('mouse_move'),
        on_click=lambda x, y, button, pressed: on_activity('mouse_click'),
        on_scroll=lambda x, y, dx, dy: on_activity('mouse_scroll')
    )
    mouse_listener.start()

    device_name = socket.gethostname()

    while True:
        current_time = time.time()
        if activity_detected and (current_time - last_activity_time) < 5:
            update_active_device(device_name)
            activity_detected = False
        time.sleep(2)

@app.route('/')
def home():
    return "Hello, World!"

def authenticate_request():
    token = request.headers.get('Authorization') or request.json.get('token')
    if token != AUTH_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    return None

@app.route('/send_command', methods=['POST'])
def send_command():
    auth_response = authenticate_request()
    if auth_response:
        return auth_response

    command = request.json.get('command')
    # Execute the command here
    print(f'Received command: {command}')
    return jsonify({'status': 'Command received'})

@app.route('/upload_file', methods=['POST'])
def upload_file():
    auth_response = authenticate_request()
    if auth_response:
        return auth_response

    file = request.files['file']
    file.save(f'./{file.filename}')
    print(f'Received file: {file.filename}')
    return jsonify({'status': 'File received'})

@app.route('/download_file', methods=['GET'])
def download_file():
    auth_response = authenticate_request()
    if auth_response:
        return auth_response

    filename = request.args.get('filename')
    return send_from_directory(directory='.', path=filename)

if __name__ == '__main__':
    # Start Localtunnel
    lt_path = r'C:\Users\kalin\AppData\Roaming\npm\lt.cmd'  # Replace with the actual path to lt
    lt_process = subprocess.Popen([lt_path, '--port', '5000'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)  # Give Localtunnel some time to establish the connection

    # Read the public URL from Localtunnel output
    public_url = None
    while True:
        output = lt_process.stdout.readline().decode('utf-8').strip()
        if 'your url is:' in output:
            public_url = output.split(' ')[-1]
            break

    if public_url:
        print(f"Ingress established at {public_url}")
        
        # Update the public URL in Firebase
        device_name = socket.gethostname()
        update_public_url(device_name, public_url)

        # Run the monitor_activity function in a separate thread
        threading.Thread(target=monitor_activity).start()

        # Run Flask application
        app.run(port=5000)
    else:
        print("Failed to establish Localtunnel connection")