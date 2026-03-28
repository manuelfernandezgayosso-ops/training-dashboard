#!/usr/bin/env python3
"""
Startup sync — runs once when Render boots the app.
Pulls Strava data using the refresh token from env vars.
"""

import os, json, time, requests
from pathlib import Path

DATA_DIR      = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(exist_ok=True)
CLIENT_ID     = os.getenv("STRAVA_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "")
REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN", "")
TOKEN_FILE    = DATA_DIR / ".strava_token.json"


def bootstrap_token():
    """Create a token file from the environment refresh token."""
    if not REFRESH_TOKEN:
        print("No STRAVA_REFRESH_TOKEN set — skipping bootstrap")
        return False

    if TOKEN_FILE.exists():
        print("Token file already exists")
        return True

    # Exchange refresh token for a full token object
    r = requests.post("https://www.strava.com/oauth/token", data={
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type":    "refresh_token",
        "refresh_token": REFRESH_TOKEN,
    })
    if r.status_code == 200:
        token = r.json()
        with open(TOKEN_FILE, "w") as f:
            json.dump(token, f, indent=2)
        print(f"✓ Token bootstrapped from environment")
        return True
    else:
        print(f"✗ Token bootstrap failed: {r.status_code} {r.text}")
        return False


if __name__ == "__main__":
    bootstrap_token()
