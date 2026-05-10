import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = f"{os.getenv('API_URL')}/api/auth/login"

payload = {
    "email": input("Enter HR Email: "),
    "password": input("Enter Password: ")
}

res = requests.post(url, json=payload, timeout=30)

print("Status Code:", res.status_code)

if res.status_code == 200:
    data = res.json()
    token = data.get("token")

    print("\n✅ TOKEN:")
    print(token)

    # OPTIONAL: save token to .env dynamically
    with open(".env", "a") as f:
        f.write(f"\nAPI_TOKEN={token}\n")

else:
    print("❌ Login failed")
    print(res.text)
