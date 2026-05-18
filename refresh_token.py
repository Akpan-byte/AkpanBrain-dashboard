#!/usr/bin/env python3
"""Refresh Google OAuth token and update rclone config."""
import json, urllib.request, urllib.parse, configparser

# Read current token
with open("/config/.hermes/google_token.json") as f:
    data = json.load(f)

refresh_token = data.get("refresh_token", "")
client_id = "REDACTED"
client_secret = "REDACTED"

if not refresh_token:
    print("NO REFRESH TOKEN FOUND")
    print("Token keys:", list(data.keys()))
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
        config.read("/config/.config/rclone/rclone.conf")
        new_token = json.dumps({
            "access_token": new_access,
            "token_type": "Bearer",
            "refresh_token": refresh_token,
            "expiry": "2099-01-01T00:00:00+00:00"
        })
        config.set("akpanbrain", "token", new_token)
        with open("/config/.config/rclone/rclone.conf", "w") as f:
            config.write(f)
        print("Rclone config updated")
        
        # Also update google_token.json
        data["token"] = new_access
        data["access_token"] = new_access
        with open("/config/.hermes/google_token.json", "w") as f:
            json.dump(data, f)
        print("google_token.json updated")
        
except Exception as e:
    print("REFRESH FAILED:", str(e)[:300])
