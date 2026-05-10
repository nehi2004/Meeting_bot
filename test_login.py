import requests, os
from dotenv import load_dotenv
load_dotenv()

API_URL  = os.getenv("API_URL")
EMAIL    = os.getenv("EMAIL") 
PASSWORD = os.getenv("PASSWORD")

# Auth endpoint try karo
for endpoint in ["/api/Auth/login", "/api/Account/login"]:
    print(f"\nTrying: {endpoint}")
    res = requests.post(f"{API_URL}{endpoint}",
        json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text[:200]}")