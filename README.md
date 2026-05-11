
# 🤖 AI Meeting Bot — CalChat+

An intelligent Python-based meeting bot that **automatically joins Google Meet**, records audio, generates AI transcripts and summaries, detects speakers, uploads everything to the backend, and emails all participants — completely hands-free.

---

## 📌 Overview

The AI Meeting Bot is a background automation service built for the **CalChat+ HR Management Platform**. Once running on a local PC, it monitors scheduled meetings via the CalChat+ API and handles the entire meeting lifecycle automatically — from joining to emailing the summary.

```
HR creates a meeting on CalChat+ website
        ↓
Bot detects it (polls every 90 seconds)
        ↓
Bot joins Google Meet 2 minutes before start
        ↓
Records audio silently via VB-Cable
        ↓
On meeting end → auto leaves
        ↓
Transcription → Summary → Speaker Detection
        ↓
Uploads to backend → updates database
        ↓
Emails all participants with full summary
        ↓
"View Details" appears on website
```

---

## 🚀 Features

- **Auto Join** — Joins Google Meet automatically at scheduled time using Selenium
- **Silent Recording** — Captures meeting audio via VB-Cable virtual audio driver
- **AI Transcription** — Converts speech to text using faster-whisper (runs 100% locally, free)
- **AI Summary** — Generates structured JSON summary using Ollama llama3.2 (runs 100% locally, free)
- **Speaker Detection** — Identifies and labels speakers using librosa MFCC + KMeans clustering
- **Auto Upload** — Sends transcript, summary, and speaker data to the .NET API
- **Auto Email** — Sends a beautiful HTML summary email to all meeting participants via SendGrid
- **Multiple Meetings** — Handles simultaneous meetings from different HRs using threading
- **Auto Startup** — Starts automatically when Windows boots via Task Scheduler
- **Token Refresh** — Automatically re-authenticates when JWT token expires

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Browser Automation | Selenium + ChromeDriver |
| Audio Capture | sounddevice + VB-Cable |
| Speech to Text | faster-whisper (Whisper base model) |
| AI Summary | Ollama llama3.2 (local LLM) |
| Speaker Detection | librosa + scikit-learn KMeans |
| Email Delivery | SendGrid API |
| Backend API | .NET Core (CalChat+ Railway) |
| Database | Supabase (PostgreSQL) |
| Scheduling | Windows Task Scheduler |

---

## 📁 File Structure

```
meeting-ai-agent/
│
├── auto_scheduler.py        # Main bot — runs in background, polls API, manages pipeline
├── phase1_transcribe.py     # Speech-to-text using faster-whisper
├── phase1_summary.py        # AI summary generation using Ollama llama3.2
├── phase2_bot.py            # Manual bot runner (for testing)
├── phase3_speakers.py       # Speaker diarisation using MFCC + KMeans
├── phase4_email.py          # HTML email via SendGrid
│
├── recordings/              # Saved WAV files from meetings
├── transcripts/             # Generated transcript text files
├── summaries/               # Generated JSON summary files
├── chrome_profile/          # Persistent Chrome profile (keeps Google login)
│
├── .env                     # Environment variables (not committed)
├── start_bot.bat            # Windows startup batch file
└── requirements.txt         # Python dependencies
```

---

## ⚙️ Setup & Installation

### Prerequisites

- Windows PC (bot requires display + audio hardware)
- Python 3.10+
- Google Chrome installed
- [VB-Cable](https://vb-audio.com/Cable/) virtual audio driver
- [Ollama](https://ollama.ai/) with llama3.2 model
- CalChat+ backend running on Railway

### 1. Clone and Install

```bash
git clone https://github.com/your-repo/meeting-ai-agent.git
cd meeting-ai-agent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure `.env`

```env
API_URL=https://your-railway-backend.up.railway.app
EMAIL=hr@yourcompany.com
PASSWORD=YourPassword123
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxx
EMAIL_SENDER=verified@yourdomain.com
```

### 3. Install Ollama Model

```bash
ollama pull llama3.2
```

### 4. Setup Chrome Profile (One-Time Google Login)

```bash
"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --user-data-dir="C:\meeting-ai-agent\chrome_profile" --profile-directory=Default
```

Sign in to your Google account in the Chrome window that opens, then close it. The bot will reuse this session automatically.

### 5. Configure Audio Routing

In Windows Volume Mixer / Sound Settings:
- Set Chrome audio **output** → **CABLE Input**
- Python bot reads from **CABLE Output**

### 6. Run the Bot

```bash
venv\Scripts\activate
python auto_scheduler.py
```

### 7. Auto-Start on Windows Boot (Optional)

```bash
schtasks /create /tn "MeetingBot" /tr "\"C:\meeting-ai-agent\venv\Scripts\python.exe\" \"C:\meeting-ai-agent\auto_scheduler.py\"" /sc onlogon /rl highest /f
```

---

## 🔄 How It Works

### 1. Scheduler Loop
`auto_scheduler.py` runs continuously and polls `GET /api/meeting/my-meetings` every 90 seconds. It checks for upcoming meetings that do not yet have a recording.

### 2. Meeting Detection
When a meeting's start time is within 2 minutes, the bot spawns a new thread and begins the pipeline for that meeting.

### 3. Chrome Join
A Chrome instance opens using the saved profile (already logged into Google). Selenium navigates to the Google Meet link and clicks the Join button using multiple fallback strategies.

### 4. Audio Recording
While the bot is in the meeting, `sounddevice` records audio from **CABLE Output** — the virtual audio device that captures Chrome's audio output. This captures everything said in the meeting.

### 5. Auto Leave
The bot monitors the meeting end time and leaves automatically. It also detects if the browser navigates away from `meet.google.com` as a secondary signal.

### 6. Transcription
`faster-whisper` (base model, CPU) converts the recorded WAV file to text. Language is auto-detected to support both Hindi and English. VAD filtering removes silence.

### 7. Summary Generation
The transcript is sent to Ollama llama3.2 running locally. The model returns a structured JSON object containing:
- Meeting title and date
- Summary paragraph
- Key points list
- Action items (task, assigned to, deadline)
- Decisions made
- Next meeting date

### 8. Speaker Detection
`librosa` extracts 13 MFCC coefficients per audio frame (1 frame = 0.25 seconds). KMeans clustering groups frames by speaker voice characteristics. The result is a labeled transcript showing which speaker said what.

### 9. Upload
The bot POSTs all data to `POST /api/meeting/{id}/recording`. The backend stores it in Supabase and sets `has_recording = true`, which triggers the **Recording Ready** badge on the frontend.

### 10. Email
`SendGrid` sends an HTML email to all meeting participants. The email includes the full summary, action items, key decisions, speaker breakdown, and transcript excerpt.

---

## 📧 Email Output Example

The auto-generated email includes:

```
📋 Meeting Title — Date

Summary:
  Short paragraph describing what was discussed.

Key Points:
  • Point 1
  • Point 2

Action Items:
  • Task description — Assigned To — Deadline

Decisions Made:
  • Decision 1

Next Meeting: April 28th

Transcript:
  Speaker_1: Hello, good morning...
  Speaker_2: Let's start the review...
```

---

## 🔒 Environment Variables

| Variable | Description |
|----------|-------------|
| `API_URL` | CalChat+ backend base URL |
| `EMAIL` | HR login email for the bot |
| `PASSWORD` | HR login password for the bot |
| `SENDGRID_API_KEY` | SendGrid API key for email sending |
| `EMAIL_SENDER` | Verified sender email in SendGrid |

---

## 📊 AI/ML Details

### Speech Recognition — faster-whisper
- Model: `base` (good balance of speed and accuracy)
- Runs entirely on CPU — no GPU needed
- `language=None` for automatic language detection
- `vad_filter=True` removes silence before processing
- Free — no API calls, no cost

### Text Summarization — Ollama llama3.2
- Runs entirely locally
- Prompted to return structured JSON output
- No internet connection required after initial download
- Free — no API calls, no cost

### Speaker Diarisation — librosa + KMeans
- 13 MFCC features extracted per 0.25-second frame
- Features normalised with StandardScaler
- KMeans clustering (k = number of meeting participants, clamped 2–5)
- Sliding window smoothing reduces label flickering
- Short segments (< 1.5 seconds) merged into neighbours

---

## ⚠️ Known Limitations

- Bot must run on a **local Windows PC** — cloud deployment is not supported due to audio hardware requirements
- Only **one meeting per bot instance** at a time (multiple meetings handled via threading)
- Chrome must not be fully closed/killed while a meeting is running
- Transcription accuracy depends on audio quality and VB-Cable routing

---

## 🔮 Future Improvements

- [ ] RAG Memory — ask AI questions about past meetings
- [ ] Google Calendar integration — auto-detect meetings
- [ ] Real-time live transcript during meetings
- [ ] Speaker name mapping (Speaker_1 → "Rahul")
- [ ] Cloud deployment using Docker + virtual display + PulseAudio

---

## 🧩 Integration with CalChat+

This bot is part of the **CalChat+ HR Management Platform**:

| Layer | Technology | Hosting |
|-------|-----------|---------|
| Frontend | Next.js + React + Tailwind CSS | Vercel |
| Backend API | .NET Core Web API | Railway |
| Database | PostgreSQL | Supabase |
| **Bot** | **Python** | **Local PC** |

The bot communicates exclusively through the CalChat+ REST API using JWT authentication. It does not access the database directly.

---

## 📄 License

This project is part of the CalChat+ platform. All rights reserved.