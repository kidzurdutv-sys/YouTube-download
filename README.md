# 📱 YouTube Shorts Downloader — Android APK

An Android app built with **Kivy** and **yt-dlp** for bulk-downloading YouTube Shorts and channel videos directly to your phone.

---

## ⚡ APK فائل کیسے حاصل کریں (How to Get Your `.apk` File)

Python اور Kivy کی Android APK بنانے کے لیے Linux اور Android SDK/NDK ٹولز کی ضرورت ہوتی ہے جو Google Colab کلاؤڈ پر **100% مفت اور 1 کلک** میں دستیاب ہیں:

---

### طریقہ 1: گوگل کولاب کے ذریعے (Fastest & 1-Click Method — Free)

1. براؤزر میں **[Google Colab](https://colab.research.google.com)** کھولیں۔
2. اوپر **Upload** ٹیب پر کلک کریں اور اس فولڈر میں موجود فائل **`Build_ShortsDownloader_APK.ipynb`** اپلوڈ کریں۔
3. اوپر مینیو میں **Runtime** پر کلک کریں اور **Run all** (یا کی بورڈ سے `Ctrl + F9`) دبائیں۔
4. 10 سے 15 منٹ میں بلڈ مکمل ہو کر **`.apk` فائل خود بخود آپ کے کمپیوٹر پر ڈاؤن لوڈ ہو جائے گی!**

---

### طریقہ 2: GitHub Actions کے ذریعے (Automatic Cloud Build)

1. اپنے [GitHub](https://github.com/new) پر ایک نیا Repository بنائیں۔
2. یہ سارا فولڈر اپنے GitHub Repo میں Push کریں۔
3. GitHub پر **Actions** ٹیب میں جائیں، **Build Android APK** کو منتخب کریں اور **Run workflow** پر کلک کریں۔
4. جب عمل مکمل ہو جائے، تو **Artifacts** سیکشن سے `shorts-downloader-apk` ڈاؤن لوڈ کریں۔

---

### طریقہ 3: Linux / WSL2 پر لوکل بلڈ (Local Build)

اگر آپ کے پاس Ubuntu یا WSL2 ہے تو ٹرمینل میں چلائیں:
```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev build-essential ccache libltdl-dev
pip install --upgrade pip
pip install buildozer==1.5.0 "cython>=3.0,<3.1"
buildozer -v android debug
```
تیار شدہ APK `bin/` فولڈر میں مل جائے گی۔

---

## 📲 موبائل میں انسٹال کرنے کا طریقہ (Install on Phone)

1. حاصل شدہ `.apk` فائل اپنے موبائل میں بھیجیں (واٹس ایپ، کیبل، یا گوگل ڈرائیو کے ذریعے)۔
2. فائل مینیجر میں جا کر `.apk` پر کلک کریں۔
3. اگر موبائل *"Install Unknown Apps"* کی وارننگ دے تو Settings میں جا کر **Allow** کر دیں۔
4. ایپ کھولیں اور یوٹیوب لنکس ڈال کر **Start Download** دبائیں۔
5. ویڈیوز آپ کے فون کے `Download/ShortsDownloader/` فولڈر اور گیلری میں محفوظ ہو جائیں گی۔
