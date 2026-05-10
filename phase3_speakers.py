import os
import sys
import json
import re
import numpy as np
import warnings
warnings.filterwarnings("ignore")


def extract_features(audio_path):
    """Audio se MFCC features nikalo"""
    import librosa
    print("  Audio load ho raha hai...")
    y, sr = librosa.load(audio_path, sr=16000, mono=True)
    
    # MFCC features — voice fingerprint ki tarah
    print("  Features extract kar raha hai...")
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=4000)
    # har 0.25 sec ka ek frame
    return mfcc.T, sr, len(y)/sr


def diarize_audio(audio_file, num_speakers=2):
    print("="*55)
    print("  SPEAKER DETECTION — Phase 3A")
    print("="*55)
    print(f"\nFile: {audio_file}")
    print(f"Expected speakers: {num_speakers}")

    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler

        features, sr, duration = extract_features(audio_file)

        if len(features) < num_speakers:
            print("Audio bahut chhoti hai!")
            return None

        print(f"  Duration: {duration:.1f}s | Frames: {len(features)}")
        print(f"  Clustering {num_speakers} speakers...")

        # Normalize
        scaler = StandardScaler()
        X = scaler.fit_transform(features)

        # KMeans clustering
        km = KMeans(n_clusters=num_speakers, random_state=42,
                    n_init=15, max_iter=500)
        labels = km.fit_predict(X)

        # Smooth labels (flickering kam karo)
        window = 5
        smoothed = []
        for i in range(len(labels)):
            start = max(0, i - window)
            end   = min(len(labels), i + window + 1)
            chunk = labels[start:end]
            smoothed.append(int(np.bincount(chunk).argmax()))
        labels = smoothed

        # Timeline banao
        hop_sec = 4000 / 16000  # 0.25 sec per frame
        results = []
        prev_spk = None
        seg_start = 0.0

        for i, label in enumerate(labels):
            spk = f"Speaker_{label + 1}"
            t   = i * hop_sec
            if spk != prev_spk:
                if prev_spk is not None:
                    results.append({
                        "speaker": prev_spk,
                        "start":    round(seg_start, 2),
                        "end":      round(t, 2),
                        "duration": round(t - seg_start, 2)
                    })
                seg_start = t
                prev_spk  = spk

        # Last segment
        if prev_spk:
            results.append({
                "speaker": prev_spk,
                "start":    round(seg_start, 2),
                "end":      round(duration, 2),
                "duration": round(duration - seg_start, 2)
            })

        # Short segments merge karo (< 1.5 sec)
        merged = []
        for seg in results:
            if merged and seg['duration'] < 1.5 and \
               merged[-1]['speaker'] != seg['speaker']:
                merged[-1]['end']      = seg['end']
                merged[-1]['duration'] = round(
                    merged[-1]['end'] - merged[-1]['start'], 2)
            else:
                merged.append(seg)
        results = merged

        # Print timeline
        print("\n" + "="*55)
        print("  SPEAKER TIMELINE")
        print("="*55)

        speakers = set(r['speaker'] for r in results)
        for seg in results:
            s = f"{int(seg['start']//60):02d}:{seg['start']%60:05.2f}"
            e = f"{int(seg['end']//60):02d}:{seg['end']%60:05.2f}"
            bar = "█" * max(1, int(seg['duration'] * 2))
            print(f"  {seg['speaker']}  {s} → {e}  {bar}")

        print(f"\nTotal speakers: {len(speakers)}")
        for sp in sorted(speakers):
            total = sum(x['duration'] for x in results if x['speaker'] == sp)
            pct   = total / duration * 100
            print(f"  {sp}: {total:.1f}s ({pct:.0f}% of meeting)")

        # Save JSON
        base = os.path.splitext(os.path.basename(audio_file))[0]
        out  = os.path.join("transcripts", f"{base}_speakers.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump({
                "audio_file":     audio_file,
                "total_speakers": len(speakers),
                "duration":       duration,
                "segments":       results
            }, f, indent=2)
        print(f"\nSaved: {out}")
        return results

    except Exception as e:
        print(f"Error: {e}")
        import traceback; traceback.print_exc()
        return None


def label_transcript(transcript_file, speaker_segments):
    """Transcript ko speaker labels ke saath combine karo"""
    if not speaker_segments:
        return None

    print("\n" + "="*55)
    print("  SPEAKER-LABELED TRANSCRIPT")
    print("="*55)

    with open(transcript_file, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        print("Transcript empty hai!")
        return None

    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    total_seg = len(speaker_segments)
    total_sen = len(sentences)
    labeled   = []
    cur_spk   = None

    for i, sentence in enumerate(sentences):
        idx     = min(int(i * total_seg / total_sen), total_seg - 1)
        speaker = speaker_segments[idx]['speaker']
        if speaker != cur_spk:
            cur_spk = speaker
            print(f"\n{speaker}:")
        print(f"  {sentence}")
        labeled.append({"speaker": speaker, "text": sentence})

    # Save labeled transcript
    base = os.path.splitext(os.path.basename(transcript_file))[0]
    out  = os.path.join("transcripts", f"{base}_labeled.txt")

    with open(out, "w", encoding="utf-8") as f:
        cur = None
        for item in labeled:
            if item['speaker'] != cur:
                cur = item['speaker']
                f.write(f"\n{cur}:\n")
            f.write(f"  {item['text']}\n")

    print(f"\nSaved: {out}")
    return labeled
if __name__ == "__main__":
    # Default
    num_spk = 2

    # Audio path
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
    else:
        wavs = sorted([f for f in os.listdir("recordings")
                       if f.endswith('.wav')])
        if not wavs:
            print("Koi recording nahi mili!")
            sys.exit(1)
        audio_path = os.path.join("recordings", wavs[-1])
        print(f"Latest: {audio_path}\n")

    # 🔥 NEW: participant count logic (API style input)
    meeting_file = "meeting.json"  # ya jo bhi tumhara API output hai
    if os.path.exists(meeting_file):
        try:
            with open(meeting_file, "r") as f:
                meeting = json.load(f)

            participant_count = len(meeting.get("participantIds") or []) or 2
            participant_count = max(2, min(participant_count, 5))  # limit 2–5

            num_spk = participant_count
            print(f"Using participant count from API: {num_spk}")

        except Exception as e:
            print("Meeting file read error, fallback to default 2 speakers")

    # CLI override (highest priority)
    if len(sys.argv) > 2:
        num_spk = int(sys.argv[2])
        print(f"Override from CLI: {num_spk}")

    # Run diarization
    segments = diarize_audio(audio_path, num_speakers=num_spk)
    if segments:
        base = os.path.splitext(os.path.basename(audio_path))[0]
        tr   = os.path.join("transcripts", f"{base}_transcript.txt")
        if os.path.exists(tr):
            label_transcript(tr, segments)
        else:
            print(f"\nTranscript nahi mila: {tr}")
            print("Pehle run karo: python phase1_transcribe.py")