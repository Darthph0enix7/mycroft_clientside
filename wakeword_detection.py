import time
import numpy as np
import openwakeword
from openwakeword.model import Model
import pyaudio
import threading
import wave
from faster_whisper import WhisperModel

openwakeword.utils.download_models()

# Audio parameters for wake word detection
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK_DURATION_MS = 30  # Duration of a chunk in milliseconds
CHUNK_SIZE = int(RATE * CHUNK_DURATION_MS / 1000)  # Number of samples per chunk

# Wake word detection parameters
THRESHOLD = 0.5  # Increased confidence threshold for wake word detection
INFERENCE_FRAMEWORK = 'onnx'
MODEL_PATHS = ['nexus.onnx', 'jarvis.onnx', 'mycroft.onnx']

# Recording parameters
ENERGY_THRESHOLD = 1500  # Energy level for speech detection
PAUSE_THRESHOLD = 1.5  # Seconds of silence before considering speech complete

# Other parameters
COOLDOWN = 5  # Increased seconds to wait before detecting another wake word

# State machine states
IDLE = "IDLE"
RECORDING = "RECORDING"
PROCESSING = "PROCESSING"
COOLDOWN_STATE = "COOLDOWN"

# Global variables
current_state = IDLE
last_detection_time = 0

state_lock = threading.Lock()  # Lock to control state changes


def check_torch_and_gpu():
    try:
        import torch
        if torch.cuda.is_available():
            return True, "cuda"
        else:
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
        compute_type = "int8"

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


def record_audio(file_path):
    """
    Record audio from the microphone for a fixed duration of 5 seconds.
    """
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True,
                        frames_per_buffer=CHUNK_SIZE)

    print("Recording for 5 seconds...")
    frames = []

    for _ in range(0, int(RATE / CHUNK_SIZE * 5)):
        data = stream.read(CHUNK_SIZE)
        frames.append(data)

    print("Recording complete.")

    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Save the recorded data to a WAV file
    with wave.open(file_path, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))


def detection_thread(stop_event, model, lock):
    """
    Thread function for wake word detection.
    """
    global last_detection_time, current_state

    while not stop_event.is_set():
        with state_lock:
            if current_state != IDLE:
                continue

        try:
            # Set up microphone stream for wake word detection
            audio = pyaudio.PyAudio()
            mic_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True,
                                    frames_per_buffer=CHUNK_SIZE)

            print("\n\nListening for wakewords...\n")

            while not stop_event.is_set():
                with state_lock:
                    if current_state != IDLE:
                        break  # Stop detection if we are no longer in IDLE state

                mic_audio = np.frombuffer(mic_stream.read(CHUNK_SIZE), dtype=np.int16)

                # Feed to openWakeWord model
                prediction = owwModel.predict(mic_audio)

                # Check for any wakeword detection
                detected_models = [mdl for mdl in prediction.keys() if prediction[mdl] >= THRESHOLD]
                if detected_models and (time.time() - last_detection_time) >= COOLDOWN:
                    with state_lock:
                        if current_state == IDLE:
                            last_detection_time = time.time()
                            current_state = RECORDING

                            # Use the first detected model
                            mdl = detected_models[0]
                            print(f'Detected activation from "{mdl}" model!')

                            # Acquire lock to ensure no overlapping recordings
                            with lock:
                                # Stop the mic stream while recording
                                mic_stream.stop_stream()
                                mic_stream.close()

                                # Record audio after detecting the wake word
                                audio_file_path = "input.wav"
                                record_audio(audio_file_path)

                                current_state = PROCESSING

                                try:
                                    # Perform transcription
                                    transcription = transcribe_audio(audio_file_path, model)
                                    print("Transcription:\n", transcription)
                                except Exception as e:
                                    print(f"An error occurred during transcription: {e}")

                                # Move to cooldown state
                                current_state = COOLDOWN_STATE

                            # Wait for cooldown period
                            time.sleep(COOLDOWN)

                            # Transition back to IDLE state after cooldown
                            with state_lock:
                                current_state = IDLE

            # Ensure microphone stream is closed properly after leaving the loop
            if mic_stream is not None:
                mic_stream.stop_stream()
                mic_stream.close()

        except Exception as e:
            print(f"An error occurred during audio processing: {e}")
            stop_event.set()
            break

        finally:
            # Ensure that audio resources are properly cleaned up
            if 'audio' in locals():
                audio.terminate()


owwModel = Model(
    wakeword_models=MODEL_PATHS,
    inference_framework=INFERENCE_FRAMEWORK
)


def listen_for_wakeword():
    # Create an event to control the detection thread
    stop_event = threading.Event()

    # Initialize the transcription model
    model = initialize_model()

    # Create a lock for recording and transcription
    lock = threading.Lock()

    # Start the detection thread
    detection_thread_instance = threading.Thread(target=detection_thread, args=(stop_event, model, lock))
    detection_thread_instance.start()

    try:
        # Wait for the detection thread to finish
        detection_thread_instance.join()
    except KeyboardInterrupt:
        print("Interrupted by user. Stopping...")
        stop_event.set()
        detection_thread_instance.join()

    print("Microphone disconnected. Stopping wake word detection.")


if __name__ == "__main__":
    listen_for_wakeword()
