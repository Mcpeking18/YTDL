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

### 1. Modern WebUI Live Server (FastAPI + Tailwind)
```bash
uv run ytdl-web
# or: uv run python server.py
```
*Starts the local FastAPI server at `http://127.0.0.1:8000` and automatically opens it in your default browser. Features instant video ID thumbnail extraction, live metadata preview, quick folder presets (`Desktop (D:)`, `Downloads`, `Music`), native folder browser, live transfer speed/ETA, and full download history.*

### 2. Classic CustomTkinter Desktop Client
```bash
uv run ytdl
# or: uv run python ytdl.py
```
*Runs the classic Python CustomTkinter desktop interface.*

## 🧪 Tests
To run the automated test suite across all modules:
```bash
uv run python -m unittest discover
```

## 🧩 Future Plans
- Modern Web UI / Figma-driven desktop client
- Batch queue management

# 👨‍💻 Author
**MCPEKING18** — learning Python modules one projekt at a time 🐍
