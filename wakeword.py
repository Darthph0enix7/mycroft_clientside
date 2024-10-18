import time
import threading
import platform
if platform.system() == "Windows":
    import pyaudiowpatch as pyaudio
else:
    import pyaudio
import numpy as np
import openwakeword
from openwakeword.model import Model
from plyer import notification
import requests
import speech_recognition as sr
import warnings

from faster_whisper import WhisperModel

def run_wakeword_detection():
    
    openwakeword.utils.download_models()

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

    def check_torch_and_gpu():
        try:
            import torch
            if torch.cuda.is_available():
                print("CUDA is available.")
                return True, "cuda"
            else:
                print("CUDA is not available.")
                return True, "cpu"
        except ImportError:
            return False, "cpu"

    def initialize_model():
        torch_installed, device = check_torch_and_gpu()
        print(f"Using device: {device}")
        if torch_installed and device == "cuda":
            model_size = "deepdml/faster-whisper-large-v3-turbo-ct2"
            compute_type = "float16"
        else:
            model_size = "base"
            compute_type = "float16"

        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        return model

    def transcribe_audio(audio_file_path, model):
        segments, info = model.transcribe(audio=audio_file_path, vad_filter=True,
                                        vad_parameters=dict(min_silence_duration_ms=500))

        print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

        transcription = ""
        for segment in segments:
            transcription += "[%.2fs -> %.2fs] %s\n" % (segment.start, segment.end, segment.text)

        return transcription

    def record_audio(file_path, mic_index, bot_key, model):
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

        # Transcribe the audio using the new method
        transcription = transcribe_audio(file_path, model)
        # Print the transcribed text
        print(f"Transcription: {transcription} sent to server.")

        # Send the transcription to the server
        send_transcription_to_server(transcription, bot_key)

    def detection_thread(mic_stream, mic_index, stop_event):
        """
        Thread function for wake word detection.
        """
        nonlocal last_notification_time
        wakeword_detected = False
        model = initialize_model()
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
                    elif mdl == 'nexus':
                        bot_key = 'nexus'
                    else:
                        bot_key = None

                    if bot_key:
                        # Start recording using the new method
                        threading.Thread(target=record_audio, args=('input.wav', mic_index, bot_key, model)).start()

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