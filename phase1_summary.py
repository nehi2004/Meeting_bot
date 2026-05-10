import json
import os
import sys
import subprocess
import threading
import time
import urllib.request
from datetime import datetime

OLLAMA_PATH = r"C:\Users\NEHI\AppData\Local\Programs\Ollama\ollama.exe"


def ensure_ollama_running():
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except:
        print("Ollama server start ho raha hai...")
        threading.Thread(
            target=lambda: subprocess.Popen(
                [OLLAMA_PATH, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ),
            daemon=True
        ).start()
        time.sleep(4)
        try:
            urllib.request.urlopen("http://localhost:11434", timeout=3)
            print("Ollama ready!")
            return True
        except:
            print("Ollama start nahi hua. Manually run karo: ollama serve")
            return False


def generate_summary(transcript_text, meeting_name="Meeting"):
    print("=" * 50)
    print("  AI SUMMARY GENERATOR (FREE - Ollama)")
    print("=" * 50)

    if not ensure_ollama_running():
        return None

    print("Summary bana raha hai... (30-60 seconds lag sakte hain)")

    prompt = f"""Analyze this meeting transcript carefully and extract real information from it.

TRANSCRIPT:
{transcript_text}

Based on the ACTUAL content above, return a JSON object. Use only real information from the transcript, do not use placeholder text.

{{
    "meeting_title": "actual title based on what was discussed",
    "date": "{datetime.now().strftime('%Y-%m-%d')}",
    "summary": "actual 2-3 line summary of what was said",
    "key_points": ["actual point from transcript", "actual point 2"],
    "action_items": [
        {{
            "task": "actual task mentioned or None if not mentioned",
            "assigned_to": "actual person or TBD",
            "deadline": "actual deadline or TBD"
        }}
    ],
    "decisions_made": ["actual decision or None if not mentioned"],
    "next_meeting": "actual next meeting info or TBD"
}}

IMPORTANT: Replace every field with REAL content from the transcript. Never use placeholder words like 'point 1' or 'short title'."""

    request_data = json.dumps({
        "model": "llama3.2",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3}
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=request_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
            raw_response = result.get("response", "")

    except Exception as e:
        print(f"Error: {e}")
        return None

    # JSON clean karo
    raw_response = raw_response.strip()

    if "```json" in raw_response:
        raw_response = raw_response.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_response:
        raw_response = raw_response.split("```")[1].split("```")[0].strip()
    elif "{" in raw_response:
        start = raw_response.index("{")
        end = raw_response.rindex("}") + 1
        raw_response = raw_response[start:end]

    # ✅ Yeh line missing thi — ab fix hai
    try:
        summary_data = json.loads(raw_response)
    except json.JSONDecodeError:
        summary_data = {"raw_summary": raw_response}

    # Print results
    print("\n" + "=" * 50)
    print("  MEETING SUMMARY")
    print("=" * 50)

    if "meeting_title" in summary_data:
        print(f"\nTitle    : {summary_data.get('meeting_title', 'N/A')}")
        print(f"Date     : {summary_data.get('date', 'N/A')}")
        print(f"\nSummary  : {summary_data.get('summary', 'N/A')}")

        print("\nKey Points:")
        for i, point in enumerate(summary_data.get("key_points", []), 1):
            print(f"  {i}. {point}")

        print("\nAction Items:")
        for item in summary_data.get("action_items", []):
            print(f"  - Task     : {item.get('task', 'N/A')}")
            print(f"    Assigned : {item.get('assigned_to', 'TBD')}")
            print(f"    Deadline : {item.get('deadline', 'TBD')}")

        print("\nDecisions Made:")
        for d in summary_data.get("decisions_made", []):
            print(f"  - {d}")

        print(f"\nNext Meeting: {summary_data.get('next_meeting', 'TBD')}")

    else:
        print("\nResponse:")
        print(summary_data.get("raw_summary", ""))

    # Save karo
    base_name = os.path.splitext(os.path.basename(meeting_name))[0]
    output_path = os.path.join("summaries", f"{base_name}_summary.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    print(f"\nSaved: {output_path}")
    return summary_data


if __name__ == "__main__":
    transcripts = sorted(os.listdir("transcripts"))

    valid = []
    for t in transcripts:
        path = os.path.join("transcripts", t)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            valid.append(t)

    if not valid:
        print("Koi valid transcript nahi mili!")
        print("Pehle kuch bolke record karo aur transcribe karo.")
        sys.exit(1)

    latest = os.path.join("transcripts", valid[-1])
    print(f"Using: {latest}\n")

    with open(latest, "r", encoding="utf-8") as f:
        text = f.read()

    generate_summary(text, latest)