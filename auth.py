"""
auth.py — Upstox OAuth2 authentication.

HOW TO USE (run this ONCE every trading day before starting bot.py):

  Step 1:  python auth.py
           Prints the Upstox authorization URL.

  Step 2:  Open the URL in your browser and log in with your Upstox account.
           After login, Upstox redirects to your redirect_uri with ?code=XXXX
           Copy that code from the browser address bar.

  Step 3:  python auth.py <YOUR_CODE>
           Exchanges the code for an access token and saves it to .env
           Then run:  python bot.py
"""

import sys
import os
import requests
from urllib.parse import urlencode
import config

AUTH_URL  = "https://api.upstox.com/v2/login/authorization/dialog"
TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"


def get_auth_url() -> str:
    params = {
        "client_id":     config.API_KEY,
        "redirect_uri":  config.REDIRECT_URI,
        "response_type": "code",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code(auth_code: str) -> str:
    payload = {
        "code":          auth_code,
        "client_id":     config.API_KEY,
        "client_secret": config.API_SECRET,
        "redirect_uri":  config.REDIRECT_URI,
        "grant_type":    "authorization_code",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept":       "application/json",
    }
    resp = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token", "")
    if not token:
        raise ValueError(f"No token in response: {data}")
    return token


def save_token(token: str):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path) as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if line.startswith("UPSTOX_ACCESS_TOKEN="):
                new_lines.append(f"UPSTOX_ACCESS_TOKEN={token}\n")
                found = True
            else:
                new_lines.append(line)
        lines = new_lines
    if not found:
        lines.append(f"UPSTOX_ACCESS_TOKEN={token}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)
    print(f"[auth] Token saved to {env_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        url = get_auth_url()
        print("\n" + "="*62)
        print("  STEP 1 — Open this URL in your browser:")
        print("="*62)
        print(f"\n  {url}\n")
        print("  Log in with Upstox → Authorize the app.")
        print("  You will be redirected to your redirect_uri URL.")
        print("  COPY the 'code' value from that URL.\n")
        print("  STEP 2 — Then run:  python auth.py <YOUR_CODE>\n")
    else:
        code = sys.argv[1].strip()
        print("[auth] Exchanging code for access token...")
        try:
            token = exchange_code(code)
            save_token(token)
            print(f"[auth] SUCCESS — token starts with: {token[:20]}...")
            print("[auth] Now run:  python bot.py")
        except Exception as e:
            print(f"[auth] FAILED: {e}")
            sys.exit(1)
