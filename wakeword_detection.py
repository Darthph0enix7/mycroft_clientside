import time
import numpy as np
from multiprocessing import Queue
import openwakeword
from openwakeword.model import Model
import pyaudio
import warnings
import threading
import speech_recognition as sr

openwakeword.utils.download_models()

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
ENERGY_THRESHOLD = 1500  # Energy level for speech detection
PAUSE_THRESHOLD = 1.5  # Seconds of silence before considering speech complete

# Other parameters
COOLDOWN = 1  # Seconds to wait before detecting another wake word

# Global variable for last detection time
last_detection_time = 0

def record_audio(file_path):
    """
    Record audio from the microphone using speech_recognition after wake word detection.
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = ENERGY_THRESHOLD
    recognizer.pause_threshold = PAUSE_THRESHOLD

    # Use the same mic as in wake word detection
    with sr.Microphone() as source:
        print("Adjusting for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=0.7)
        print("Recording...")
        audio_data = recognizer.listen(source)
        print("Recording complete.")

        # Save the audio data to a WAV file
        with open(file_path, "wb") as f:
            f.write(audio_data.get_wav_data())

def detection_thread(mic_stream, stop_event, queue):
    """
    Thread function for wake word detection.
    """
    global last_detection_time
    wakeword_detected = False

    print("\n\nListening for wakewords...\n")
    while not stop_event.is_set():
        try:
            mic_audio = np.frombuffer(mic_stream.read(CHUNK_SIZE), dtype=np.int16)

            # Feed to openWakeWord model
            prediction = owwModel.predict(mic_audio)

            # Check for any wakeword detection
            detected_models = [mdl for mdl in prediction.keys() if prediction[mdl] >= THRESHOLD]
            if detected_models and not wakeword_detected and (time.time() - last_detection_time) >= COOLDOWN:
                last_detection_time = time.time()
                wakeword_detected = True  # Prevent multiple triggers

                # Use the first detected model
                mdl = detected_models[0]

                print(f'Detected activation from "{mdl}" model!')

                # Record audio after detecting the wake word
                audio_file_path = "input.wav"
                record_audio(audio_file_path)

                # Signal the process_command script via the queue
                queue.put((mdl, audio_file_path))

            # Reset wakeword_detected after cooldown
            if (time.time() - last_detection_time) >= COOLDOWN:
                wakeword_detected = False

        except Exception as e:
            print(f"An error occurred during audio processing: {e}")
            # Assume mic is disconnected
            stop_event.set()
            break

owwModel = Model(
    wakeword_models=MODEL_PATHS,
    inference_framework=INFERENCE_FRAMEWORK
)

def listen_for_wakeword(queue):
    audio = pyaudio.PyAudio()
    mic_index = None  # Use default microphone

    mic_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True,
                            input_device_index=mic_index, frames_per_buffer=CHUNK_SIZE)

    # Create an event to control the detection thread
    stop_event = threading.Event()

    # Start the detection thread
    detection_thread_instance = threading.Thread(target=detection_thread, args=(mic_stream, stop_event, queue))
    detection_thread_instance.start()

    # Wait for the detection thread to finish
    detection_thread_instance.join()

    # When the detection thread finishes, it means the mic was disconnected
    print("Microphone disconnected. Stopping wake word detection.")
    mic_stream.close()
    audio.terminate()

if __name__ == "__main__":
    queue = Queue()
    listen_for_wakeword(queue)