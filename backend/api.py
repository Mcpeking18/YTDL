import json
import os
import shutil
import tempfile
import threading
from pathlib import Path
from tkinter import Tk, filedialog
from yt_dlp import YoutubeDL

from backend.core import (
    build_ydl_options,
    check_ffmpeg,
    clean_error_message,
    clear_history_file,
    extract_youtube_video_id,
    format_duration,
    get_default_download_dir,
    is_playlist_url,
    load_history,
    log_error,
    open_in_explorer,
    resolve_unique_path,
    save_history_entry,
)


class DownloaderAPI:
    def __init__(self, window=None):
        self.window = window
        self._is_downloading = False
        self._last_download_path: Path | None = None

    def get_initial_state(self) -> dict:
        """Returns startup context for the UI."""
        return {
            "default_dir": str(get_default_download_dir()),
            "ffmpeg_installed": check_ffmpeg(),
            "history": load_history(),
        }

    def get_preview(self, url: str) -> dict:
        """Fetches metadata and thumbnail URL for live preview."""
        url = url.strip()
        if not url:
            return {"success": False, "error": "Empty URL"}

        video_id = extract_youtube_video_id(url)
        thumb_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg" if video_id else None

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
                return {"success": False, "error": "Could not fetch video info"}

            is_playlist = (info.get("_type") == "playlist") or is_playlist_url(url)
            if is_playlist and info.get("entries"):
                playlist_title = info.get("title") or "YouTube Playlist"
                entries = list(info.get("entries") or [])
                count = len(entries) if entries else info.get("playlist_count") or 0
                title = f"📁 {playlist_title}"
                details = f"Playlist ({count} videos) • No cookies required"

                if not thumb_url and entries and entries[0]:
                    thumb_url = entries[0].get("thumbnail") or entries[0].get("thumbnails", [{}])[-1].get("url")
            else:
                title = info.get("title") or "Unknown Video"
                channel = info.get("uploader") or info.get("channel") or ""
                dur_str = format_duration(info.get("duration"))
                details_parts = [p for p in (channel, dur_str) if p]
                details = " • ".join(details_parts) if details_parts else "YouTube Video"

                if not thumb_url and info.get("thumbnail"):
                    thumb_url = info.get("thumbnail")

            return {
                "success": True,
                "title": title,
                "details": details,
                "thumbnail": thumb_url or "",
                "is_playlist": is_playlist,
            }
        except Exception as e:
            return {"success": False, "error": clean_error_message(str(e))}

    def select_folder(self) -> str | None:
        """Opens native folder picker dialog."""
        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(initialdir=str(get_default_download_dir()))
        root.destroy()
        return selected if selected else None

    def start_download(self, url: str, format_type: str, quality: str, destination_dir_str: str) -> dict:
        """Initiates download process in background thread."""
        if self._is_downloading:
            return {"success": False, "error": "A download is already running."}

        url = url.strip()
        if not url:
            return {"success": False, "error": "Please enter a valid URL."}

        destination_dir = Path(destination_dir_str.strip())
        if not destination_dir.is_dir():
            return {"success": False, "error": "Destination folder does not exist."}

        self._is_downloading = True
        threading.Thread(
            target=self._download_worker,
            args=(url, format_type, quality, destination_dir),
            daemon=True,
        ).start()
        return {"success": True}

    def _send_event(self, event_type: str, payload: dict):
        """Dispatches an event payload to the frontend web window."""
        if self.window:
            try:
                js_code = f"window.onAppEvent({json.dumps(event_type)}, {json.dumps(payload)});"
                self.window.evaluate_js(js_code)
            except Exception:
                pass

    def _download_worker(self, url: str, format_type: str, quality: str, destination_dir: Path):
        def progress_hook(d: dict):
            if d.get("status") == "downloading":
                downloaded = d.get("downloaded_bytes") or 0
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                percent = (downloaded / total) if total > 0 else 0
                speed = clean_error_message(d.get("_speed_str") or "")
                eta = clean_error_message(d.get("_eta_str") or "")
                info = d.get("info_dict") or {}

                self._send_event("progress", {
                    "percent": round(percent * 100, 1),
                    "speed": speed,
                    "eta": eta,
                    "item_index": info.get("playlist_index"),
                    "item_total": info.get("n_entries"),
                })
            elif d.get("status") == "finished":
                self._send_event("processing", {"message": "Merging streams & embedding cover art..."})

        try:
            with tempfile.TemporaryDirectory(prefix="ytdl_") as temp_dir:
                ydl_opts = build_ydl_options(temp_dir, format_type, quality, progress_hook)
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                valid_extensions = {".mp3", ".mp4", ".m4a", ".webm", ".mkv"}
                completed = [
                    Path(temp_dir) / f for f in os.listdir(temp_dir)
                    if not f.endswith((".part", ".ytdl"))
                    and (Path(temp_dir) / f).is_file()
                    and (Path(temp_dir) / f).suffix.lower() in valid_extensions
                ]

                if not completed:
                    self._is_downloading = False
                    self._send_event("error", {"error": "Download completed, but no media files were generated."})
                    return

                last_file = None
                for src in completed:
                    dst = resolve_unique_path(destination_dir, src.name)
                    shutil.move(str(src), str(dst))
                    last_file = dst

                    fmt_label = f"Audio ({quality})" if format_type == "mp3" else f"Video ({quality})"
                    save_history_entry(dst.stem, fmt_label, dst)

                self._last_download_path = last_file
                self._is_downloading = False
                self._send_event("success", {
                    "filename": last_file.name,
                    "path": str(last_file),
                    "dir": destination_dir.name,
                    "history": load_history(),
                })

        except Exception as error:
            self._is_downloading = False
            cleaned = clean_error_message(str(error))
            log_error(url, cleaned)
            self._send_event("error", {"error": cleaned})

    def open_path(self, path_str: str):
        """Opens file or directory in OS file manager."""
        if path_str:
            open_in_explorer(Path(path_str))

    def open_last_download(self):
        """Opens the most recently downloaded item in file manager."""
        if self._last_download_path:
            open_in_explorer(self._last_download_path)

    def clear_history(self) -> list:
        """Clears download history."""
        clear_history_file()
        return []
