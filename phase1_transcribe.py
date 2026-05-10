from faster_whisper import WhisperModel
import os
import sys

def transcribe_audio(audio_file_path):
    print("=" * 50)
    print("  TRANSCRIPTION (Local - FREE)")
    print("=" * 50)
    print(f"\nFile: {audio_file_path}")
    print("Model load ho raha hai... (pehli baar thoda time lagega)")

    # Best balance: speed + accuracy
    model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8"
    )

    print("Transcribing with auto language detection...")

    # ✅ UPDATED PART (IMPORTANT FIX)
    segments, info = model.transcribe(
        audio_file_path,
        language=None,          # Hindi + English auto detect
        beam_size=5,            # better accuracy
        vad_filter=True,        # remove silence
        vad_parameters=dict(
            min_silence_duration_ms=500
        )
    )

    print(f"\nDetected language: {info.language} (probability: {info.language_probability:.2f})")

    transcript = ""
    for segment in segments:
        transcript += segment.text + " "

    transcript = transcript.strip()

    # Save output
    os.makedirs("transcripts", exist_ok=True)

    base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
    output_path = os.path.join("transcripts", f"{base_name}_transcript.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    print("\nTranscript ready!")
    print(f"Saved: {output_path}")

    print("\n--- TRANSCRIPT ---")
    print(transcript)

    return output_path, transcript


if __name__ == "__main__":
    recordings = sorted(os.listdir("recordings"))

    if not recordings:
        print("Koi recording nahi mili!")
        sys.exit(1)

    audio_path = os.path.join("recordings", recordings[-1])
    transcribe_audio(audio_path)