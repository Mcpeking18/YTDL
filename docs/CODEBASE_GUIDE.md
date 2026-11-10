# YTDL: The Complete Beginner-Friendly Codebase Walkthrough

Welcome! This guide explains every single file, function, and concept in the **YTDL (YouTube Downloader)** codebase in plain English. No prior web development or advanced Python experience is required.

---

# The Big Picture: How This Project is Structured

This project has two distinct versions across Git branches:
1. **Branch `main` (and `Py/CTK-build`)**: The **Desktop GUI version** built entirely in Python using `customtkinter`, `yt-dlp`, `pillow`, and `ffmpeg`.
2. **Branch `webui`**: The **WebUI version** split into a Python backend (`FastAPI` + `server.py` + `backend/core.py`) and a modern web frontend (`HTML` + `CSS` + `JavaScript`).

---

# PART 1: The Desktop App (`ytdl.py`)

In the desktop version, everything runs in a single Python process on your machine.

### 1. The Core Imports & Why They Are There
- `import ctypes`: A Python tool to talk to the Windows operating system kernel. We use it for `SetCurrentProcessExplicitAppUserModelID` so Windows doesn't treat our app as a generic Python script, allowing our custom character icon to appear on the Windows taskbar.
- `import threading`: **Crucial concept.** In any GUI app, the "Main Thread" draws the buttons and handles mouse clicks. If you download a 500 MB video on the main thread, the entire app freezes and Windows says *"Not Responding"*. `threading.Thread` lets the download run in the background while the UI stays smooth and responsive.
- `import tempfile`: Creates an isolated folder in Windows `AppData/Local/Temp/ytdl_...` where yt-dlp downloads raw chunks and converts audio. Only once everything succeeds does it move the finished file to your Desktop. This guarantees your Desktop never gets cluttered with broken `.part` files.
- `import shutil`: Standard library file utilities. We use `shutil.which("ffmpeg")` to check if FFmpeg is installed, and `shutil.move()` to transfer files safely.
- `from PIL import Image`: The **Pillow** library. It handles image loading, resizing thumbnails to 160x90, and converting WebP formats into JPG.
- `from yt_dlp import YoutubeDL`: The engine that talks to YouTube, extracts video URLs, and runs FFmpeg.

---

### 2. Helper Functions Explained

#### `check_ffmpeg() -> bool`
- **What it does**: Checks if `ffmpeg.exe` exists in your system's PATH.
- **Why it matters**: Without FFmpeg, YouTube video and audio cannot be merged, and MP3 conversion is impossible. If missing, the app warns you at startup rather than crashing halfway through a download.

#### `get_default_download_dir() -> Path`
- **What it does**: Checks if `D:\Desktop` exists. If yes, it defaults there. If not (like on other PCs), it safely falls back to `C:\Users\<Name>\Desktop` or `Downloads`.

#### `resolve_unique_path(directory, filename) -> Path`
- **What it does**: Prevents overwriting existing files.
- **How it works**: If `Song.mp3` already exists on your Desktop, a while-loop checks `Song (1).mp3`, `Song (2).mp3`, etc., until it finds an unused name. Your existing files are **never** replaced or deleted.

#### `extract_youtube_video_id(url: str) -> str | None`
- **What it does**: Uses **Regular Expressions (Regex)** to extract the unique 11-character YouTube video ID (like `dQw4w9WgXcQ`).
- **Why it matters**: YouTube thumbnail images always live at `https://img.youtube.com/vi/<ID>/mqdefault.jpg`. Extracting the ID lets us load the video thumbnail with zero delay.

#### `build_ydl_options(temp_dir, format_type, quality, progress_hook) -> dict`
- **What it does**: This is the configuration brain passed to `yt-dlp`.
- **Key options set**:
  - `outtmpl`: Output filename template in the temp folder.
  - `writethumbnail`: Downloads the highest-resolution thumbnail available.
  - `FFmpegThumbnailsConvertor`: Converts YouTube's WebP thumbnails to standard JPG (because MP3 ID3 tags only support JPG/PNG).
  - `FFmpegExtractAudio`: Extracts the audio stream and re-encodes to MP3 with your chosen bitrate (128, 192, 256, or 320 kbps).
  - `EmbedThumbnail`: Injects the thumbnail directly into the MP3/MP4 file as album artwork.
  - `ignoreerrors`: Lets multi-video playlists keep downloading even if one video in the playlist is blocked.

#### `save_history_entry()` and `load_history()`
- **What it does**: Reads and writes recent download titles, formats, and timestamps to a lightweight `history.json` file on your computer.

---

### 3. The `YTDLApp` Class (CustomTkinter GUI)

- **`class YTDLApp(ctk.CTk)`**: Creates the main application window.
- **Debounced Preview (`on_url_input_changed`)**:
  - If you type or paste a link, we don't want to query YouTube on every keystroke.
  - `self.after(500, self.trigger_preview_fetch)` waits 500 milliseconds after you stop typing before launching the background thread to fetch the title and thumbnail.
- **`progress_hook(self, d: dict)`**:
  - `yt-dlp` periodically calls this function during downloading with a dictionary `d`.
  - We extract `downloaded_bytes / total_bytes` to update the progress bar, plus `_speed_str` (e.g. `4.5 MiB/s`) and `_eta_str` (time remaining).
  - `self.after(0, ...)` safely sends these updates from the background thread back to the main UI thread.
- **"Open in Folder" (`open_last_downloaded`)**:
  - Once the download is complete, clicking this button triggers `subprocess.Popen(f'explorer /select,"{file_path}"')`, which opens Windows Explorer and automatically highlights the exact downloaded file.

---

# PART 2: The Modern WebUI Architecture (`webui` branch)

The `webui` branch splits the application into two independent halves:
1. **The Backend (Python + FastAPI)**: Runs on your PC at `http://127.0.0.1:8000`.
2. **The Frontend (Browser / Web)**: The user interface you see and interact with.

```
┌──────────────────────────────────────────────────────────────┐
│                    THE CLIENT-SERVER FLOW                    │
├──────────────────────────────┬───────────────────────────────┤
│ Frontend (Browser)           │ Backend (Python / FastAPI)    │
├──────────────────────────────┼───────────────────────────────┤
│ User pastes URL              │                               │
│  ─── fetch('/api/preview') ──> Fetches Title & Thumbnail     │
│  <── JSON metadata response ── Sends info back to Browser    │
│                              │                               │
│ User clicks [Download]       │                               │
│  ─── fetch('/api/download') ─> Starts background download    │
│                              │ Runs yt-dlp & FFmpeg          │
│                              │                               │
│ Browser polls /api/progress  │                               │
│  ─── fetch('/api/progress') ─> Returns speed: 5MB/s, ETA: 10s│
│                              │                               │
│ Finished!                    │ File safely moved to Desktop  │
└──────────────────────────────┴───────────────────────────────┘
```

---

### 1. The Frontend Triad: HTML, CSS, JavaScript

Think of a web page like a human body:
- **HTML (`web/index.html`) is the Skeleton**: It defines *what* exists on the page (an input box, a card, an image, a button, a progress bar). It has no styling and does no work by itself.
- **CSS (`web/style.css` + Tailwind) is the Appearance**: It defines *how* it looks (dark `#0f0f0f` background, rounded corners, red glowing buttons, smooth fonts).
- **JavaScript (`web/app.js`) is the Brain / Nervous System**: It listens for user actions (mouse clicks, typing), communicates with Python using HTTP requests (`fetch`), and updates the HTML live without reloading the page.

#### Key Functions in `web/app.js`:
- **`extractYoutubeId(url)`**: Extracts the 11-character video ID right in JavaScript using regex. This lets the browser show the video thumbnail with **0 milliseconds of delay** before the Python server even responds!
- **`fetchPreview(url)`**: Sends `GET /api/preview?url=...` to Python to retrieve the video title, channel, duration, and playlist count.
- **`startProgressPolling()`**: Runs a timer every 350ms (`setInterval`) calling `GET /api/progress`. As Python downloads, JavaScript moves the red progress bar and writes the live transfer speed (`MB/s`) and ETA onto the screen.
- **Folder Presets**: Quick buttons (`Desktop (D:)`, `Downloads`, `Music`) that instantly write the destination path into the input field when clicked.

---

### 2. The Backend Server (`server.py` & `backend/core.py`)

- **What is FastAPI?**: A modern, high-performance Python web framework. It lets us create URL endpoints (like `/api/preview`, `/api/download`) that receive requests from JavaScript and return JSON data.
- **What is Uvicorn?**: The lightning-fast ASGI server that runs FastAPI on your local machine (`127.0.0.1:8000`).
- **`BackgroundTasks` in FastAPI**: When you click Download, FastAPI delegates the heavy `yt-dlp` download to a background worker so the web server never freezes or lags.
- **`open_folder_picker()`**: When you click the "Browse" button in your browser, web browsers normally block access to your file system. Python bypasses this by launching a tiny native Windows PowerShell `FolderBrowserDialog` that pops up directly on your desktop!

---

# Summary Comparison

| Feature | Desktop GUI (`ytdl.py`) | WebUI (`server.py` + `web/`) |
| :--- | :--- | :--- |
| **Framework** | CustomTkinter (Python) | FastAPI + HTML/Tailwind/JS |
| **Window Type** | Native Tkinter window | Real Browser (Chrome/Edge/Brave) |
| **Styling** | Python code (`CTkFrame`, `CTkButton`) | Tailwind CSS (easy to match Figma) |
| **Threading** | `threading.Thread` in Python | FastAPI `BackgroundTasks` + JS polling |
| **Extensibility** | Good for quick single-file tools | Excellent for adding modern UI features |

Both branches share the exact same battle-tested download engine, collision-safe file handling, metadata tagging, and FFmpeg muxing!
