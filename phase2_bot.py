import time
import os
import sys
import json
import requests
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np

load_dotenv()

# ════════════════════════════════════════════════════
#  SETTINGS
# ════════════════════════════════════════════════════
SAMPLE_RATE = 16000
CHANNELS    = 1
OUTPUT_DIR  = "recordings"
API_URL     = os.getenv("API_URL", "https://steadfast-warmth-production-64c8.up.railway.app")
API_TOKEN   = os.getenv("API_TOKEN", "")
# ════════════════════════════════════════════════════


def find_best_input_device():
    devices = sd.query_devices()
    priority_keywords = [
        'stereo mix', 'cable output', 'what u hear',
        'microphone array', 'microphone',
    ]
    for keyword in priority_keywords:
        for i, dev in enumerate(devices):
            if keyword in dev['name'].lower() and dev['max_input_channels'] > 0:
                try:
                    test = sd.rec(int(0.1 * SAMPLE_RATE),
                                  samplerate=SAMPLE_RATE,
                                  channels=1, dtype='int16', device=i)
                    sd.wait()
                    print(f"  Audio device: [{i}] {dev['name']}")
                    return i
                except Exception:
                    continue
    print("  Default mic use kar raha hai")
    return None


def list_all_input_devices():
    print("\nSaare available input devices:")
    for i, d in enumerate(sd.query_devices()):
        if d['max_input_channels'] > 0:
            print(f"  [{i:2d}] {d['name']}")
    print()


def setup_chrome():
    options = Options()
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_mic":    1,
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.notifications":       2,
    })
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def mute_bot(driver):
    for aria in ["microphone", "mic", "camera", "video"]:
        try:
            btns = driver.find_elements(
                By.XPATH, f"//button[contains(@aria-label,'{aria}')]")
            for b in btns:
                label = (b.get_attribute("aria-label") or "").lower()
                if "off" not in label and b.is_displayed():
                    b.click()
                    time.sleep(0.8)
                    break
        except Exception:
            pass


def join_meet(driver, url):
    print(f"  Meeting khul rahi hai: {url}")
    driver.get(url)
    time.sleep(5)
    mute_bot(driver)

    join_texts = ["Join now", "Ask to join", "Join", "Abhi join karein"]
    joined = False

    for attempt in range(6):
        for text in join_texts:
            try:
                for btn in driver.find_elements(
                        By.XPATH, f"//button[contains(.,'{text}')]"):
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        print(f"  Joined! ('{text}')")
                        joined = True
                        break
            except Exception:
                pass
            if joined:
                break

        if not joined:
            for text in join_texts:
                try:
                    for span in driver.find_elements(
                            By.XPATH, f"//span[contains(text(),'{text}')]"):
                        try:
                            parent = span.find_element(
                                By.XPATH, "./ancestor::button")
                            if parent.is_displayed():
                                parent.click()
                                print(f"  Joined via span!")
                                joined = True
                                break
                        except Exception:
                            pass
                    if joined:
                        break
                except Exception:
                    pass

        if not joined:
            try:
                for rb in driver.find_elements(By.XPATH, "//*[@role='button']"):
                    if any(t.lower() in rb.text.lower() for t in join_texts):
                        if rb.is_displayed():
                            rb.click()
                            print(f"  Joined via role=button!")
                            joined = True
                            break
            except Exception:
                pass

        if joined:
            break
        print(f"  Retry {attempt+1}/6 ...")
        time.sleep(3)

    if not joined:
        print("\n  Auto-join nahi hua.")
        input("  Chrome mein manually join karo, phir ENTER dabao: ")
        
        # Strategy 4 — JavaScript se click karo
    if not joined:
        try:
            driver.execute_script("""
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    const txt = btn.innerText.toLowerCase();
                    if (txt.includes('join') || txt.includes('ask')) {
                        btn.click();
                        break;
                    }
                }
            """)
            time.sleep(2)
            print("  Joined via JavaScript!")
            joined = True
        except Exception:
            pass

    time.sleep(3)
    return joined


def record_audio(device_id):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_DIR, f"meeting_{ts}.wav")
    frames   = []

    def _cb(indata, frame_count, time_info, status):
        if status:
            print(f"  [audio warning] {status}")
        frames.append(indata.copy())

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=CHANNELS,
        dtype='int16', device=device_id, callback=_cb,
    )

    print("\n  Recording chal rahi hai ...")
    print("  Meeting khatam hone pe ENTER dabao\n")

    with stream:
        input()

    if not frames:
        print("  Koi audio frame nahi aaya!")
        return None

    audio    = np.concatenate(frames, axis=0)
    duration = len(audio) / SAMPLE_RATE
    wav.write(filename, SAMPLE_RATE, audio)
    print(f"  Saved: {filename}  ({duration:.1f}s)")
    return filename


def upload_recording(meeting_id, transcript, labeled_transcript,
                     summary_data, speaker_segments, audio_file):
    """
    Meeting data .NET API pe upload karo.
    POST /api/meeting/{id}/recording
    """
    if not API_URL:
        print("  API_URL .env mein nahi hai — skip")
        return False
    if not meeting_id:
        print("  meeting_id nahi diya — skip")
        return False

    # Speakers aggregate
    spk_list = []
    if speaker_segments:
        spk_time = defaultdict(float)
        total    = sum(s['duration'] for s in speaker_segments) or 1
        for seg in speaker_segments:
            spk_time[seg['speaker']] += seg['duration']
        for label, dur in spk_time.items():
            spk_list.append({
                "label":      label,
                "duration":   round(dur, 1),
                "percentage": round(dur / total * 100, 1)
            })

    # Duration from WAV file
    duration = 0
    if audio_file and os.path.exists(audio_file):
        try:
            rate, data = wav.read(audio_file)
            duration   = len(data) // rate
        except Exception:
            pass

    payload = {
        "transcript":        transcript         or "",
        "labeledTranscript": labeled_transcript  or "",
        "summary":           json.dumps(summary_data) if summary_data else "{}",
        "speakers":          json.dumps(spk_list),
        "durationSeconds":   duration
    }

    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"

    try:
        print(f"\n  Uploading to API (meeting id: {meeting_id}) ...")
        res = requests.post(
            f"{API_URL}/api/meeting/{meeting_id}/recording",
            json=payload,
            headers=headers,
            timeout=30
        )
        if res.status_code == 200:
            print(f"  Uploaded! Meeting {meeting_id} updated successfully.")
            return True
        else:
            print(f"  Upload failed: {res.status_code} — {res.text}")
    except Exception as e:
        print(f"  Upload error: {e}")

    return False


def run_bot(url):
    print("\n" + "="*55)
    print("   MEETING BOT - PHASE 2")
    print("="*55)

    print("\n[1/3] Audio device dhundh raha hai ...")
    list_all_input_devices()
    device_id = find_best_input_device()

    print("\n[2/3] Chrome khol raha hai ...")
    driver = setup_chrome()
    join_meet(driver, url)

    print("\n[3/3] Recording ...")
    print("-"*55)
    audio_file = record_audio(device_id)
    driver.quit()
    print("\n  Browser band ho gaya.")
    return audio_file


if __name__ == "__main__":
    # Meeting URL
    url = sys.argv[1] if len(sys.argv) > 1 else input(
        "\nGoogle Meet link paste karo:\nURL: ").strip()

    if not url:
        print("URL nahi di!")
        sys.exit(1)

    # Meeting ID for API upload
    meeting_id = os.getenv("MEETING_ID", "").strip()
    if not meeting_id:
        meeting_id = input(
            "Meeting ID daalo (skip karne ke liye Enter dabao): "
        ).strip()

    # Run bot
    audio_file = run_bot(url)

    if audio_file:
        print("\n" + "="*55)
        choice = input(
            "Transcript + Summary + Upload karna hai? (h/n): "
        ).strip().lower()

        if choice == "h":
            from phase1_transcribe import transcribe_audio
            from phase1_summary    import generate_summary
            from phase3_speakers   import diarize_audio, label_transcript

            # Transcribe
            print("\n--- Transcription ---")
            transcript_file, transcript_text = transcribe_audio(audio_file)

            # Summary
            print("\n--- Summary ---")
            summary_data = generate_summary(transcript_text, audio_file)

            # Speaker detection
            print("\n--- Speaker Detection ---")
            speaker_segments = diarize_audio(audio_file, num_speakers=2)

            labeled_text = ""
            if speaker_segments and transcript_file:
                label_transcript(transcript_file, speaker_segments)
                base = os.path.splitext(os.path.basename(audio_file))[0]
                lf = os.path.join("transcripts", "transcript_labeled.txt")

                if os.path.exists(lf):
                    with open(lf, "r", encoding="utf-8") as f:
                        labeled_text = f.read()

            # Upload
            if meeting_id:
                upload_recording(
                    meeting_id         = meeting_id,
                    transcript         = transcript_text,
                    labeled_transcript = labeled_text,
                    summary_data       = summary_data,
                    speaker_segments   = speaker_segments,
                    audio_file         = audio_file
                )
            else:
                print("\n  Meeting ID nahi diya — API upload skip kiya.")

            print("\n" + "="*55)
            print("  ALL DONE!")
            print(f"  Recording  : {audio_file}")
            print(f"  Transcript : {transcript_file}")
            print(f"  Upload     : {'Done' if meeting_id else 'Skipped'}")
            print("="*55)