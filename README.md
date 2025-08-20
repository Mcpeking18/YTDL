# 🎥 YT-DLP Downloader (Python)

A simple YouTube (and other supported sites) downloader made with **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** and **FFmpeg** in Python.  
It lets you download **audio (mp3)** or **video (mp4)** and saves them into your chosen folder.

---

## ✨ Features
- Choose between **Audio (mp3)** or **Video (mp4)**
- Temporary download folder (for speed) → files are moved to final folder automatically
- Error logging (writes errors to `errors.txt`)
- Beginner-friendly and kept simple
- Uses `ffmpeg` in background for conversions

## 🛠️ Requirements

- **Python 3.9+**
- **yt-dlp**
```pip install yt-dlp```

- **FFmpeg** (must be installed & available in PATH)

## 🚀 Usage
Clone or download this repo

Run the script: ```python ytdl.py```

Paste the video URL

Choose:

1 → download as mp3

2 → download as mp4

Files will be downloaded to C:/Temp first, then moved to D:/Desktop (you can change paths in the code).

## 🧩 Future Plans
- Add a GUI (Tkinter / PyQt)

- Add quality selection (e.g., 720p, 1080p, 4K)

- Show a nicer progress bar

- Allow changing download folder from script

# 👨‍💻 Author
**MCPEKING18** — learning Python modules one projekt at a time 🐍