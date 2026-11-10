<div align="center">
  <img src="assets/logo.png" width="140" alt="YTDL Logo" style="border-radius: 16px;" />
  <h1>YTDL - YouTube Downloader</h1>
  <p>A simple, modern YouTube (and media) downloader with live video preview, automatic album art embedding, and dark mode GUI.</p>
</div>

---

## ✨ Features
- **Modern YouTube Darkroom GUI**: Built with `customtkinter` with an authentic YouTube dark aesthetic and custom taskbar branding.
- **One-Click Paste**: Quick `📋 Paste` button to instantly grab YouTube links from your clipboard.
- **Live Video & Playlist Preview**: Automatically debounces and fetches thumbnails, title, channel name, and duration or playlist track count.
- **Embedded Cover Art & Metadata**: Embeds the highest-quality thumbnail directly into downloaded files (album cover art for MP3s and poster artwork for MP4 videos).
- **Audio Bitrate Selection**: Choose your preferred audio bitrate (**320 kbps**, **256 kbps**, **192 kbps**, **128 kbps**).
- **Video Resolution Selection**: Pick your preferred resolution (**Best Available**, **1080p**, **720p**, **480p**, **360p**).
- **Full Playlist Support**: Download complete YouTube playlists out of the box (no cookies required for public or unlisted playlists).
- **Download Speed & ETA**: Real-time progress bar showing download percentage, transfer speed, and estimated time remaining.
- **One-Click "Show in Folder"**: Instantly highlight and inspect downloaded files in Windows Explorer upon completion.
- **Download History**: Keep track of recent downloads with a dedicated `📜 History` viewer and 1-click folder opening.
- **Startup FFmpeg Pre-Check**: Checks for FFmpeg availability on launch and warns if missing.
- **Failsafes & Data Protection**:
  - Downloads in an isolated temporary sandbox and safely moves finished files.
  - Resolves filenames collision-free (`(1)`, `(2)`, etc.) so existing files are never overwritten.
  - Strict directory validation: never creates unexpected folders and warns if a target path is invalid.
  - Auto-cleans up partial/interrupted files on failure.

## 🛠️ Requirements

- **Python 3.11+**
- **yt-dlp**, **customtkinter**, and **pillow**
```bash
pip install yt-dlp customtkinter pillow
```
*(Alternatively, use `uv run ytdl.py` or `uv sync`)*

- **FFmpeg** (must be installed & available in PATH)

## 🚀 Usage
1. Clone or download this repo.
2. Run the application: 
   ```bash
   uv run ytdl.py
   # or: python ytdl.py
   ```
3. The GUI window will open:
   - Paste your video URL.
   - Choose or browse to your preferred destination folder.
   - Select your format (Audio MP3 or Video MP4) and quality.
4. Click **Download**!

## 🧪 Tests
To run the automated test suite:
```bash
python -m unittest test_ytdl.py
```

## 🧩 Future Plans
- Modern Web UI / Figma-driven desktop client
- Batch queue management

# 👨‍💻 Author
**MCPEKING18** — learning Python modules one projekt at a time 🐍
