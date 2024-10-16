import time
from multiprocessing import Queue

def process_command(queue):
    if not queue.empty():
        wakeword, audio_file_path = queue.get()
        print(f"Processing command for wakeword: {wakeword}")
        print(f"Audio file path: {audio_file_path}")
        # Add your command processing logic here
        time.sleep(3)  # Simulate command processing
    time.sleep(1)  # Check for signal periodically

if __name__ == "__main__":
    queue = Queue()
    process_command(queue)