import time
import socket
from pynput import keyboard, mouse
from firebase import update_active_device
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.clock import Clock


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

def monitor_activity_arm():
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

