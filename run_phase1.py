from phase1_record import record_meeting
from phase1_transcribe import transcribe_audio
from phase1_summary import generate_summary

print("\n MEETING AI AGENT - PHASE 1")
print("Recording → Transcription → Summary\n")

# Step 1: Record karo
audio_file = record_meeting()

# Step 2: Transcribe karo
transcript_file, transcript_text = transcribe_audio(audio_file)

# Step 3: Summary banao
summary = generate_summary(transcript_text)

print("\n\nSab kuch complete ho gaya!")
print(f"Recording: {audio_file}")
print(f"Transcript: {transcript_file}")
print("Summary: summaries/ folder mein dekho")