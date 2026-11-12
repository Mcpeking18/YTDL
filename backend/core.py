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


def get_common_folder_presets() -> list[dict]:
    """Returns a list of common accessible download folders for quick 1-click selection."""
    presets = []
    d_desktop = Path("D:/Desktop")
    if d_desktop.is_dir():
        presets.append({"label": "Desktop (D:)", "path": str(d_desktop)})

    c_desktop = Path.home() / "Desktop"
    if c_desktop.is_dir() and c_desktop != d_desktop:
        presets.append({"label": "Desktop (C:)", "path": str(c_desktop)})

    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        presets.append({"label": "Downloads", "path": str(downloads)})

    music = Path.home() / "Music"
    if music.is_dir():
        presets.append({"label": "Music", "path": str(music)})

    videos = Path.home() / "Videos"
    if videos.is_dir():
        presets.append({"label": "Videos", "path": str(videos)})

    return presets


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


def open_folder_picker(initial_dir: str = "") -> str:
    """Invokes native Windows folder picker in a subprocess without freezing."""
    if not sys.platform.startswith("win"):
        return initial_dir
    try:
        init_path = initial_dir if (initial_dir and Path(initial_dir).is_dir()) else str(get_default_download_dir())
        ps_script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
            f"$f.SelectedPath = '{init_path}'; "
            "$f.Description = 'Select Download Folder'; "
            "$f.ShowNewFolderButton = $true; "
            "if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.SelectedPath }"
        )
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=40,
        )
        selected = proc.stdout.strip()
        if selected and Path(selected).is_dir():
            return selected
        return initial_dir
    except Exception:
        return initial_dir


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


def fetch_metadata_preview(url: str) -> dict:
    """
    Fetches video or playlist metadata and thumbnail URL.
    Guarantees a thumbnail if a valid YouTube video ID is found.
    """
    url = url.strip()
    if not url:
        return {"success": False, "error": "URL cannot be empty"}

    video_id = extract_youtube_video_id(url)
    default_thumb = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg" if video_id else ""

    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            if video_id:
                return {
                    "success": True,
                    "title": "YouTube Video",
                    "details": "Ready to download",
                    "thumbnail": default_thumb,
                    "is_playlist": False,
                }
            return {"success": False, "error": "Could not fetch metadata for this URL"}

        is_playlist = (info.get("_type") == "playlist") or is_playlist_url(url)
        if is_playlist and info.get("entries"):
            playlist_title = info.get("title") or "YouTube Playlist"
            entries = list(info.get("entries") or [])
            count = len(entries) if entries else info.get("playlist_count") or 0
            title = f"📁 {playlist_title}"
            details = f"Playlist ({count} videos) • No cookies required"

            thumb = default_thumb
            if not thumb and entries and entries[0]:
                thumb = entries[0].get("thumbnail") or entries[0].get("thumbnails", [{}])[-1].get("url") or ""
            if not thumb and info.get("thumbnails"):
                thumb = info["thumbnails"][-1].get("url") or ""
        else:
            title = info.get("title") or "Unknown Video"
            channel = info.get("uploader") or info.get("channel") or ""
            dur_str = format_duration(info.get("duration"))
            details_parts = [p for p in (channel, dur_str) if p]
            details = " • ".join(details_parts) if details_parts else "YouTube Video"
            thumb = default_thumb or info.get("thumbnail") or ""

        return {
            "success": True,
            "title": title,
            "details": details,
            "thumbnail": thumb,
            "is_playlist": is_playlist,
        }
    except Exception as e:
        if video_id:
            return {
                "success": True,
                "title": "YouTube Video",
                "details": f"ID: {video_id} • Ready",
                "thumbnail": default_thumb,
                "is_playlist": False,
            }
        return {"success": False, "error": clean_error_message(str(e))}


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


def set_history_file_path(path: Path | None = None) -> None:
    """Sets a custom history file path (useful for testing without touching live history)."""
    global HISTORY_FILE
    HISTORY_FILE = path if path else (ROOT_DIR / "history.json")


def get_ytdlp_version() -> str:
    """Returns the currently installed yt-dlp version string."""
    try:
        import yt_dlp.version
        return getattr(yt_dlp.version, "__version__", "unknown")
    except Exception:
        return "unknown"


def update_ytdlp_via_uv() -> dict:
    """Runs 'uv lock --upgrade-package yt-dlp' and 'uv sync' in the project root."""
    uv_path = shutil.which("uv")
    if not uv_path:
        return {"success": False, "error": "uv is not installed or not on PATH."}
    try:
        old_version = get_ytdlp_version()

        # 1. Upgrade yt-dlp in uv.lock
        proc = subprocess.run(
            [uv_path, "lock", "--upgrade-package", "yt-dlp"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            return {"success": False, "error": proc.stderr.strip() or "Failed to lock yt-dlp"}

        # 2. Sync the virtual environment
        sync_proc = subprocess.run(
            [uv_path, "sync"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if sync_proc.returncode != 0:
            return {"success": False, "error": sync_proc.stderr.strip() or "Failed to sync virtual environment"}

        # 3. Query new version from the virtual environment
        ver_proc = subprocess.run(
            [uv_path, "run", "python", "-c", "import yt_dlp.version; print(yt_dlp.version.__version__)"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=15,
        )
        new_version = ver_proc.stdout.strip() if ver_proc.returncode == 0 else get_ytdlp_version()
        is_updated = (new_version != old_version)

        return {
            "success": True,
            "version": new_version,
            "old_version": old_version,
            "updated": is_updated,
            "message": f"Updated to v{new_version}!" if is_updated else f"Already on latest v{new_version}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


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
