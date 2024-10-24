import time
import socket
import os
import json
from firebase import update_active_device, decrypt_client_secret, decrypt_firebase_config, decrypt_adminsdk
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from evdev import InputDevice, categorize, ecodes

load_dotenv()

encryption_key_cli = os.environ.get('ENCRYPTION_KEY_CLI').encode()
encryption_key_config = os.environ.get('ENCRYPTION_KEY_CONFIG').encode()
encryption_key_adminsdk = os.environ.get('ENCRYPTION_KEY_ADMINSDK').encode()
AUTH_TOKEN = os.environ.get('AUTH_TOKEN')

decrypt_client_secret(encryption_key_cli)
decrypt_firebase_config(encryption_key_config)
decrypt_adminsdk(encryption_key_adminsdk)

with open('firebase_config.json') as config_file:
    firebase_config = json.load(config_file)

import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("firebase_adminsdk.json")
firebase_admin.initialize_app(cred, firebase_config)

global last_activity_time, device_name, activity_detected

last_activity_time = time.time()
activity_detected = False
device_name = socket.gethostname()

def monitor_activity_arm():
    global last_activity_time, device_name, activity_detected

    # List all input devices
    devices = [InputDevice(path) for path in os.listdir('/dev/input') if 'event' in path]

    while True:
        for device in devices:
            try:
                for event in device.read_loop():
                    if event.type == ecodes.EV_KEY or event.type == ecodes.EV_ABS:
                        last_activity_time = time.time()
                        activity_detected = True
                        #print(f'Activity detected: {event.code}')
            except OSError:
                # Handle device read errors
                pass

        current_time = time.time()
        if activity_detected and (current_time - last_activity_time) < 5:
            update_active_device(device_name)
            activity_detected = False
        time.sleep(2)

monitor_activity_arm()