[app]
title = Shorts Downloader
package.name = shortsdownloader
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy==2.3.0,yt-dlp,certifi,mutagen,pycryptodome,requests,urllib3,charset_normalizer,idna

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,ACCESS_NETWORK_STATE,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO

# Modern Android target/min API
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a

# Auto-accept the Android SDK license prompts during CI builds.
android.accept_sdk_license = True

# Needed on Android 11+ for the app to write into the public Downloads folder.
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
