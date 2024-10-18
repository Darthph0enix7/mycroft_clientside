from cryptography.fernet import Fernet
from firebase_admin import db
from flask import request, jsonify

def decrypt_client_secret(encryption_key_cli):
    with open("service_account.json.encrypted", "rb") as encrypted_file:
        encrypted_data = encrypted_file.read()

    fernet = Fernet(encryption_key_cli)
    decrypted_data = fernet.decrypt(encrypted_data)

    with open("service_account.json", "wb") as decrypted_file:
        decrypted_file.write(decrypted_data)

def decrypt_firebase_config(encryption_key_config):
    with open("firebase_config.json.encrypted", "rb") as encrypted_file:
        encrypted_data = encrypted_file.read()

    fernet = Fernet(encryption_key_config)
    decrypted_data = fernet.decrypt(encrypted_data)

    with open("firebase_config.json", "wb") as decrypted_file:
        decrypted_file.write(decrypted_data)

def decrypt_adminsdk(encryption_key_adminsdk):
    with open("firebase_adminsdk.json.encrypted", "rb") as encrypted_file:
        encrypted_data = encrypted_file.read()

    fernet = Fernet(encryption_key_adminsdk)
    decrypted_data = fernet.decrypt(encrypted_data)

    with open("firebase_adminsdk.json", "wb") as decrypted_file:
        decrypted_file.write(decrypted_data)

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

def authenticate_request(AUTH_TOKEN):
    token = request.headers.get('Authorization') or request.json.get('token')
    if token != AUTH_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    return None