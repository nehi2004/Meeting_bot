import smtplib
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
load_dotenv()

SENDER_EMAIL    = os.getenv("EMAIL_SENDER")
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD")



def send_meeting_summary_email(
    to_emails: list,
    meeting_title: str,
    summary_data: dict,
    transcript: str = "",
    labeled_transcript: str = ""
):

    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
    SENDER_EMAIL = os.getenv("EMAIL_SENDER")

    if not SENDGRID_API_KEY:
        print("SendGrid API key missing!")
        return False

    if not to_emails:
        print("No recipients!")
        return False

    # ── Parse summary ──
    if isinstance(summary_data, str):
        try:
            summary_data = json.loads(summary_data)
        except:
            summary_data = {}

    title    = summary_data.get("meeting_title", meeting_title)
    summary  = summary_data.get("summary", "N/A")
    kp       = summary_data.get("key_points", [])
    actions  = summary_data.get("action_items", [])
    decisions= summary_data.get("decisions_made", [])
    next_mtg = summary_data.get("next_meeting", "TBD")
    date     = summary_data.get("date", "")

    # ── Build HTML safely ──
    key_points_html = "".join([f"<li>{p}</li>" for p in kp]) if kp else ""
    actions_html = "".join([
        f"<li>{a.get('task')} - {a.get('assigned_to')} ({a.get('deadline')})</li>"
        for a in actions
    ]) if actions else ""
    decisions_html = "".join([f"<li>{d}</li>" for d in decisions]) if decisions else ""

    transcript_html = ""
    if labeled_transcript:
        short = labeled_transcript[:2000] + ("..." if len(labeled_transcript) > 2000 else "")
        transcript_html = f"<pre>{short}</pre>"

    html = f"""
    <h2>📋 {title}</h2>
    <p><b>Date:</b> {date}</p>

    <h3>Summary</h3>
    <p>{summary}</p>

    {f"<h3>Key Points</h3><ul>{key_points_html}</ul>" if key_points_html else ""}

    {f"<h3>Action Items</h3><ul>{actions_html}</ul>" if actions_html else ""}

    {f"<h3>Decisions</h3><ul>{decisions_html}</ul>" if decisions_html else ""}

    <h3>Next Meeting</h3>
    <p>{next_mtg}</p>

    {transcript_html}
    """

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)

        message = Mail(
            from_email=SENDER_EMAIL,
            to_emails=to_emails,
            subject=f"Meeting Summary: {title}",
            html_content=html
        )

        response = sg.send(message)

        print("Email sent via SendGrid!", response.status_code)
        return True

    except Exception as e:
        print("SendGrid error:", e)
        return False
def get_participant_emails(meeting_id, API_URL, API_TOKEN):
    import requests

    try:
        # ✅ Step 1: Meeting detail
        detail_res = requests.get(
            f"{API_URL}/api/Meeting/{meeting_id}/detail",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            timeout=15
        )

        if detail_res.status_code != 200:
            print("❌ Meeting detail failed:", detail_res.status_code)
            return []

        data = detail_res.json()

        participant_ids = data.get("participantIds", [])
        organizer_email = data.get("organizerEmail")

        if not participant_ids:
            print("⚠️ No participants found")
        
        # ✅ Step 2: Get ALL users
        users_res = requests.get(
            f"{API_URL}/api/Meeting/users",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            timeout=15
        )

        if users_res.status_code != 200:
            print("❌ Users fetch failed:", users_res.status_code)
            return []

        users = users_res.json()

        emails = []

        # ✅ Match users with participants
        for u in users:
            if u["id"] in participant_ids:
                if u.get("email"):
                    emails.append(u["email"])
                    print(f"✅ Found: {u['email']}")

        # ✅ Add organizer email
        if organizer_email and organizer_email not in emails:
            emails.append(organizer_email)
            print(f"✅ Organizer: {organizer_email}")

        # ✅ Remove duplicates
        final_emails = list(set(emails))

        print(f"📧 Total emails: {final_emails}")
        return final_emails

    except Exception as e:
        print("❌ Email fetch error:", e)
        return []
