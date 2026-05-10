"""
auto_scheduler.py
==================
Background mein chalti hai.
Har 90 sec mein API check karta hai.
Meeting start time pe bot automatically join karta hai.
"""

import time
import os
import json
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ══════════════════════════════════════════════
#  LOAD ENV
# ══════════════════════════════════════════════
env_path = Path(r"C:\meeting-ai-agent\.env")
load_dotenv(dotenv_path=env_path, override=True)

API_URL     = os.getenv("API_URL", "")
API_TOKEN   = os.getenv("API_TOKEN", "")
EMAIL       = os.getenv("EMAIL", "")
PASSWORD    = os.getenv("PASSWORD", "")
OUTPUT_DIR  = "recordings"
SAMPLE_RATE = 16000
CHANNELS    = 1

# ══════════════════════════════════════════════
#  GLOBALS
# ══════════════════════════════════════════════
processed_meetings   = set()
active_meetings      = {}
active_meetings_lock = threading.Lock()


# ══════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════
def fresh_login():
    global API_TOKEN
    try:
        print("[Auth] Trying login...")
        print("[Auth] Email:", EMAIL)
        res = requests.post(
            f"{API_URL}/api/Account/login",
            json={"email": EMAIL, "password": PASSWORD},
            timeout=20
        )
        print("[Auth] Status:", res.status_code)
        res.raise_for_status()
        API_TOKEN = res.json()["token"]
        print("[Auth] Fresh token mil gaya")
        return True
    except Exception as e:
        print("[Auth] Login failed:", e)
        return False


def headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_TOKEN}"
    }


# ══════════════════════════════════════════════
#  TIME HELPERS
# ══════════════════════════════════════════════
def parse_dt(s):
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo("Asia/Kolkata"))


# ══════════════════════════════════════════════
#  FETCH MEETINGS
# ══════════════════════════════════════════════
def fetch_meetings():
    global API_TOKEN
    url = f"{API_URL}/api/meeting/my-meetings"
    for attempt in range(10):
        try:
            res = requests.get(url, headers=headers(), timeout=30)
            if res.status_code == 401:
                print("[Auth] Token expired. Re-login...")
                if fresh_login():
                    continue
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"[Scheduler] Retry {attempt+1}/10: {e}")
            time.sleep(5)
    print("[Scheduler] Failed to fetch meetings after retries")
    return []


# ══════════════════════════════════════════════
#  AUDIO
# ══════════════════════════════════════════════
def find_audio_device():
    devices = sd.query_devices()
    for keyword in ['stereo mix', 'cable output', 'microphone array', 'microphone']:
        for i, dev in enumerate(devices):
            if keyword in dev['name'].lower() and dev['max_input_channels'] > 0:
                try:
                    sd.rec(int(0.1 * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                           channels=1, dtype='int16', device=i)
                    sd.wait()
                    print(f"  Audio device: [{i}] {dev['name']}")
                    return i
                except Exception:
                    continue
    return None


# ══════════════════════════════════════════════
#  CHROME
# ══════════════════════════════════════════════
def setup_chrome():
    profile_dir = r"C:\meeting-ai-agent\chrome_profile"

    for f in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        try:
            path = os.path.join(profile_dir, f)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_mic":    1,
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.notifications":       2,
    })
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def mute_bot(driver):
    for aria in ["microphone", "mic", "camera", "video"]:
        try:
            for b in driver.find_elements(By.XPATH,
                    f"//button[contains(@aria-label,'{aria}')]"):
                label = (b.get_attribute("aria-label") or "").lower()
                if "off" not in label and b.is_displayed():
                    b.click()
                    time.sleep(0.8)
                    break
        except Exception:
            pass


def join_meet(driver, url):
    print(f"  Chrome: {url}")
    driver.get(url)
    time.sleep(10)
    mute_bot(driver)

    for i in range(5):
        try:
            buttons = driver.find_elements(By.XPATH, "//button")
            for b in buttons:
                txt = (b.text or "").lower()
                if any(x in txt for x in ["join now", "ask to join", "join"]):
                    b.click()
                    print("  Join button clicked")
                    break
        except Exception:
            pass
        time.sleep(3)

    print("  Waiting for join confirmation...")
    for _ in range(20):
        try:
            url_now = driver.current_url
            if "/call/" in url_now:
                print("  CONFIRMED: Meeting joined")
                return True
            leave_btn = driver.find_elements(By.XPATH,
                "//button[contains(@aria-label,'leave') or contains(@aria-label,'Leave')]")
            if leave_btn:
                print("  CONFIRMED: Meeting joined")
                return True
        except Exception:
            pass
        time.sleep(2)

    print("  Join detect nahi hua (recording chalegi)")
    return False


def leave_meet(driver):
    try:
        leave_xpaths = [
            "//button[contains(@aria-label,'leave') or contains(@aria-label,'Leave')]",
            "//button[contains(@aria-label,'hang up') or contains(@aria-label,'Hang up')]",
            "//button[contains(@data-tooltip,'Leave')]",
        ]
        for xpath in leave_xpaths:
            try:
                btns = driver.find_elements(By.XPATH, xpath)
                for btn in btns:
                    if btn.is_displayed():
                        btn.click()
                        print("  Left meeting via button")
                        time.sleep(2)
                        return
            except Exception:
                pass

        driver.execute_script("""
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                const t = (b.innerText + (b.getAttribute('aria-label') || '')).toLowerCase();
                if (t.includes('leave') || t.includes('hang')) { b.click(); break; }
            }
        """)
        print("  Left meeting via JS")
        time.sleep(2)
    except Exception as e:
        print(f"  Leave error (ok): {e}")


# ══════════════════════════════════════════════
#  UPLOAD
# ══════════════════════════════════════════════
def upload_recording(meeting_id, transcript, labeled_transcript,
                     summary_data, speaker_segments, audio_file):
    from collections import defaultdict

    spk_list = []
    if speaker_segments:
        spk_time = defaultdict(float)
        total = sum(s['duration'] for s in speaker_segments) or 1
        for seg in speaker_segments:
            spk_time[seg['speaker']] += seg['duration']
        for label, dur in spk_time.items():
            spk_list.append({
                "label":      label,
                "duration":   round(dur, 1),
                "percentage": round(dur / total * 100, 1)
            })

    duration = 0
    if audio_file and os.path.exists(audio_file):
        try:
            rate, data = wav.read(audio_file)
            duration = len(data) // rate
        except Exception:
            pass

    payload = {
        "transcript":        transcript         or "",
        "labeledTranscript": labeled_transcript  or "",
        "summary":           json.dumps(summary_data) if summary_data else "{}",
        "speakers":          json.dumps(spk_list),
        "durationSeconds":   duration
    }

    print(f"\n  Uploading meeting {meeting_id} ...")
    for attempt in range(5):
        try:
            res = requests.post(
                f"{API_URL}/api/meeting/{meeting_id}/recording",
                json=payload, headers=headers(), timeout=30
            )
            if res.ok:
                print(f"  Uploaded! Meeting {meeting_id} updated.")
                return True
            elif res.status_code == 401:
                print("  Token expired. Re-login...")
                if fresh_login():
                    continue
            else:
                print(f"  Upload failed ({attempt+1}/5): {res.status_code}")
        except Exception as e:
            print(f"  Upload error ({attempt+1}/5): {e}")
        time.sleep(5)

    print("  Final upload failed")
    return False


# ══════════════════════════════════════════════
#  MAIN PIPELINE
# ══════════════════════════════════════════════
def run_pipeline(meeting):
    meeting_id = str(meeting.get("id"))

    with active_meetings_lock:
        if meeting_id in active_meetings:
            print(f"Meeting {meeting_id} already running")
            return
        active_meetings[meeting_id] = True

    try:
        title    = meeting.get("title", "Meeting")
        link     = meeting.get("meetingLink") or meeting.get("meeting_link", "")
        end_str  = meeting.get("endTime") or meeting.get("end_time", "")
        end_time = parse_dt(end_str)

        print(f"\n{'='*60}")
        print(f"  BOT STARTED: {title} (ID: {meeting_id})")
        print(f"  Link: {link}")
        print(f"  End:  {end_time}")
        print(f"{'='*60}")

        device_id = find_audio_device()
        driver    = setup_chrome()

        join_thread = threading.Thread(target=join_meet, args=(driver, link), daemon=True)
        join_thread.start()
        join_thread.join(timeout=60)

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(OUTPUT_DIR, f"meeting_{ts}.wav")
        frames   = []

        def audio_callback(indata, frame_count, time_info, status):
            frames.append(indata.copy())

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=CHANNELS,
            dtype="int16", device=device_id, callback=audio_callback
        )

        print("\n  Recording shuru...")

        with stream:
            while True:
                now = datetime.now(ZoneInfo("Asia/Kolkata"))
                if end_time and now >= end_time:
                    print(f"  [{meeting_id}] End time reached")
                    break
                try:
                    if "meet.google.com" not in driver.current_url:
                        print(f"  [{meeting_id}] Meeting closed")
                        break
                except Exception:
                    break
                time.sleep(10)

        try:
            leave_meet(driver)
            driver.quit()
        except Exception:
            pass

        print(f"  [{meeting_id}] Browser closed")

        if not frames:
            print(f"  [{meeting_id}] No audio recorded!")
            return

        audio = np.concatenate(frames, axis=0)
        wav.write(filename, SAMPLE_RATE, audio)
        print(f"  [{meeting_id}] Saved: {filename}")

        # Transcription
        from phase1_transcribe import transcribe_audio
        transcript_file, transcript_text = transcribe_audio(filename)

        # Summary
        from phase1_summary import generate_summary
        summary_data = generate_summary(transcript_text, filename)

        # Speaker Detection
        from phase3_speakers import diarize_audio, label_transcript
        participant_ids   = meeting.get("participantIds") or meeting.get("participant_ids") or []
        participant_count = max(2, min(len(participant_ids) or 2, 5))
        print(f"\n  Participants: {participant_ids}")
        print(f"  Speakers used: {participant_count}")
        speaker_segments = diarize_audio(filename, num_speakers=participant_count)

        labeled_text = ""
        if speaker_segments and transcript_file:
            label_transcript(transcript_file, speaker_segments)
            base = os.path.splitext(os.path.basename(filename))[0]
            lf   = os.path.join("transcripts", f"{base}_labeled.txt")
            if os.path.exists(lf):
                with open(lf, "r", encoding="utf-8") as f:
                    labeled_text = f.read()

        # Upload
        print(f"\n--- Uploading ({meeting_id}) ---")
        upload_recording(meeting_id, transcript_text, labeled_text,
                         summary_data, speaker_segments, filename)

        # Email
        print(f"\n--- Sending Email ({meeting_id}) ---")
        try:
            from phase4_email import send_meeting_summary_email, get_participant_emails
            recipient_emails = get_participant_emails(meeting_id, API_URL, API_TOKEN)
            if not recipient_emails:
                fallback = os.getenv("EMAIL_SENDER")
                if fallback:
                    recipient_emails = [fallback]
            if recipient_emails:
                send_meeting_summary_email(
                    to_emails=recipient_emails,
                    meeting_title=title,
                    summary_data=summary_data,
                    labeled_transcript=labeled_text
                )
                print(f"  Email sent to {recipient_emails}")
        except Exception as e:
            print(f"  Email error: {e}")

        print(f"\n  ALL DONE! Meeting {meeting_id}")
        processed_meetings.add(meeting_id)

    except Exception as e:
        print(f"[Pipeline Error {meeting_id}] {e}")
        import traceback
        traceback.print_exc()

    finally:
        with active_meetings_lock:
            active_meetings.pop(meeting_id, None)


# ══════════════════════════════════════════════
#  SCHEDULER LOOP
# ══════════════════════════════════════════════
def scheduler_loop():
    print("=" * 60)
    print("  AUTO MEETING BOT SCHEDULER")
    print("=" * 60)

    # Internet check
    print("[Startup] Internet check kar raha hai...")
    for i in range(30):
        try:
            requests.get("https://google.com", timeout=5)
            print("[Startup] Internet connected!")
            break
        except Exception:
            print(f"[Startup] Waiting for internet... ({i+1}/30)")
            time.sleep(10)

    # Login
    print("[Startup] Logging in...")
    if not fresh_login():
        print("Login failed! .env check karo")
        return
    print("[Startup] Login successful!\n")

    print("Har 90 sec mein upcoming meetings check hogi.")
    print("Jab meeting start ho → bot auto join karega.")
    print("Ctrl+C se band karo.\n")

    while True:
        try:
            meetings = fetch_meetings()
            now      = datetime.now(ZoneInfo("Asia/Kolkata"))

            print(f"\nMeetings fetched: {len(meetings)}")

            active = [m for m in meetings if not m.get("hasRecording", False)]

            for meeting in active:
                mid      = meeting.get("id")
                start_dt = parse_dt(meeting.get("startTime") or meeting.get("start_time"))
                end_dt   = parse_dt(meeting.get("endTime") or meeting.get("end_time"))
                link     = meeting.get("meetingLink") or meeting.get("meeting_link", "")

                print(f"[DEBUG] {mid} | Start: {start_dt} | End: {end_dt} | Now: {now}")

                if not link or not start_dt:
                    continue

                if mid in processed_meetings:
                    continue

                with active_meetings_lock:
                    if str(mid) in active_meetings:
                        print(f"Meeting {mid} already running")
                        continue

                if end_dt and now >= end_dt:
                    continue

                join_at = start_dt - timedelta(minutes=2)

                if now >= join_at and (not end_dt or now <= end_dt):
                    print(f"\n[{now.strftime('%H:%M:%S')}] Joining: {meeting.get('title')} (ID:{mid})")
                    processed_meetings.add(mid)
                    threading.Thread(
                        target=run_pipeline,
                        args=(meeting,),
                        daemon=True
                    ).start()
                else:
                    mins = int((start_dt - now).total_seconds() / 60)
                    print(f"[{now.strftime('%H:%M:%S')}] '{meeting.get('title')}' (ID:{mid}) — {mins} min mein")

        except KeyboardInterrupt:
            print("\nScheduler stopped")
            break
        except Exception as e:
            print(f"Scheduler error: {e}")

        time.sleep(90)


if __name__ == "__main__":
    scheduler_loop()