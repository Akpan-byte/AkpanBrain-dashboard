#!/usr/bin/env python3
"""Upload snapshot to Google Drive"""
import json, urllib.request, os, time

creds = json.load(open('/config/.hermes/google_token.json'))
# Try multiple token field names
token = creds.get('access_token') or creds.get('token') or ''
if not token:
    # Refresh first
    import urllib.parse
    data = urllib.parse.urlencode({
        'grant_type': 'refresh_token',
        'refresh_token': creds['refresh_token'],
        'client_id': creds['client_id'],
        'client_secret': creds['client_secret']
    }).encode()
    req = urllib.request.Request(creds['token_uri'], data=data)
    resp = urllib.request.urlopen(req, timeout=10)
    new_tokens = json.loads(resp.read())
    token = new_tokens['access_token']
    creds.update(new_tokens)
    with open('/config/.hermes/google_token.json', 'w') as f:
        json.dump(creds, f)
    print("Token refreshed")
    
headers_auth = {'Authorization': 'Bearer ' + token}
# Test token
try:
    req = urllib.request.Request('https://www.googleapis.com/drive/v3/about?fields=user', headers=headers_auth)
    resp = urllib.request.urlopen(req, timeout=10)
    about = json.loads(resp.read())
    print(f"Authenticated as: {about.get('user',{}).get('emailAddress','?')}")
except Exception as e:
    print(f"Auth test failed: {e}")
    exit(1)

# Find AkpanBrain folder
url = 'https://www.googleapis.com/drive/v3/files?q=name=%27AkpanBrain%27+and+trashed=false&fields=files(id,name)&spaces=drive'
req = urllib.request.Request(url, headers=headers_auth)
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read())
folders = data.get('files', [])
if not folders:
    print("No AkpanBrain folder found!")
    exit()

folder_id = folders[0]['id']
print(f"AkpanBrain folder: {folder_id}")

# Create/find snapshots subfolder
def find_or_create(name, parent):
    url = f"https://www.googleapis.com/drive/v3/files?q=name=%27{name}%27+and+%27{parent}%27+in+parents+and+mimeType=%27application/vnd.google-apps.folder%27+and+trashed=false&fields=files(id,name)"
    req = urllib.request.Request(url, headers=headers_auth)
    resp = urllib.request.urlopen(req, timeout=10)
    existing = json.loads(resp.read()).get('files', [])
    if existing:
        print(f"Found existing: {name} → {existing[0]['id']}")
        return existing[0]['id']
    meta = json.dumps({'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent]}).encode()
    req = urllib.request.Request('https://www.googleapis.com/drive/v3/files', data=meta, headers={**headers_auth, 'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req, timeout=10)
    result = json.loads(resp.read())
    print(f"Created: {name} → {result['id']}")
    return result['id']

snap_id = find_or_create('snapshots', folder_id)
v5_id = find_or_create('v5-neural-mvp', snap_id)

# Upload files
files_to_upload = [
    ('/config/brain/dashboard/snapshots/v5-neural-mvp/README.md', 'text/plain'),
    ('/config/brain/dashboard/snapshots/v5-neural-mvp/index.html', 'text/html'),
    ('/config/brain/dashboard/snapshots/v5-neural-mvp/index_built.html', 'text/html'),
    ('/config/brain/dashboard/snapshots/v5-neural-mvp/build.py', 'text/x-python'),
    ('/config/brain/dashboard/snapshots/v5-neural-mvp/api_server_v4.py', 'text/x-python'),
]

for fpath, mime in files_to_upload:
    fname = os.path.basename(fpath)
    fsize = os.path.getsize(fpath)
    
    boundary = '-------314159265358979323846'
    parts = []
    parts.append('--' + boundary)
    parts.append('Content-Type: application/json; charset=UTF-8')
    parts.append('')
    parts.append(json.dumps({"name": fname, "parents": [v5_id]}))
    parts.append('--' + boundary)
    parts.append('Content-Type: ' + mime)
    parts.append('')
    
    body = '\r\n'.join(parts).encode() + b'\r\n'
    with open(fpath, 'rb') as f:
        body += f.read()
    body += ('\r\n--' + boundary + '--\r\n').encode()
    
    req = urllib.request.Request(
        'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
        data=body,
        headers={**headers_auth, 'Content-Type': 'multipart/related; boundary=' + boundary}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        print(f"✅ {fname} ({fsize} bytes) → {result['id']}")
    except Exception as e:
        print(f"❌ {fname}: {e}")

print("\nDone! Snapshot saved to Google Drive → AkpanBrain/snapshots/v5-neural-mvp/")
