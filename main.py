import asyncio
import datetime
import json
import os
import pickle
import platform
import socket
import subprocess
import threading
import time
import warnings
from datetime import datetime, timezone
from typing import List, Optional, Type

import dateutil.parser
import firebase_admin
import pyautogui  # For taking screenshots
import requests
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from firebase_admin import credentials, db
from flask import Flask, jsonify, request, send_from_directory
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, Tool
from langchain_experimental.utilities import PythonREPL
from pydantic import BaseModel, Field
from pynput import keyboard, mouse

from multiprocessing import Process, Queue
import wakeword_detection
import process_command
import activity_monitoring

load_dotenv()

encryption_key_cli = os.environ.get('ENCRYPTION_KEY_CLI').encode()
encryption_key_config = os.environ.get('ENCRYPTION_KEY_CONFIG').encode()
encryption_key_adminsdk = os.environ.get('ENCRYPTION_KEY_ADMINSDK').encode()

def decrypt_client_secret():
    print("Starting decryption of client_secret.json.encrypted")
    with open("service_account.json.encrypted", "rb") as encrypted_file:
        encrypted_data = encrypted_file.read()
        print(f"Encrypted data: {encrypted_data[:100]}...")  # Print first 100 bytes for brevity

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


if __name__ == "__main__":

    # Initialize Firebase Admin SDK with credentials
    cred = credentials.Certificate("firebase_adminsdk.json")
    firebase_admin.initialize_app(cred, firebase_config)
    
    queue = Queue()

    p1 = Process(target=wakeword_detection.listen_for_wakeword, args=(queue,))
    p2 = Process(target=process_command.process_command, args=(queue,))
    p3 = Process(target=activity_monitoring.monitor_activity)

    p1.start()
    p2.start()
    p3.start()

    p1.join()
    p2.join()
    p3.join()