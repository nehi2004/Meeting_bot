# test_speaker_mic.py
import sounddevice as sd
import numpy as np
import time

print("Headphones disconnect karo pehle!")
print("Phir YouTube video loud chalao...")
time.sleep(3)
print("Recording 5 seconds...")

# Microphone Array use karo
recording = sd.rec(
    int(5 * 16000),
    samplerate=16000,
    channels=1,
    dtype='int16',
    device=None  # system default mic
)
sd.wait()

vol = np.abs(recording).mean()
print(f"Volume: {vol:.1f}")
if vol > 50:
    print("PERFECT! Meeting audio capture hoga!")
elif vol > 10:
    print("Theek hai — kaam karega thoda loud karo speakers")
else:
    print("Abhi bhi low — speakers aur louder karo")