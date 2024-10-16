from faster_whisper import WhisperModel
import torch

model_size = "base"

# Run on GPU with FP16
model = WhisperModel("deepdml/faster-whisper-large-v3-turbo-ct2", device="cuda", compute_type="float16")

#model = WhisperModel("deepdml/faster-whisper-large-v3-turbo-ct2", device="cuda", compute_type="int8_float16")
# or run on CPU with INT8
# model = WhisperModel(model_size, device="cpu", compute_type="int8")

segments, info = model.transcribe(audio="input.wav", vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500))

print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

for segment in segments:
    print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))