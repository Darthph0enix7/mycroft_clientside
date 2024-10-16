import time
from main import RealtimeDB
import socket
from pynput import keyboard, mouse

def update_active_device(device_name):
    db_instance = RealtimeDB()
    db_instance.write_data('active_device', device_name)


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

if __name__ == "__main__":
    monitor_activity()