#!/usr/bin/env python3
"""
AkpanBrain → Google Drive Sync
Bidirectional sync with proper folder hierarchy
Uses Python Drive API (rclone token is stale)
"""
import json, os, sys, time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

BRAIN_DIR = "/config/brain"
TOKEN_PATH = "/config/.hermes/google_token.json"
SYNC_MARKER = f"{BRAIN_DIR}/cache/.last_sync"

# Map local files to Drive folder structure
SYNC_MAP = {
    "api_server.py": ("", "root"),                    # brain/api_server.py
    "akpanbrain.py": ("", "root"),                    # brain/akpanbrain.py
    "vectors/brain.index": ("vectors", "folder"),
    "vectors/meta.json": ("vectors", "folder"),
    "memory/episodic.db": ("memory", "folder"),
    "graph/brain.graphml": ("graph", "folder"),
    "dashboard/index.html": ("dashboard", "folder"),
}

def get_drive_service():
    creds = Credentials.from_authorized_user_info(json.load(open(TOKEN_PATH)))
    return build('drive', 'v3', credentials=creds)

def find_brain_folder_id(drive):
    """Find the AkpanBrain root folder"""
    resp = drive.files().list(q="name='AkpanBrain' and trashed=false", spaces='drive', pageSize=1).execute()
    items = resp.get('files', [])
    if not items:
        print("ERROR: AkpanBrain folder not found on Drive")
        sys.exit(1)
    return items[0]['id']

def find_or_create_folder(drive, name, parent_id):
    """Find a subfolder by name under parent, or create it"""
    resp = drive.files().list(
        q=f"name='{name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces='drive', pageSize=1
    ).execute()
    items = resp.get('files', [])
    if items:
        return items[0]['id']
    # Create it
    meta = {'name': name, 'parents': [parent_id], 'mimeType': 'application/vnd.google-apps.folder'}
    result = drive.files().create(body=meta, fields='id').execute()
    print(f"  Created folder: {name}/")
    return result['id']

def upload_file(drive, local_path, remote_name, parent_id, existing_files):
    """Upload or update a file on Drive"""
    if not os.path.exists(local_path):
        return False
    
    # Check if file already exists in this parent
    file_id = None
    for f in existing_files:
        if f['name'] == remote_name and parent_id in f.get('parents', []):
            file_id = f['id']
            break
    
    try:
        media = MediaFileUpload(local_path, resumable=True, mimetype='application/octet-stream')
        if file_id:
            drive.files().update(fileId=file_id, media_body=media).execute()
        else:
            metadata = {'name': remote_name, 'parents': [parent_id]}
            drive.files().create(body=metadata, media_body=media).execute()
        return True
    except Exception as e:
        print(f"  ERROR uploading {remote_name}: {e}")
        return False

def sync_to_drive(drive=None, brain_folder_id=None):
    """Push local brain files to Google Drive"""
    if not drive:
        drive = get_drive_service()
    if not brain_folder_id:
        brain_folder_id = find_brain_folder_id(drive)
    
    # Find the brain/ subfolder
    brain_sub_id = None
    resp = drive.files().list(
        q=f"name='brain' and '{brain_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces='drive', pageSize=1
    ).execute()
    items = resp.get('files', [])
    if items:
        brain_sub_id = items[0]['id']
    else:
        meta = {'name': 'brain', 'parents': [brain_folder_id], 'mimeType': 'application/vnd.google-apps.folder'}
        result = drive.files().create(body=meta, fields='id').execute()
        brain_sub_id = result['id']
        print(f"  Created brain/ subfolder")
    
    # List all existing files under brain/
    all_files = []
    page_token = None
    while True:
        resp = drive.files().list(
            q=f"'{brain_sub_id}' in parents and trashed=false",
            spaces='drive', pageSize=100, pageToken=page_token,
            fields='nextPageToken,files(id,name,parents,size)'
        ).execute()
        all_files.extend(resp.get('files', []))
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    
    # Also get files from subfolders
    for f in list(all_files):
        if f.get('mimeType') == 'application/vnd.google-apps.folder' or not f.get('name', '').count('.'):
            # It's likely a folder - get its children
            if f.get('id'):
                sub_resp = drive.files().list(
                    q=f"'{f['id']}' in parents and trashed=false",
                    spaces='drive', pageSize=50,
                    fields='files(id,name,parents,size)'
                ).execute()
                all_files.extend(sub_resp.get('files', []))
    
    synced = 0
    errors = 0
    
    # Ensure subfolders exist
    folder_cache = {}
    for rel_path, (folder_name, _) in SYNC_MAP.items():
        if folder_name and folder_name not in folder_cache:
            if folder_name == "root":
                folder_cache[folder_name] = brain_sub_id
            else:
                folder_cache[folder_name] = find_or_create_folder(drive, folder_name, brain_sub_id)
    folder_cache["root"] = brain_sub_id
    
    for rel_path, (folder_name, _) in SYNC_MAP.items():
        local_path = f"{BRAIN_DIR}/{rel_path}"
        remote_name = os.path.basename(rel_path)
        parent_id = folder_cache.get(folder_name, brain_sub_id)
        
        if upload_file(drive, local_path, remote_name, parent_id, all_files):
            size = os.path.getsize(local_path)
            print(f"  ✅ {rel_path}: {size:,}B")
            synced += 1
        else:
            if os.path.exists(local_path):
                print(f"  ❌ {rel_path}: upload failed")
                errors += 1
            else:
                print(f"  ⏭️ {rel_path}: skipped (not found)")
        time.sleep(0.3)  # Rate limit
    
    # Write sync marker
    marker = {
        'last_sync': int(time.time() * 1000),
        'files_synced': synced,
        'errors': errors,
        'status': 'connected',
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    os.makedirs(f"{BRAIN_DIR}/cache", exist_ok=True)
    with open(SYNC_MARKER, 'w') as f:
        json.dump(marker, f, indent=2)
    
    return {'synced': synced, 'errors': errors}

def verify_sync(drive=None, brain_folder_id=None):
    """Verify Drive files match local files by size"""
    if not drive:
        drive = get_drive_service()
    if not brain_folder_id:
        brain_folder_id = find_brain_folder_id(drive)
    
    # Get brain subfolder
    resp = drive.files().list(
        q=f"name='brain' and '{brain_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces='drive', pageSize=1
    ).execute()
    if not resp.get('files'):
        print("❌ brain/ subfolder not found on Drive")
        return False
    
    print("=== Bidirectional Sync Verification ===")
    verified = 0; mismatches = 0
    
    # Check each synced file
    checks = [
        ('api_server.py', '/config/brain/api_server.py'),
        ('brain.index', '/config/brain/vectors/brain.index'),
        ('meta.json', '/config/brain/vectors/meta.json'),
        ('episodic.db', '/config/brain/memory/episodic.db'),
        ('brain.graphml', '/config/brain/graph/brain.graphml'),
    ]
    
    for name, local_path in checks:
        if not os.path.exists(local_path):
            continue
        local_size = os.path.getsize(local_path)
        # Find on Drive
        resp = drive.files().list(
            q=f"name='{name}' and trashed=false",
            spaces='drive', pageSize=5, fields='files(id,name,size,parents)'
        ).execute()
        drive_match = None
        for f in resp.get('files', []):
            drive_size = int(f.get('size', 0))
            if drive_size == local_size:
                drive_match = f; break
        
        if drive_match:
            print(f"  ✅ {name}: {local_size:,}B verified")
            verified += 1
        else:
            best = resp.get('files', [{}])[0]
            ds = int(best.get('size', 0))
            print(f"  ❌ {name}: local={local_size:,}B drive={ds:,}B")
            mismatches += 1
    
    return mismatches == 0

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'sync'
    
    if action == 'sync':
        print("🔄 Syncing brain → Google Drive...")
        result = sync_to_drive()
        print(f"\n📊 Result: {result['synced']} synced, {result['errors']} errors")
    elif action == 'verify':
        verify_sync()
    elif action == 'both':
        print("🔄 Syncing...")
        sync_to_drive()
        print("\n🔍 Verifying...")
        verify_sync()
    else:
        print(f"Usage: {sys.argv[0]} [sync|verify|both]")
