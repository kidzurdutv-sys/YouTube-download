#!/usr/bin/env python3
"""
YouTube Shorts Bulk Downloader — Android (Kivy) version
=========================================================
Mobile port of the bulk downloader app, built with Kivy widgets for Android.

Key features:
  - Fast, direct stream download (video+audio) without requiring external ffmpeg binary.
  - Automatically saves to public Downloads/ShortsDownloader folder on Android,
    with automatic fallback to app-specific storage if restricted.
  - Full SSL certificate validation bundled via certifi.
  - Dynamic runtime permission handling for Android.
  - YouTube player client spoofing (android/web) to avoid bot detection blocks.
"""

import os
import re
import sys
import subprocess
import threading
import traceback
from datetime import datetime
from pathlib import Path

# --------------------------------------------------------------------------
# Platform detection & Android environment preparation
# --------------------------------------------------------------------------
def is_android_env():
    """Detect if running under Android (python-for-android / Pyjnius)."""
    return (
        "ANDROID_ARGUMENT" in os.environ
        or "ANDROID_ENTRYPOINT" in os.environ
        or "PYTHON_SERVICE_ARGUMENT" in os.environ
        or sys.platform == "android"
    )

# --------------------------------------------------------------------------
# Auto-install: desktop-only helper to run without manual pip install
# --------------------------------------------------------------------------
REQUIRED_PACKAGES = {
    "kivy": "kivy==2.3.0",
    "yt_dlp": "yt-dlp",
    "certifi": "certifi",
    "mutagen": "mutagen",
    "Crypto": "pycryptodome",
    "requests": "requests",
}

def _ensure_packages_installed():
    if is_android_env():
        # NEVER attempt pip install inside an Android APK
        return

    import importlib
    missing = []
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(pip_name)

    if not missing:
        return

    print(f"[setup] Installing missing packages: {', '.join(missing)}")
    print("[setup] This only happens once — please wait...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade", "pip",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    for pip_name in missing:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
        except subprocess.CalledProcessError as e:
            print(f"[setup] Failed to install {pip_name}: {e}")
            print("[setup] Try running manually: pip install " + pip_name)
            sys.exit(1)

    print("[setup] All packages installed. Starting app...")
    importlib.invalidate_caches()


_ensure_packages_installed()

# Configure SSL certs for yt-dlp and requests on Android
try:
    import certifi
    ca_file = certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", ca_file)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", ca_file)
except ImportError:
    pass

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.utils import platform

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

SHORTS_URL_PATTERN = re.compile(r"youtube\.com/shorts/", re.IGNORECASE)
DEFAULT_MAX_DURATION = 180


# --------------------------------------------------------------------------
# URL Helpers & Storage Logic
# --------------------------------------------------------------------------

def normalize_channel_shorts_url(url):
    url = url.strip().rstrip("/")
    if not url:
        return url
    if "/shorts" in url.lower() or "playlist?list=" in url.lower() or "/watch?v=" in url.lower():
        return url
    if re.search(r"youtube\.com/(@[\w.\-]+|channel/[\w\-]+|c/[\w.\-]+|user/[\w.\-]+)$", url, re.IGNORECASE):
        return url + "/shorts"
    return url


def is_short_entry(entry, max_duration=DEFAULT_MAX_DURATION):
    if not entry:
        return False
    url = entry.get("webpage_url") or entry.get("original_url") or entry.get("url") or ""
    if SHORTS_URL_PATTERN.search(url):
        return True
    duration = entry.get("duration")
    width = entry.get("width")
    height = entry.get("height")
    if duration is not None and duration <= max_duration:
        if width and height:
            return height >= width
        return duration <= 60
    return False


def get_downloads_dir():
    """Returns accessible folder: public Downloads on Android with automatic fallback."""
    if platform == "android" or is_android_env():
        # 1. Try public Download/ShortsDownloader folder
        try:
            from android.storage import primary_external_storage_path
            storage_root = primary_external_storage_path()
            base = Path(storage_root) / "Download" / "ShortsDownloader"
            base.mkdir(parents=True, exist_ok=True)
            # Test write access
            test_f = base / ".write_test"
            test_f.touch()
            test_f.unlink()
            return base
        except Exception:
            pass

        # 2. Try app-specific external storage
        try:
            from android.storage import app_storage_path
            base = Path(app_storage_path()) / "Download"
            base.mkdir(parents=True, exist_ok=True)
            return base
        except Exception:
            pass

        # 3. Try app user data dir
        try:
            base = Path(App.get_running_app().user_data_dir) / "downloads"
            base.mkdir(parents=True, exist_ok=True)
            return base
        except Exception:
            pass

        base = Path("/sdcard/Download/ShortsDownloader")
        base.mkdir(parents=True, exist_ok=True)
        return base
    else:
        base = Path.cwd() / "downloads"
        base.mkdir(parents=True, exist_ok=True)
        return base


def request_android_permissions():
    if platform != "android" and not is_android_env():
        return
    try:
        from android.permissions import request_permissions, Permission
        perms = [
            Permission.INTERNET,
            Permission.WRITE_EXTERNAL_STORAGE,
            Permission.READ_EXTERNAL_STORAGE,
        ]
        # On Android 13+, add media permissions if available
        if hasattr(Permission, "READ_MEDIA_VIDEO"):
            perms.append(Permission.READ_MEDIA_VIDEO)
        if hasattr(Permission, "READ_MEDIA_AUDIO"):
            perms.append(Permission.READ_MEDIA_AUDIO)
        request_permissions(perms)
    except Exception as e:
        print(f"[permissions] Warning: could not request permissions: {e}")


# --------------------------------------------------------------------------
# Downloader Core
# --------------------------------------------------------------------------

class ShortsDownloader:
    def __init__(self, output_dir, max_duration=DEFAULT_MAX_DURATION,
                 enforce_shorts_filter=True, log_callback=None,
                 progress_callback=None, stop_flag=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_duration = max_duration
        self.enforce_shorts_filter = enforce_shorts_filter
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.stop_flag = stop_flag or (lambda: False)
        self.results = {"downloaded": [], "skipped": [], "failed": []}

    def _log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        if self.log_callback:
            self.log_callback(line)

    def _get_base_ydl_opts(self):
        opts = {
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": False,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"]
                }
            }
        }
        return opts

    def _extract_info(self, url):
        opts = self._get_base_ydl_opts()
        opts.update({
            "extract_flat": "in_playlist",
            "skip_download": True,
        })
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    def resolve_urls(self, raw_inputs):
        resolved = []
        for raw in raw_inputs:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            target = normalize_channel_shorts_url(raw)
            try:
                info = self._extract_info(target)
            except Exception as e:
                self._log(f"Could not read '{raw}': {e}")
                self.results["failed"].append({"url": raw, "error": str(e)})
                continue
            entries = info.get("entries") if info else None
            if entries:
                for entry in entries:
                    if entry is None:
                        continue
                    vurl = entry.get("url") or entry.get("webpage_url")
                    if vurl and not vurl.startswith("http"):
                        vurl = f"https://www.youtube.com/watch?v={vurl}"
                    if vurl:
                        resolved.append((vurl, entry))
            elif info:
                resolved.append((info.get("webpage_url", target), info))
        return resolved

    def download_all(self, raw_inputs):
        self._log(f"Resolving {len(raw_inputs)} input(s)...")
        video_list = self.resolve_urls(raw_inputs)
        total = len(video_list)
        self._log(f"Found {total} candidate video(s).")

        for idx, (vurl, entry) in enumerate(video_list, 1):
            if self.stop_flag():
                self._log("Stopped by user.")
                break
            if self.enforce_shorts_filter and not is_short_entry(entry, self.max_duration):
                self._log(f"[{idx}/{total}] Skipping (not a Short): {vurl}")
                self.results["skipped"].append(vurl)
                if self.progress_callback:
                    self.progress_callback(idx, total)
                continue
            self._log(f"[{idx}/{total}] Downloading: {vurl}")
            ok, err = self._download_single(vurl)
            if ok:
                self.results["downloaded"].append(vurl)
            else:
                self._log(f"   Failed: {err}")
                self.results["failed"].append({"url": vurl, "error": err})
            if self.progress_callback:
                self.progress_callback(idx, total)

        self._log(
            f"Done! Downloaded: {len(self.results['downloaded'])}, "
            f"Skipped: {len(self.results['skipped'])}, "
            f"Failed: {len(self.results['failed'])}"
        )
        return self.results

    def _download_single(self, url):
        outtmpl = str(self.output_dir / "%(uploader)s - %(title).100s [%(id)s].%(ext)s")
        opts = self._get_base_ydl_opts()
        opts.update({
            "outtmpl": outtmpl,
            # Ensure complete streams containing both video and audio
            "format": "b[ext=mp4]/b/best[vcodec!=none][acodec!=none]/best",
            "noplaylist": True,
            "retries": 3,
            "fragment_retries": 3,
            "ignoreerrors": False,
        })
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return True, None
        except Exception as e:
            return False, str(e)


# --------------------------------------------------------------------------
# Kivy UI
# --------------------------------------------------------------------------

class ShortsDownloaderApp(App):
    def build(self):
        self.title = "Shorts Downloader"
        self.state = {"stop": False, "running": False}

        root = BoxLayout(orientation="vertical", padding=12, spacing=8)

        root.add_widget(Label(
            text="Paste YouTube Shorts or Channel URLs (one per line):",
            size_hint_y=None, height=30, halign="left"
        ))

        self.url_input = TextInput(
            hint_text="https://youtube.com/shorts/...\nhttps://www.youtube.com/@Channel",
            size_hint_y=0.28,
            multiline=True
        )
        root.add_widget(self.url_input)

        opts_row = BoxLayout(size_hint_y=None, height=44, spacing=6)
        self.filter_checkbox = CheckBox(active=True, size_hint_x=None, width=40)
        opts_row.add_widget(self.filter_checkbox)
        opts_row.add_widget(Label(text="Only Shorts", size_hint_x=None, width=90))
        opts_row.add_widget(Label(text="Max sec:", size_hint_x=None, width=70))
        self.duration_label = Label(text=str(DEFAULT_MAX_DURATION), size_hint_x=None, width=40)
        self.duration_slider = Slider(min=10, max=300, value=DEFAULT_MAX_DURATION)
        self.duration_slider.bind(value=self._on_duration_change)
        opts_row.add_widget(self.duration_slider)
        opts_row.add_widget(self.duration_label)
        root.add_widget(opts_row)

        self.dest_label = Label(
            text=f"Saving to: {get_downloads_dir()}",
            size_hint_y=None, height=24, font_size=12
        )
        root.add_widget(self.dest_label)

        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        self.start_btn = Button(text="Start Download", background_color=(0.18, 0.65, 0.25, 1))
        self.start_btn.bind(on_press=self.start_download)
        self.stop_btn = Button(text="Stop", disabled=True, background_color=(0.85, 0.25, 0.2, 1))
        self.stop_btn.bind(on_press=self.stop_download)
        btn_row.add_widget(self.start_btn)
        btn_row.add_widget(self.stop_btn)
        root.add_widget(btn_row)

        self.progress = ProgressBar(max=1, value=0, size_hint_y=None, height=18)
        root.add_widget(self.progress)
        self.progress_label = Label(text="", size_hint_y=None, height=20, font_size=12)
        root.add_widget(self.progress_label)

        self.log_label = Label(
            text="Ready. Paste URLs above and tap Start Download.\n",
            size_hint_y=None, valign="top", halign="left", font_size=12, markup=False
        )
        self.log_label.bind(texture_size=self._resize_log)
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.log_label)
        root.add_widget(scroll)

        # Trigger Android permissions on start
        request_android_permissions()
        return root

    def _resize_log(self, instance, value):
        instance.size = (instance.parent.width if instance.parent else value[0], value[1])
        instance.text_size = (instance.width, None)

    def _on_duration_change(self, instance, value):
        self.duration_label.text = str(int(value))

    def append_log(self, line):
        def _do(dt):
            self.log_label.text += line + "\n"
        Clock.schedule_once(_do, 0)

    def set_progress(self, done, total):
        def _do(dt):
            self.progress.max = max(total, 1)
            self.progress.value = done
            self.progress_label.text = f"{done} / {total}"
        Clock.schedule_once(_do, 0)

    def start_download(self, *_):
        if self.state["running"]:
            return
        if yt_dlp is None:
            self.append_log("ERROR: yt-dlp module not available.")
            return
        raw_text = self.url_input.text.strip()
        raw_inputs = [line for line in raw_text.splitlines() if line.strip()]
        if not raw_inputs:
            self.append_log("Please paste at least one valid URL.")
            return

        output_dir = get_downloads_dir()
        self.dest_label.text = f"Saving to: {output_dir}"
        self.state["stop"] = False
        self.state["running"] = True
        self.start_btn.disabled = True
        self.stop_btn.disabled = False
        self.progress.value = 0
        self.log_label.text = ""

        def worker():
            downloader = ShortsDownloader(
                output_dir=output_dir,
                max_duration=int(self.duration_slider.value),
                enforce_shorts_filter=self.filter_checkbox.active,
                log_callback=self.append_log,
                progress_callback=self.set_progress,
                stop_flag=lambda: self.state["stop"],
            )
            try:
                downloader.download_all(raw_inputs)
            except Exception:
                self.append_log("Fatal error:\n" + traceback.format_exc())
            finally:
                self.state["running"] = False

                def _reset(dt):
                    self.start_btn.disabled = False
                    self.stop_btn.disabled = True
                Clock.schedule_once(_reset, 0)

        threading.Thread(target=worker, daemon=True).start()

    def stop_download(self, *_):
        self.state["stop"] = True
        self.append_log("Stopping after current video completes...")


if __name__ == "__main__":
    ShortsDownloaderApp().run()
