import requests
import os
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

API_URL = os.getenv("API_URL")
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# Step 1: Login and get fresh token
login_res = requests.post(
    f"{API_URL}/api/account/login",
    json={
        "email": EMAIL,
        "password": PASSWORD
    },
    timeout=30
)

login_res.raise_for_status()
token = login_res.json()["token"]

# Step 2: Get meetings
res = requests.get(
    f"{API_URL}/api/meeting/my-meetings",
    headers={"Authorization": f"Bearer {token}"},
    timeout=30
)

res.raise_for_status()
meetings = res.json()

print("Now IST:", datetime.now(ZoneInfo("Asia/Kolkata")))
print("Total meetings:", len(meetings))

for m in meetings:
    print(m["id"], "-", m["title"])