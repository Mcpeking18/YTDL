# 🎥 YT-DLP Downloader (Python)

A simple, beautiful YouTube (and other supported sites) downloader made with **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**, **FFmpeg**, and **CustomTkinter** in Python.  
It features a modern dark-mode Graphical User Interface (GUI) to let you easily download **audio (mp3)** or **video (mp4)** and saves them into your chosen folder.

---

## ✨ Features
- **Modern YouTube Darkroom GUI**: Built with `customtkinter` with an authentic YouTube dark aesthetic.
- **Live Video Preview**: Automatically fetches the video thumbnail, title, channel name, and duration as soon as you paste a URL.
- **Embedded Cover Art & Metadata**: Automatically embeds the highest-quality thumbnail directly into downloaded files (album cover art for MP3s and poster artwork for MP4 videos).
- **Format Options**: Choose between **Audio (mp3)** or **Video (mp4)** with modern segmented toggle controls.
- **Quality Selection**: Pick your preferred video resolution (e.g., Best, 1080p, 720p, 480p, 360p).
- **Custom Destination**: Choose any destination directory directly from the UI (defaults to your Desktop).
- **Live Progress Bar & Status Pill**: See real-time download and processing progress.
- **Failsafes & Data Protection**:
  - Downloads in an isolated temporary directory and cleanly moves completed files upon finish.
  - Auto-renames files (`(1)`, `(2)`, etc.) to prevent overwriting existing files in your folder.
  - Automatically cleans up partial/interrupted files on failure.
  - Built-in retry handling for network drops.

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
- Add playlist downloading support
- Download history tab

# 👨‍💻 Author
**MCPEKING18** — learning Python modules one projekt at a time 🐍
