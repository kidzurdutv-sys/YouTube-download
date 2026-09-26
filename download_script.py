#!/usr/bin/env python3
"""24/7 Cloud Video Downloader for GitHub Actions"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

STATE_FILE = 'uploaded_videos.json'
DOWNLOAD_DIR = Path('downloads')

# Add your video URLs here or set VIDEO_URLS env var
VIDEO_URLS = os.getenv('VIDEO_URLS', '').split(',') if os.getenv('VIDEO_URLS') else []

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {'uploaded_videos': [], 'last_run': None}

def save_state(state):
    state['last_run'] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    print(f"State saved: {len(state['uploaded_videos'])} videos tracked")

def get_video_id(url):
    if 'youtube.com' in url:
        if 'v=' in url:
            return url.split('v=')[1].split('&')[0]
    return url

def download_video(url, video_id):
    print(f"\nDownloading: {url}")
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    cmd = ['yt-dlp', '-f', 'best', '-o', str(DOWNLOAD_DIR / '%(title)s.%(ext)s'), url]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Downloaded: {video_id}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed: {video_id} - {e.stderr}")
        return False

def main():
    print(f"\n{'#'*60}")
    print(f"# 24/7 Cloud Video Downloader - {datetime.now().isoformat()}")
    print(f"{'#'*60}\n")
    
    state = load_state()
    print(f"Loaded: {len(state['uploaded_videos'])} previously uploaded videos")
    
    new_downloads = []
    for url in VIDEO_URLS:
        url = url.strip()
        if not url:
            continue
        video_id = get_video_id(url)
        if video_id in state['uploaded_videos']:
            print(f"Skipping (already downloaded): {video_id}")
            continue
        if download_video(url, video_id):
            new_downloads.append(video_id)
    
    state['uploaded_videos'].extend(new_downloads)
    save_state(state)
    
    print(f"\n{'#'*60}")
    print(f"# Summary: Downloaded {len(new_downloads)}, Total tracked: {len(state['uploaded_videos'])}")
    print(f"{'#'*60}\n")

if __name__ == '__main__':
    main()































































