import time
import socket
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.clock import Clock
from firebase import update_active_device
from firebase import decrypt_client_secret, decrypt_firebase_config, decrypt_adminsdk, update_public_url, update_active_device, authenticate_request
from monitor_activity import monitor_activity
from wakeword import run_wakeword_detection
import firebase_admin
from firebase_admin import credentials
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import os

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

global last_activity_time, device_name, activity_detected

last_activity_time = time.time()
activity_detected = False
device_name = socket.gethostname()

class ActivityMonitorApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical')
        button = Button(text='Click me')
        button.bind(on_press=self.on_button_press)
        layout.add_widget(button)

        Window.bind(on_touch_down=self.on_touch_down)
        Window.bind(on_touch_move=self.on_touch_move)
        Window.bind(on_touch_up=self.on_touch_up)

        Clock.schedule_interval(self.check_activity, 2)

        return layout

    def on_button_press(self, instance):
        self.on_activity('button_press')

    def on_touch_down(self, instance, touch):
        self.on_activity('touch_down')

    def on_touch_move(self, instance, touch):
        self.on_activity('touch_move')

    def on_touch_up(self, instance, touch):
        self.on_activity('touch_up')

    def on_activity(self, activity_type):
        global last_activity_time, activity_detected
        last_activity_time = time.time()
        activity_detected = True
        #print(f'Activity detected: {activity_type}')

    def check_activity(self, dt):
        global last_activity_time, activity_detected, device_name
        current_time = time.time()
        if activity_detected and (current_time - last_activity_time) < 5:
            update_active_device(device_name)
            activity_detected = False

ActivityMonitorApp().run()