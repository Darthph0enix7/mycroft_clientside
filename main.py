import os
import re
import threading
import json
import time
import socket
import platform
import subprocess
import firebase_admin
from firebase_admin import credentials
from flask import Flask, request, jsonify, send_from_directory
from pynput import keyboard, mouse
import pyautogui
from dotenv import load_dotenv
import ctypes
import sys
from pyngrok import ngrok

from firebase import decrypt_client_secret, decrypt_firebase_config, decrypt_adminsdk, update_public_url, update_active_device, authenticate_request
from wakeword import run_wakeword_detection

load_dotenv()

encryption_key_cli = os.environ.get('ENCRYPTION_KEY_CLI').encode()
encryption_key_config = os.environ.get('ENCRYPTION_KEY_CONFIG').encode()
encryption_key_adminsdk = os.environ.get('ENCRYPTION_KEY_ADMINSDK').encode()
# Token for basic authentication
AUTH_TOKEN = os.environ.get('AUTH_TOKEN')  # Replace with your actual token

decrypt_client_secret(encryption_key_cli)
decrypt_firebase_config(encryption_key_config)
decrypt_adminsdk(encryption_key_adminsdk)

# Load Firebase configuration from JSON file
with open('firebase_config.json') as config_file:
    firebase_config = json.load(config_file)

cred = credentials.Certificate("firebase_adminsdk.json")
firebase_admin.initialize_app(cred, firebase_config)

app = Flask(__name__)

@app.route('/')
def home():
    return "Server running"

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
    
    # Get the original dimensions of the screenshot
    original_width, original_height = screenshot.size
    
    # Calculate the scaling factor to maintain the aspect ratio
    max_resolution = 1080
    scaling_factor = min(max_resolution / original_width, max_resolution / original_height)
    
    # Calculate the new dimensions while maintaining the aspect ratio
    new_width = int(original_width * scaling_factor)
    new_height = int(original_height * scaling_factor)
    
    # Resize the screenshot
    resized_screenshot = screenshot.resize((new_width, new_height))
    resized_screenshot.save(screenshot_path)
    
    # Return the screenshot path
    return jsonify({"image_url": f"{public_url}/screenshot"})

@app.route('/screenshot', methods=['GET'])
def get_screenshot():
    # Serve the screenshot file
    return send_from_directory(directory=os.getcwd(), path='screenshot.png')

@app.route('/open_app', methods=['POST'])
def open_app():
    auth_response = authenticate_request(AUTH_TOKEN)
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
    auth_response = authenticate_request(AUTH_TOKEN)
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
    auth_response = authenticate_request(AUTH_TOKEN)
    if auth_response:
        return auth_response

    file = request.files['file']
    file.save(f'./{file.filename}')
    print(f'Received file: {file.filename}')
    return jsonify({'status': 'File received'})

@app.route('/download_file', methods=['GET'])
def download_file():
    auth_response = authenticate_request(AUTH_TOKEN)
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

if __name__ == '__main__':
    load_dotenv()
    # Authenticate using the token from the environment variable
    ngrok.set_auth_token(os.environ['NGROK_AUTHTOKEN'])

    # Start an Ngrok tunnel to your local Flask app (running on port 8000)
    tunnel = ngrok.connect(7888)
    public_url = tunnel.public_url

    # Print the public URL for the tunnel
    print(f"Ngrok Tunnel URL: {public_url}")

    device_name = socket.gethostname()
    update_public_url(device_name, public_url)

    threading.Thread(target=monitor_activity).start()

    globals()['public_url'] = public_url

    threading.Thread(target=app.run, kwargs={'port': 7888, 'host': '0.0.0.0'}).start()

    threading.Thread(target=run_wakeword_detection, args=(AUTH_TOKEN,)).start()

    while True:
        time.sleep(1)
else:
    print("Failed to establish tunnel connection")
