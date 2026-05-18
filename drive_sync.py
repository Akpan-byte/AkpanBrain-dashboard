#!/usr/bin/env python3
"""
AkpanBrain Drive Sync — Uses Python Google Drive API (not rclone)
Syncs brain data between /config/brain/ and Google Drive AkpanBrain/brain/
"""
import json, os, time, hashlib
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

BRAIN_DIR = "/config/brain"
TOKEN_PATH = "/config/.hermes/google_token.json"
SYNC_MARKER = f"{BRAIN_DIR}/cache/.last_sync"
DRIVE_ROOT = "AkpanBrain"
DRIVE_BRAIN = "brain"

# Files to sync (local → Drive)
SYNC_FILES = {
    "akpanbrain.py": f"{BRAIN_DIR}/akpanbrain.py",
    "vectors/brain.index": f"{BRAIN_DIR}/vectors/brain.index",
    "vectors/meta.json": f"{BRAIN_DIR}/vectors/meta.json",
    "memory/episodic.db": f"{BRAIN_DIR}/memory/episodic.db",
    "graph/brain.graphml": f"{BRAIN_DIR}/graph/brain.graphml",
}

class DriveSync:
    def __init__(self):
        self.service = None
        self.root_id = None
        self.brain_id = None
        self._file_cache = {}  # name → drive file id
        
    def _get_creds(self):
        with open(TOKEN_PATH) as f:
            token_data = json.load(f)
        creds = Credentials.from_authorized_user_info(token_data)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token
            with open(TOKEN_PATH, 'w') as f:
                json.dump({
                    'access_token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'expiry': creds.expiry.isoformat() if creds.expiry else '2099-01-01T00:00:00+00:00'
                }, f)
        return creds
    
    def connect(self):
        """Connect to Drive and find/create AkpanBrain/brain/ folders"""
        creds = self._get_creds()
        self.service = build('drive', 'v3', credentials=creds)
        
        # Find root folder
        results = self.service.files().list(
            q=f"name='{DRIVE_ROOT}' and trashed=false and mimeType='application/vnd.google-apps.folder'",
            spaces='drive', pageSize=1
        ).execute()
        files = results.get('files', [])
        if files:
            self.root_id = files[0]['id']
        else:
            # Create root folder
            f = self.service.files().create(body={
                'name': DRIVE_ROOT,
                'mimeType': 'application/vnd.google-apps.folder'
            }).execute()
            self.root_id = f['id']
            print(f"Created Drive folder: {DRIVE_ROOT}")
        
        # Find brain subfolder
        results = self.service.files().list(
            q=f"name='{DRIVE_BRAIN}' and '{self.root_id}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'",
            spaces='drive', pageSize=1
        ).execute()
        files = results.get('files', [])
        if files:
            self.brain_id = files[0]['id']
        else:
            f = self.service.files().create(body={
                'name': DRIVE_BRAIN,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.root_id]
            }).execute()
            self.brain_id = f['id']
            print(f"Created Drive folder: {DRIVE_ROOT}/{DRIVE_BRAIN}")
        
        self._build_file_cache()
        return True
    
    def _build_file_cache(self):
        """List all files in brain folder on Drive"""
        self._file_cache = {}
        if not self.brain_id:
            return
        page_token = None
        while True:
            results = self.service.files().list(
                q=f"'{self.brain_id}' in parents and trashed=false",
                spaces='drive', fields='nextPageToken, files(id, name, md5Checksum, modifiedTime)',
                pageToken=page_token
            ).execute()
            for f in results.get('files', []):
                self._file_cache[f['name']] = f
            page_token = results.get('nextPageToken')
            if not page_token:
                break
    
    def _get_local_md5(self, filepath):
        """Get MD5 hash of a local file"""
        if not os.path.exists(filepath):
            return None
        h = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
    
    def upload_file(self, local_path, drive_name):
        """Upload a file to Drive (create or update)"""
        if not os.path.exists(local_path):
            return None
        
        media = MediaFileUpload(local_path, resumable=True)
        
        if drive_name in self._file_cache:
            # Update existing file
            file_id = self._file_cache[drive_name]['id']
            f = self.service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            print(f"  ↑ Updated: {drive_name}")
        else:
            # Create new file
            f = self.service.files().create(
                body={'name': drive_name, 'parents': [self.brain_id]},
                media_body=media
            ).execute()
            print(f"  ↑ Created: {drive_name}")
        
        self._file_cache[drive_name] = f
        return f.get('id')
    
    def download_file(self, drive_name, local_path):
        """Download a file from Drive"""
        if drive_name not in self._file_cache:
            return False
        
        file_id = self._file_cache[drive_name]['id']
        request = self.service.files().get_media(fileId=file_id)
        
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        
        print(f"  ↓ Downloaded: {drive_name}")
        return True
    
    def sync_up(self):
        """Upload all brain files to Drive"""
        count = 0
        for drive_name, local_path in SYNC_FILES.items():
            if os.path.exists(local_path):
                local_md5 = self._get_local_md5(local_path)
                drive_md5 = self._file_cache.get(drive_name, {}).get('md5Checksum')
                
                if local_md5 != drive_md5:
                    try:
                        self.upload_file(local_path, drive_name)
                        count += 1
                    except Exception as e:
                        print(f"  ✗ Failed: {drive_name}: {e}")
                else:
                    print(f"  = Unchanged: {drive_name}")
        
        return count
    
    def sync_down(self):
        """Download all Drive files to local (for recovery/other agents)"""
        count = 0
        for drive_name, local_path in SYNC_FILES.items():
            if drive_name in self._file_cache:
                drive_md5 = self._file_cache[drive_name].get('md5Checksum')
                local_md5 = self._get_local_md5(local_path)
                
                if drive_md5 != local_md5:
                    try:
                        self.download_file(drive_name, local_path)
                        count += 1
                    except Exception as e:
                        print(f"  ✗ Failed: {drive_name}: {e}")
        return count
    
    def sync_bidirectional(self):
        """Full bidirectional sync — upload changes, download new from Drive"""
        print(f"\n🔄 Bidirectional sync started...")
        self._build_file_cache()  # Refresh cache
        
        up_count = self.sync_up()
        down_count = self.sync_down()
        
        # Save sync marker
        sync_data = {
            "last_sync": time.time() * 1000,
            "drive_status": "connected",
            "files_synced": up_count + down_count,
            "uploaded": up_count,
            "downloaded": down_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        os.makedirs(os.path.dirname(SYNC_MARKER), exist_ok=True)
        with open(SYNC_MARKER, 'w') as f:
            json.dump(sync_data, f, indent=2)
        
        print(f"✅ Sync complete: {up_count}↑ {down_count}↓")
        return sync_data


def main():
    print("🧠 AkpanBrain Drive Sync")
    print("=" * 40)
    
    sync = DriveSync()
    try:
        if sync.connect():
            print(f"✅ Connected to Drive: {DRIVE_ROOT}/{DRIVE_BRAIN}")
            print(f"   Root ID: {sync.root_id}")
            print(f"   Brain ID: {sync.brain_id}")
            print(f"   Files on Drive: {len(sync._file_cache)}")
            result = sync.sync_bidirectional()
            return result
        else:
            print("❌ Failed to connect to Drive")
            return None
    except Exception as e:
        print(f"❌ Sync error: {e}")
        return None


if __name__ == "__main__":
    main()
