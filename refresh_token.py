#!/usr/bin/env python3
"""Refresh Google OAuth token and update rclone config.
Requires env vars: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
"""
import json, urllib.request, urllib.parse, configparser, os

# Read current token
with open(os.path.expanduser("~/.hermes/google_token.json")) as f:
    data = json.load(f)

refresh_token = data.get("refresh_token", "")
client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")

if not refresh_token:
    print("NO REFRESH TOKEN FOUND")
    exit(1)
if not client_id or not client_secret:
    print("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars")
    exit(1)

# Refresh the access token
params = urllib.parse.urlencode({
    "client_id": client_id,
    "client_secret": client_secret,
    "refresh_token": refresh_token,
    "grant_type": "refresh_token"
}).encode()

req = urllib.request.Request("https://oauth2.googleapis.com/token", data=params)
try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        new_access = result.get("access_token", "")
        print("REFRESH SUCCESS")
        print("New access token:", new_access[:30] + "...")
        print("Expires in:", result.get("expires_in", "?"))
        
        # Update rclone config
        config = configparser.ConfigParser()
        config.read(os.path.expanduser("~/.config/rclone/rclone.conf"))
        new_token = json.dumps({
            "access_token": new_access,
            "token_type": "Bearer",
            "refresh_token": refresh_token,
            "expiry": "2099-01-01T00:00:00+00:00"
        })
        config.set("akpanbrain", "token", new_token)
        with open(os.path.expanduser("~/.config/rclone/rclone.conf"), "w") as f:
            config.write(f)
        print("Rclone config updated")
        
        # Also update google_token.json
        data["token"] = new_access
        data["access_token"] = new_access
        with open(os.path.expanduser("~/.hermes/google_token.json"), "w") as f:
            json.dump(data, f)
        print("google_token.json updated")
        
except Exception as e:
    print("REFRESH FAILED:", str(e)[:300])
