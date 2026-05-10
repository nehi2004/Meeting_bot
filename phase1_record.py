import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
from datetime import datetime
import os

SAMPLE_RATE = 16000   # Whisper ke liye best quality
CHANNELS = 1          # Mono audio
OUTPUT_DIR = "recordings"

def record_meeting():
    print("=" * 50)
    print("  MEETING RECORDER")
    print("=" * 50)
    print("\nRecording shuru karne ke liye Enter dabao...")
    input()

    frames = []

    def callback(indata, frame_count, time_info, status):
        if status:
            print(f"Warning: {status}")
        frames.append(indata.copy())

    print("Recording chal rahi hai...")
    print("Band karne ke liye ENTER dabao\n")

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='int16',
        callback=callback
    )

    with stream:
        input()  # Enter dabao tab tak record hota rahega

    print("Recording band ho gayi. Saving...")

    # Audio combine karo
    audio_data = np.concatenate(frames, axis=0)

    # Filename mein date/time daalo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_DIR, f"meeting_{timestamp}.wav")

    # Save karo
    wav.write(filename, SAMPLE_RATE, audio_data)

    duration = len(audio_data) / SAMPLE_RATE
    print(f"\nSaved: {filename}")
    print(f"Duration: {duration:.1f} seconds")

    return filename

if __name__ == "__main__":
    saved_file = record_meeting()
    print(f"\nAb transcription ke liye run karo:")
    print(f"python phase1_transcribe.py {saved_file}")