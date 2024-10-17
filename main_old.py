import os
import re
import threading
import json
import time
import socket
import subprocess
import requests
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, jsonify, send_from_directory
from pynput import keyboard, mouse
import pyautogui  # For taking screenshots
import platform
import warnings
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

encryption_key_cli = os.environ.get('ENCRYPTION_KEY_CLI').encode()
encryption_key_config = os.environ.get('ENCRYPTION_KEY_CONFIG').encode()
encryption_key_adminsdk = os.environ.get('ENCRYPTION_KEY_ADMINSDK').encode()

def decrypt_client_secret():
    print("Starting decryption of client_secret.json.encrypted")
    with open("service_account.json.encrypted", "rb") as encrypted_file:
        encrypted_data = encrypted_file.read()

    fernet = Fernet(encryption_key_cli)
    decrypted_data = fernet.decrypt(encrypted_data)

    with open("service_account.json", "wb") as decrypted_file:
        decrypted_file.write(decrypted_data)

def decrypt_firebase_config():
    with open("firebase_config.json.encrypted", "rb") as encrypted_file:
        encrypted_data = encrypted_file.read()

    fernet = Fernet(encryption_key_config)
    decrypted_data = fernet.decrypt(encrypted_data)

    with open("firebase_config.json", "wb") as decrypted_file:
        decrypted_file.write(decrypted_data)

def decrypt_adminsdk():
    print("Starting decryption of client_secret.json.encrypted")
    with open("firebase_adminsdk.json.encrypted", "rb") as encrypted_file:
        encrypted_data = encrypted_file.read()

    fernet = Fernet(encryption_key_adminsdk)
    decrypted_data = fernet.decrypt(encrypted_data)

    with open("firebase_adminsdk.json", "wb") as decrypted_file:
        decrypted_file.write(decrypted_data)

decrypt_client_secret()
decrypt_firebase_config()
decrypt_adminsdk()



# Load Firebase configuration from JSON file
with open('firebase_config.json') as config_file:
    firebase_config = json.load(config_file)

cred = credentials.Certificate("firebase_adminsdk.json")
firebase_admin.initialize_app(cred, firebase_config)

app = Flask(__name__)

@app.route('/')
def home():
    return "Server running"

# Firebase Realtime Database interaction
class RealtimeDB:
    def __init__(self):
        self.db = db.reference()

    def write_data(self, path, data):
        try:
            ref = self.db.child(path)
            ref.set(data)
            print(f'Data written to Firebase: {path}')
        except Exception as e:
            print(f'Error writing to Firebase: {e}')

def update_public_url(device_name, public_url):
    db_instance = RealtimeDB()
    db_instance.write_data(f'devices/{device_name}/public_url', public_url)

def update_active_device(device_name):
    db_instance = RealtimeDB()
    db_instance.write_data('active_device', device_name)

# Token for basic authentication
AUTH_TOKEN = os.environ.get('AUTH_TOKEN', 'Denemeler123.')  # Replace with your actual token

def authenticate_request():
    token = request.headers.get('Authorization') or request.json.get('token')
    if token != AUTH_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    return None

# Predefined apps that can be opened via the "start" command
APP_COMMANDS = {
    "Spotify": "start spotify:",
    "WhatsApp": "start whatsapp:",
    "Onenote": "start OneNote:",
    "Opera": "start Opera Browser:",
    "Discord": "start discord:",
    "Epic Games": "start epicgameslauncher:",
    "Steam": "start steam:",
    "Elden Ring": "start steam://rungameid/1245620"  # Example Steam game ID for Elden Ring
}

# Helper function to resolve paths with environment variables like %ProgramFiles%
def resolve_path(path):
    return os.path.expandvars(path)

@app.route('/take_screenshot', methods=['GET'])
def take_screenshot():
    # Take a screenshot
    screenshot_path = os.path.join(os.getcwd(), 'screenshot.png')
    screenshot = pyautogui.screenshot()
    
    # Resize the screenshot
    resized_screenshot = screenshot.resize((800, 600))  # Resize to 800x600 resolution
    resized_screenshot.save(screenshot_path)
    
    # Return the screenshot path
    return jsonify({"image_url": f"{public_url}/screenshot"})

@app.route('/screenshot', methods=['GET'])
def get_screenshot():
    # Serve the screenshot file
    return send_from_directory(directory=os.getcwd(), path='screenshot.png')

@app.route('/open_app', methods=['POST'])
def open_app():
    auth_response = authenticate_request()
    if auth_response:
        return auth_response

    data = request.json
    app_name = data.get("app_name")

    if not app_name or app_name not in APP_COMMANDS:
        return jsonify({"error": "Invalid app name provided."}), 400

    try:
        # Resolve the path for the app
        command = APP_COMMANDS[app_name]
        resolved_command = resolve_path(command)
        
        # Use subprocess.Popen to open the app in the background (non-blocking)
        process = subprocess.Popen(resolved_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return jsonify({"status": f"Successfully opened {app_name}."}), 200
    except Exception as e:
        # Capture any error details if the process fails to start
        return jsonify({"error": f"Failed to open {app_name}. Error: {str(e)}"}), 500

@app.route('/send_command', methods=['POST'])
def send_command():
    auth_response = authenticate_request()
    if auth_response:
        return auth_response

    command = request.json.get('command')
    # Execute the command here
    print(f'Received command: {command}')
    # Optionally execute the command using subprocess
    try:
        subprocess.Popen(command, shell=True)
        return jsonify({'status': 'Command executed'})
    except Exception as e:
        return jsonify({'error': f'Failed to execute command. Error: {str(e)}'}), 500

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

def monitor_activity():
    global last_activity_time, device_name, activity_detected

    last_activity_time = time.time()
    activity_detected = False

    def on_activity(activity_type):
        global last_activity_time, activity_detected
        last_activity_time = time.time()
        activity_detected = True
        #print(f'Activity detected: {activity_type}')

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

def run_wakeword_detection():
    import time
    import threading
    import platform
    if platform.system() == "Windows":
        import pyaudiowpatch as pyaudio
    else:
        import pyaudio
    import numpy as np
    from openwakeword.model import Model
    from plyer import notification
    import requests
    import speech_recognition as sr
    import warnings

    # Suppress specific warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=UserWarning)

    # === Configurable Parameters ===

    # Microphone settings
    MIC_NAME = "default"  # Name of the microphone to use

    # Audio parameters for wake word detection
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK_DURATION_MS = 30  # Duration of a chunk in milliseconds
    CHUNK_SIZE = int(RATE * CHUNK_DURATION_MS / 1000)  # Number of samples per chunk

    # Wake word detection parameters
    THRESHOLD = 0.1  # Confidence threshold for wake word detection
    INFERENCE_FRAMEWORK = 'onnx'
    MODEL_PATHS = ['nexus.onnx', 'jarvis.onnx', 'mycroft.onnx']

    # Recording parameters
    ENERGY_THRESHOLD = 2000  # Energy level for speech detection
    PAUSE_THRESHOLD = 2  # Seconds of silence before considering speech complete

    # Server configuration
    SERVER_URL = "https://rolling-essa-enpoi-12c37b5e.koyeb.app/send"
    SERVER_TOKEN = "Denemeler123."

    # Other parameters
    COOLDOWN = 1  # Seconds to wait before detecting another wake word

    def get_device_index(audio, device_name):
        """
        Get the index of the microphone device based on its name.
        """
        device_count = audio.get_device_count()
        for i in range(device_count):
            device_info = audio.get_device_info_by_index(i)
            if device_name in device_info['name']:
                return device_info['index']
        return None

    def initialize_mic_stream(audio, mic_index, format, channels, rate, chunk):
        """
        Initialize the microphone stream.
        """
        try:
            mic_stream = audio.open(format=format, channels=channels, rate=rate, input=True,
                                    input_device_index=mic_index, frames_per_buffer=chunk)
            return mic_stream
        except Exception as e:
            print(f"Mic {mic_index} not available. Waiting for it to be connected...")
            return None  # Return None if mic cannot be initialized

    def send_transcription_to_server(transcription, bot_key):
        """
        Send the transcription to the server.
        """
        if not transcription or len(transcription.strip()) <= 1:
            print("Transcription is empty or invalid. Not sending to server.")
            return

        # Print the transcribed text that is being sent
        print(f"Sending transcription to assistant: {transcription.strip()}")

        headers = {
            "Authorization": SERVER_TOKEN,
            "Content-Type": "application/json"
        }

        payload = {
            "message": transcription.strip(),
            "bot_key": bot_key
        }

        try:
            response = requests.post(SERVER_URL, json=payload, headers=headers)
            if response.status_code == 200:
                print(f"Successfully sent transcription to {bot_key}.")
            else:
                print(f"Failed to send transcription to {bot_key}. Server responded with: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error sending transcription to server for {bot_key}: {e}")

    def record_audio(file_path, mic_index, bot_key):
        """
        Record audio from the microphone using speech_recognition.
        """
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = ENERGY_THRESHOLD
        recognizer.pause_threshold = PAUSE_THRESHOLD

        # Use the same mic as in wake word detection
        with sr.Microphone(device_index=mic_index) as source:
            print("Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=0.7)
            print("Recording...")
            audio_data = recognizer.listen(source)
            print("Recording complete.")

            # Save the audio data to a WAV file
            with open(file_path, "wb") as f:
                f.write(audio_data.get_wav_data())

        # Placeholder for transcription
        transcription = "This is a placeholder transcription. answer with ok"
        # Print the transcribed text
        print(f"Transcription: {transcription}")

        # Send the transcription to the server
        #send_transcription_to_server(transcription, bot_key)
        print("Transcription sent to server.")  

    def detection_thread(mic_stream, mic_index, stop_event):
        """
        Thread function for wake word detection.
        """
        nonlocal last_notification_time
        wakeword_detected = False

        print("\n\nListening for wakewords...\n")
        while not stop_event.is_set():
            try:
                mic_audio = np.frombuffer(mic_stream.read(CHUNK_SIZE), dtype=np.int16)

                # Feed to openWakeWord model
                prediction = owwModel.predict(mic_audio)

                # Check for any wakeword detection
                detected_models = [mdl for mdl in prediction.keys() if prediction[mdl] >= THRESHOLD]
                if detected_models and not wakeword_detected and (time.time() - last_notification_time) >= COOLDOWN:
                    last_notification_time = time.time()
                    wakeword_detected = True  # Prevent multiple triggers

                    # Use the first detected model
                    mdl = detected_models[0]

                    notification.notify(
                        title='Wake Word Detected',
                        message=f'Detected activation from \"{mdl}\" model!',
                        app_name='WakeWordService'
                    )
                    print(f'Detected activation from \"{mdl}\" model!')

                    # Determine bot_key based on detected model
                    if mdl == 'mycroft':
                        bot_key = 'mycroft'
                    elif mdl == 'jarvis':
                        bot_key = 'jarvis'
                    else:
                        bot_key = None

                    if bot_key:
                        # Start recording using the new method
                        threading.Thread(target=record_audio, args=('input.wav', mic_index, bot_key)).start()

                # Reset wakeword_detected after cooldown
                if (time.time() - last_notification_time) >= COOLDOWN:
                    wakeword_detected = False

            except Exception as e:
                print(f"An error occurred during audio processing: {e}")
                # Assume mic is disconnected
                stop_event.set()
                break

    last_notification_time = 0

    owwModel = Model(
        wakeword_models=MODEL_PATHS,
        inference_framework=INFERENCE_FRAMEWORK
    )
    def list_available_mics():
        audio = pyaudio.PyAudio()
        device_count = audio.get_device_count()
        print("Available microphones:")
        for i in range(device_count):
            device_info = audio.get_device_info_by_index(i)
            print(f"Index {i}: {device_info['name']}")
        audio.terminate()
    list_available_mics()

    # Existing logic to select the microphone based on MIC_NAME
    while True:
        audio = pyaudio.PyAudio()

        mic_index = get_device_index(audio, MIC_NAME)
        if mic_index is None:
            print(f"Microphone '{MIC_NAME}' not found. Waiting for it to be connected...")
            while mic_index is None:
                time.sleep(5)
                audio.terminate()
                audio = pyaudio.PyAudio()
                mic_index = get_device_index(audio, MIC_NAME)

        mic_stream = initialize_mic_stream(audio, mic_index, FORMAT, CHANNELS, RATE, CHUNK_SIZE)
        if mic_stream is None:
            # Could not initialize mic stream, go back to waiting
            audio.terminate()
            continue

        # Create an event to control the detection thread
        stop_event = threading.Event()

        # Start the detection thread
        detection_thread_instance = threading.Thread(target=detection_thread, args=(mic_stream, mic_index, stop_event))
        detection_thread_instance.start()

        # Wait for the detection thread to finish
        detection_thread_instance.join()

        # When the detection thread finishes, it means the mic was disconnected
        print("Microphone disconnected. Stopping wake word detection.")
        mic_stream.close()
        audio.terminate()
        print("Returning to waiting for microphone to be connected...")

        # Wait a bit before retrying
        time.sleep(5)

def extract_public_url_from_conf(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
        match = re.search(r'You can now access http://0.0.0.0:5000 on (https://\S+)', content)
        if match:
            return match.group(1)
    return None

if __name__ == '__main__':
    # Start the tunnel using curl and wg-quick
    tunnel_command = "curl https://tunnel.pyjam.as/5000 > tunnel.conf && wg-quick up ./tunnel.conf"
    subprocess.run(tunnel_command, shell=True)
    time.sleep(2)  # Give the tunnel some time to establish the connection

    # Extract the public URL from the tunnel.conf file
    public_url = extract_public_url_from_conf('tunnel.conf')

    if public_url:
        print(f"Ingress established at {public_url}")
        
        # Update Firebase with the public URL
        device_name = socket.gethostname()
        update_public_url(device_name, public_url)
        
        # Run the monitor_activity function in a separate thread
        threading.Thread(target=monitor_activity).start()
        
        # Set public_url as a global variable
        globals()['public_url'] = public_url
        
        # Run the Flask app in a separate thread
        threading.Thread(target=app.run, kwargs={'port':5000, 'host':'0.0.0.0'}).start()
        
        # Start the wakeword detection code in a separate thread
        threading.Thread(target=run_wakeword_detection).start()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
    else:
        print("Failed to establish tunnel connection")
