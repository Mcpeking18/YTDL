# 🎥 YT-DLP Downloader (Python)

A simple, beautiful YouTube (and other supported sites) downloader made with **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**, **FFmpeg**, and **CustomTkinter** in Python.  
It features a modern dark-mode Graphical User Interface (GUI) to let you easily download **audio (mp3)** or **video (mp4)** and saves them into your chosen folder.

---

## ✨ Features
- **Modern GUI**: Built with `customtkinter` for a sleek, dark-themed experience.
- **Format Options**: Choose between **Audio (mp3)** or **Video (mp4)**.
- **Quality Selection**: Pick your preferred video resolution (e.g., Best, 1080p, 720p, 480p, 360p).
- **Live Progress Bar**: See exactly how far along your download is.
- **Bulletproof Failsafes**: 
  - Downloads to a temporary folder (`C:/Temp`) for speed, then safely moves finished files to your final destination (`D:/Desktop`).
  - Auto-renames files to prevent overwriting existing videos on your Desktop.
  - Ignores partial or broken downloads.
  - Automatic retry mechanism (up to 3 times) for network interruptions.

## 🛠️ Requirements

- **Python 3.9+**
- **yt-dlp** and **customtkinter**
```bash
pip install yt-dlp customtkinter
```

- **FFmpeg** (must be installed & available in PATH)

## 🚀 Usage
1. Clone or download this repo.
2. Run the script: 
   ```bash
   python ytdl.py
   ```
3. The GUI window will open. Paste your video URL.
4. Select your format and desired quality.
5. Click **Download**!

*Note: Files will be downloaded to `C:/Temp` first, then automatically moved to `D:/Desktop` when finished (you can change these paths at the top of the `ytdl.py` file).*

## 🧩 Future Plans
- Allow changing download folder directly from the UI
- Add playlist downloading support

# 👨‍💻 Author
**MCPEKING18** — learning Python modules one projekt at a time 🐍