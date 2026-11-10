import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from PIL import Image
from yt_dlp import YoutubeDL

ROOT_DIR = Path(__file__).parent.parent
HISTORY_FILE = ROOT_DIR / "history.json"


def check_ffmpeg() -> bool:
    """Checks if FFmpeg is installed and accessible on PATH."""
    return shutil.which("ffmpeg") is not None


def get_default_download_dir() -> Path:
    """Finds D:/Desktop if available, or falls back to system Desktop/Downloads."""
    d_desktop = Path("D:/Desktop")
    if d_desktop.is_dir():
        return d_desktop
    desktop = Path.home() / "Desktop"
    if desktop.is_dir():
        return desktop
    downloads = Path.home() / "Downloads"
    return downloads if downloads.is_dir() else Path.home()


def resolve_unique_path(directory: Path, filename: str) -> Path:
    """Prevents file overwrite by appending (1), (2), etc."""
    destination = directory / filename
    if not destination.exists():
        return destination

    stem, suffix = destination.stem, destination.suffix
    counter = 1
    while True:
        candidate = directory / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def open_in_explorer(target_path: Path) -> None:
    """Opens Windows Explorer with the specific file selected, or opens folder."""
    try:
        if target_path.exists():
            if sys.platform.startswith("win"):
                subprocess.Popen(f'explorer /select,"{str(target_path)}"')
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(target_path)])
            else:
                subprocess.Popen(["xdg-open", str(target_path.parent)])
        elif target_path.parent.exists():
            if sys.platform.startswith("win"):
                os.startfile(str(target_path.parent))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target_path.parent)])
            else:
                subprocess.Popen(["xdg-open", str(target_path.parent)])
    except Exception:
        pass


def extract_youtube_video_id(url: str) -> str | None:
    """Extracts 11-char video ID from standard/short/music YouTube URLs."""
    patterns = [
        r"(?:v=|\/vi\/|youtu\.be\/|\/shorts\/)([0-9A-Za-z_-]{11})",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def is_playlist_url(url: str) -> bool:
    """Checks if the URL is or contains a playlist parameter."""
    return ("list=" in url) or ("/playlist" in url)


def format_duration(seconds: int | float | None) -> str:
    """Formats duration in seconds to standard MM:SS or HH:MM:SS."""
    if not seconds:
        return ""
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    return f"{hours}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins}:{secs:02d}"


def extract_bitrate_number(quality_str: str) -> str:
    """Extracts numeric bitrate from strings like '320 kbps' or '192 kbps'."""
    match = re.search(r"(\d+)", quality_str)
    return match.group(1) if match else "192"


def build_ydl_options(temp_dir: str, format_type: str, quality: str, progress_hook) -> dict:
    """
    Builds yt-dlp configuration with highest-quality thumbnail embedding.
    Embeds artwork directly into MP3 tags (album art) and MP4 containers.
    """
    options = {
        "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook] if progress_hook else [],
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "windowsfilenames": True,
        "retries": 3,
        "fragment_retries": 3,
        "writethumbnail": True,
        "ignoreerrors": True,
    }

    if format_type == "mp3":
        bitrate = extract_bitrate_number(quality)
        options.update({
            "format": "bestaudio/best",
            "postprocessors": [
                {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate,
                },
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail", "already_have_thumbnail": False},
            ],
        })
    else:
        if quality in ("best", "Best Available"):
            format_str = "bestvideo+bestaudio/best"
        else:
            match = re.search(r"(\d+)", quality)
            height = match.group(1) if match else "1080"
            format_str = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"

        options.update({
            "format": format_str,
            "merge_output_format": "mp4",
            "postprocessors": [
                {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail", "already_have_thumbnail": False},
            ],
        })

    return options


def clean_error_message(raw_error: str) -> str:
    """Strips terminal color codes and cleans up error strings."""
    cleaned = re.sub(r"\x1b\[[0-9;]*m", "", str(raw_error)).strip()
    return cleaned[6:].strip() if cleaned.startswith("ERROR:") else cleaned


def log_error(url: str, error_message: str) -> None:
    """Appends timestamped error details to 'errors.txt'."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(ROOT_DIR / "errors.txt", "a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] URL: {url} | Error: {error_message}\n")


def load_history() -> list[dict]:
    """Loads recent download history from history.json."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history_entry(title: str, format_desc: str, file_path: Path) -> None:
    """Appends a successful download to history.json (keeps latest 40 entries)."""
    history = load_history()
    entry = {
        "title": title,
        "format": format_desc,
        "path": str(file_path),
        "timestamp": time.strftime("%Y-%m-%d %H:%M"),
    }
    history.insert(0, entry)
    history = history[:40]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def clear_history_file() -> None:
    """Clears history.json entries."""
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
    except Exception:
        pass
