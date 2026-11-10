import ctypes
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageDraw
from yt_dlp import YoutubeDL

# Enable custom app icon on the Windows taskbar
try:
    if sys.platform.startswith("win"):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mcpeking.ytdl.app.1.0")
except Exception:
    pass

# --- YouTube Theme Palette ---
COLOR_BG = "#0f0f0f"            # YouTube Dark Canvas
COLOR_CARD = "#181818"          # Raised Card Surface
COLOR_CARD_BORDER = "#282828"   # Subtle Card Hairline Border
COLOR_INPUT_BG = "#121212"      # Input Field Background
COLOR_INPUT_BORDER = "#333333"  # Input Field Border
COLOR_RED = "#ff0000"           # Iconic YouTube Red
COLOR_RED_HOVER = "#cc0000"     # Darker Red on Hover
COLOR_BUTTON_SECONDARY = "#272727"
COLOR_BUTTON_SEC_HOVER = "#383838"
COLOR_TEXT_PRIMARY = "#ffffff"  # Crisp White Text
COLOR_TEXT_SECONDARY = "#aaaaaa" # Muted Gray for Labels
COLOR_TEXT_MUTED = "#717171"    # Status Gray

HISTORY_FILE = Path(__file__).parent / "history.json"


# --- Helper Functions ---

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
                # /select highlights the exact file
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


def create_placeholder_image(width: int = 160, height: int = 90) -> Image.Image:
    """Draws a sleek placeholder image with a muted play icon."""
    img = Image.new("RGB", (width, height), color="#202020")
    draw = ImageDraw.Draw(img)
    cx, cy = width // 2, height // 2
    draw.polygon([(cx - 8, cy - 12), (cx - 8, cy + 12), (cx + 12, cy)], fill="#3f3f3f")
    return img


def fetch_image_from_url(image_url: str, target_size=(160, 90)) -> Image.Image | None:
    """Downloads an image from a URL and resizes it to target dimensions."""
    try:
        req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read()
        img = Image.open(io.BytesIO(data))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        return img.resize(target_size, Image.Resampling.LANCZOS)
    except Exception:
        return None


def extract_bitrate_number(quality_str: str) -> str:
    """Extracts numeric bitrate from strings like '320 kbps (High)' or '192 kbps'."""
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
        # Download the highest quality thumbnail available to embed as cover art
        "writethumbnail": True,
        # Allow multi-track playlist downloads gracefully without stopping on one failure
        "ignoreerrors": True,
    }

    if format_type == "mp3":
        bitrate = extract_bitrate_number(quality)
        options.update({
            "format": "bestaudio/best",
            "postprocessors": [
                # 1. Convert WebP thumbnails to JPG for ID3 compatibility
                {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
                # 2. Extract and encode to MP3 with chosen bitrate
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate,
                },
                # 3. Add audio metadata tags
                {"key": "FFmpegMetadata"},
                # 4. Embed the thumbnail image into the MP3 file as cover art
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
                # 1. Convert WebP to JPG for MP4 compatibility
                {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
                # 2. Add video metadata tags
                {"key": "FFmpegMetadata"},
                # 3. Embed thumbnail as the MP4 video poster/cover
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
    with open("errors.txt", "a", encoding="utf-8") as file:
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


# --- Main Application ---

class YTDLApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window setup: Clean, spacious dimensions
        self.title("YouTube Downloader")
        self.geometry("540x690")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=COLOR_BG)

        # Set window and taskbar icon
        icon_path = Path(__file__).parent / "assets" / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self._preview_timer = None
        self._current_preview_url = ""
        self._last_loaded_title = ""
        self.last_download_path: Path | None = None

        # Check FFmpeg availability at startup
        self.ffmpeg_installed = check_ffmpeg()

        # Header Frame: Logo, Title, and History Button
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=24, pady=(16, 10))

        # Left side of header (Logo + Title)
        self.header_left = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.header_left.pack(side="left")

        logo_path = Path(__file__).parent / "assets" / "logo.png"
        if logo_path.exists():
            logo_pil = Image.open(logo_path)
            self.app_logo_image = ctk.CTkImage(
                light_image=logo_pil,
                dark_image=logo_pil,
                size=(36, 36),
            )
            self.logo_badge = ctk.CTkLabel(
                self.header_left,
                image=self.app_logo_image,
                text="",
            )
            self.logo_badge.pack(side="left", padx=(0, 10))
        else:
            self.logo_badge = ctk.CTkLabel(
                self.header_left,
                text=" ▶ ",
                fg_color=COLOR_RED,
                text_color=COLOR_TEXT_PRIMARY,
                corner_radius=6,
                font=ctk.CTkFont(size=14, weight="bold"),
                width=36,
                height=26,
            )
            self.logo_badge.pack(side="left", padx=(0, 10))

        self.title_label = ctk.CTkLabel(
            self.header_left,
            text="YouTube Downloader",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.title_label.pack(side="left")

        # Right side of header: History Button
        self.history_btn = ctk.CTkButton(
            self.header_frame,
            text="📜 History",
            width=84,
            height=32,
            fg_color=COLOR_BUTTON_SECONDARY,
            hover_color=COLOR_BUTTON_SEC_HOVER,
            border_color=COLOR_INPUT_BORDER,
            border_width=1,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            corner_radius=8,
            command=self.open_history_window,
        )
        self.history_btn.pack(side="right")

        # Startup FFmpeg warning banner if FFmpeg is missing from PATH
        if not self.ffmpeg_installed:
            self.ffmpeg_banner = ctk.CTkFrame(
                self,
                fg_color="#361700",
                corner_radius=8,
                border_width=1,
                border_color="#d97706",
            )
            self.ffmpeg_banner.pack(padx=24, pady=(0, 10), fill="x")

            self.ffmpeg_banner_label = ctk.CTkLabel(
                self.ffmpeg_banner,
                text="⚠️ FFmpeg was not detected on your system PATH.\nAudio MP3 conversion and 1080p+ video muxing will fail.",
                text_color="#fcd34d",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                justify="left",
            )
            self.ffmpeg_banner_label.pack(padx=12, pady=8)

        # Raised card container
        self.card = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
        )
        self.card.pack(padx=24, pady=(0, 16), fill="both", expand=True)

        # 1. URL Input Label + Frame (with Paste Button)
        self.url_label = ctk.CTkLabel(
            self.card,
            text="Video or Playlist URL",
            text_color=COLOR_TEXT_SECONDARY,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        )
        self.url_label.pack(anchor="w", padx=24, pady=(14, 4))

        self.url_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.url_frame.pack(padx=24, pady=(0, 10), fill="x")

        self.url_var = ctk.StringVar()
        self.url_var.trace_add("write", self.on_url_input_changed)

        self.url_input = ctk.CTkEntry(
            self.url_frame,
            textvariable=self.url_var,
            placeholder_text="Paste YouTube link here...",
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_INPUT_BORDER,
            text_color=COLOR_TEXT_PRIMARY,
            placeholder_text_color=COLOR_TEXT_MUTED,
            corner_radius=8,
            height=36,
        )
        self.url_input.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.paste_btn = ctk.CTkButton(
            self.url_frame,
            text="📋 Paste",
            width=75,
            height=36,
            fg_color=COLOR_BUTTON_SECONDARY,
            hover_color=COLOR_BUTTON_SEC_HOVER,
            border_color=COLOR_INPUT_BORDER,
            border_width=1,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            corner_radius=8,
            command=self.paste_from_clipboard,
        )
        self.paste_btn.pack(side="right")

        # 2. Thumbnail & Metadata Preview Card (160x90 standard 16:9)
        self.preview_card = ctk.CTkFrame(
            self.card,
            fg_color=COLOR_INPUT_BG,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
        )
        self.preview_card.pack(padx=24, pady=(0, 12), fill="x")

        self._placeholder_pil = create_placeholder_image(160, 90)
        self.thumbnail_ctk_image = ctk.CTkImage(
            light_image=self._placeholder_pil,
            dark_image=self._placeholder_pil,
            size=(160, 90),
        )
        self.thumbnail_label = ctk.CTkLabel(
            self.preview_card,
            image=self.thumbnail_ctk_image,
            text="",
            corner_radius=6,
        )
        self.thumbnail_label.pack(side="left", padx=10, pady=10)

        self.info_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.info_frame.pack(side="left", fill="both", expand=True, padx=(4, 12), pady=10)

        self.preview_title = ctk.CTkLabel(
            self.info_frame,
            text="No video loaded",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            wraplength=250,
            justify="left",
            anchor="w",
        )
        self.preview_title.pack(anchor="w", pady=(2, 4))

        self.preview_details = ctk.CTkLabel(
            self.info_frame,
            text="Paste a YouTube link above to preview",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
            wraplength=250,
            justify="left",
            anchor="w",
        )
        self.preview_details.pack(anchor="w")

        # 3. Save Destination
        self.loc_label = ctk.CTkLabel(
            self.card,
            text="Save Destination",
            text_color=COLOR_TEXT_SECONDARY,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        )
        self.loc_label.pack(anchor="w", padx=24, pady=(0, 4))

        self.folder_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.folder_frame.pack(padx=24, pady=(0, 12), fill="x")

        self.output_dir_var = ctk.StringVar(value=str(get_default_download_dir()))
        self.folder_entry = ctk.CTkEntry(
            self.folder_frame,
            textvariable=self.output_dir_var,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_INPUT_BORDER,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=8,
            height=36,
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.browse_btn = ctk.CTkButton(
            self.folder_frame,
            text="Browse",
            width=90,
            height=36,
            fg_color=COLOR_BUTTON_SECONDARY,
            hover_color=COLOR_BUTTON_SEC_HOVER,
            border_color=COLOR_INPUT_BORDER,
            border_width=1,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=8,
            command=self.browse_folder,
        )
        self.browse_btn.pack(side="right")

        # 4. Format & Quality Controls
        self.controls_label = ctk.CTkLabel(
            self.card,
            text="Format & Quality",
            text_color=COLOR_TEXT_SECONDARY,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        )
        self.controls_label.pack(anchor="w", padx=24, pady=(0, 4))

        self.controls_row = ctk.CTkFrame(self.card, fg_color="transparent")
        self.controls_row.pack(padx=24, pady=(0, 14), fill="x")

        self.format_var = ctk.StringVar(value="Audio (MP3)")
        self.format_btn = ctk.CTkSegmentedButton(
            self.controls_row,
            values=["Audio (MP3)", "Video (MP4)"],
            variable=self.format_var,
            selected_color=COLOR_RED,
            selected_hover_color=COLOR_RED_HOVER,
            unselected_color=COLOR_BUTTON_SECONDARY,
            unselected_hover_color=COLOR_BUTTON_SEC_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=8,
            height=36,
            command=self.toggle_quality,
        )
        self.format_btn.pack(side="left", fill="x", expand=True, padx=(0, 12))

        # Dynamic Quality / Bitrate Dropdown
        self.quality_var = ctk.StringVar(value="320 kbps (High)")
        self.quality_dropdown = ctk.CTkOptionMenu(
            self.controls_row,
            variable=self.quality_var,
            values=["320 kbps (High)", "256 kbps", "192 kbps (Standard)", "128 kbps (Compact)"],
            fg_color=COLOR_BUTTON_SECONDARY,
            button_color=COLOR_INPUT_BORDER,
            button_hover_color=COLOR_BUTTON_SEC_HOVER,
            dropdown_fg_color=COLOR_CARD,
            dropdown_hover_color=COLOR_RED,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=8,
            width=150,
            height=36,
        )
        self.quality_dropdown.pack(side="right")

        # 5. YouTube-Red Pill Download Button
        self.download_btn = ctk.CTkButton(
            self.card,
            text="Download",
            fg_color=COLOR_RED,
            hover_color=COLOR_RED_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            corner_radius=21,
            height=42,
            command=self.start_download_thread,
        )
        self.download_btn.pack(padx=24, pady=(2, 10), fill="x")

        # 6. Thin Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            self.card,
            height=6,
            progress_color=COLOR_RED,
            fg_color=COLOR_BUTTON_SECONDARY,
            corner_radius=3,
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(padx=24, pady=(0, 10), fill="x")

        # 7. Status Container Pill + "Show in Folder" Action Button
        self.status_card = ctk.CTkFrame(
            self.card,
            fg_color=COLOR_INPUT_BG,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            height=38,
        )
        self.status_card.pack(padx=24, pady=(0, 12), fill="x")

        self.status_label = ctk.CTkLabel(
            self.status_card,
            text="● Ready",
            text_color=COLOR_TEXT_SECONDARY,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.status_label.pack(side="left", padx=12, pady=6)

        self.open_folder_btn = ctk.CTkButton(
            self.status_card,
            text="📂 Open in Folder",
            width=120,
            height=26,
            fg_color=COLOR_BUTTON_SECONDARY,
            hover_color=COLOR_BUTTON_SEC_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            corner_radius=6,
            command=self.open_last_downloaded,
        )
        # Hidden until a download completes

    # --- Clipboard & URL Logic ---

    def paste_from_clipboard(self):
        """Pastes clipboard contents into the URL entry."""
        try:
            clipboard_text = self.clipboard_get().strip()
            if clipboard_text:
                self.url_var.set(clipboard_text)
        except Exception:
            pass

    def on_url_input_changed(self, *args):
        """Debounces URL input changes (500ms delay)."""
        url = self.url_var.get().strip()
        if not url:
            self.reset_preview()
            return
        if self._preview_timer is not None:
            self.after_cancel(self._preview_timer)
        self._preview_timer = self.after(500, self.trigger_preview_fetch, url)

    def trigger_preview_fetch(self, url: str):
        """Starts preview worker thread."""
        if url == self._current_preview_url:
            return
        self._current_preview_url = url
        self.update_status("● Loading metadata preview...", "#ffd700")
        threading.Thread(target=self._fetch_preview_worker, args=(url,), daemon=True).start()

    def _fetch_preview_worker(self, url: str):
        """Fetches thumbnail and info in background thread, with playlist handling."""
        video_id = extract_youtube_video_id(url)
        thumbnail_img = None

        if video_id:
            thumb_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
            thumbnail_img = fetch_image_from_url(thumb_url, (160, 90))
            if thumbnail_img:
                self.after(0, self._update_preview_image, thumbnail_img)

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
                return

            # Check if this is a playlist
            is_playlist = (info.get("_type") == "playlist") or is_playlist_url(url)
            if is_playlist and info.get("entries"):
                playlist_title = info.get("title") or "YouTube Playlist"
                entries = list(info.get("entries") or [])
                count = len(entries) if entries else info.get("playlist_count") or "Multi"
                title = f"📁 {playlist_title}"
                details = f"Playlist ({count} videos) • No cookies required"

                # Grab thumbnail from first item if possible
                if thumbnail_img is None and entries and entries[0]:
                    first_thumb = entries[0].get("thumbnail") or entries[0].get("thumbnails", [{}])[-1].get("url")
                    if first_thumb:
                        thumbnail_img = fetch_image_from_url(first_thumb, (160, 90))
                        if thumbnail_img:
                            self.after(0, self._update_preview_image, thumbnail_img)
            else:
                title = info.get("title") or "Unknown Video"
                channel = info.get("uploader") or info.get("channel") or ""
                dur_str = format_duration(info.get("duration"))
                details_parts = [p for p in (channel, dur_str) if p]
                details = " • ".join(details_parts) if details_parts else "YouTube Video"

                if thumbnail_img is None and info.get("thumbnail"):
                    thumbnail_img = fetch_image_from_url(info["thumbnail"], (160, 90))
                    if thumbnail_img:
                        self.after(0, self._update_preview_image, thumbnail_img)

            self._last_loaded_title = title
            self.after(0, self._update_preview_info, title, details)
            self.after(0, self.update_status, "● Ready to download", "#00e676")
        except Exception:
            if not thumbnail_img:
                self.after(0, self.reset_preview, "Could not load preview", "Check URL")
            self.after(0, self.update_status, "● Ready", COLOR_TEXT_SECONDARY)

    def _update_preview_image(self, pil_image: Image.Image):
        ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(160, 90))
        self.thumbnail_label.configure(image=ctk_img)
        self.thumbnail_label.image = ctk_img

    def _update_preview_info(self, title: str, details: str):
        self.preview_title.configure(text=title)
        self.preview_details.configure(text=details)

    def reset_preview(self, title: str = "No video loaded", details: str = "Paste a YouTube link above to preview"):
        self._current_preview_url = ""
        self._last_loaded_title = ""
        self._update_preview_image(self._placeholder_pil)
        self.preview_title.configure(text=title)
        self.preview_details.configure(text=details)

    # --- UI & Download Handlers ---

    def browse_folder(self):
        selected_dir = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if selected_dir:
            self.output_dir_var.set(selected_dir)

    def toggle_quality(self, _value=None):
        """Swaps options between audio bitrates and video resolutions."""
        if "MP4" in self.format_var.get():
            self.quality_dropdown.configure(
                values=["Best Available", "1080p", "720p", "480p", "360p"],
            )
            self.quality_var.set("Best Available")
        else:
            self.quality_dropdown.configure(
                values=["320 kbps (High)", "256 kbps", "192 kbps (Standard)", "128 kbps (Compact)"],
            )
            self.quality_var.set("320 kbps (High)")

    def update_status(self, text: str, color: str = COLOR_TEXT_SECONDARY):
        self.status_label.configure(text=text, text_color=color)

    def open_last_downloaded(self):
        """Opens Explorer and selects the last downloaded file."""
        if self.last_download_path:
            open_in_explorer(self.last_download_path)

    def start_download_thread(self):
        url = self.url_input.get().strip()
        if not url:
            self.update_status("● Please enter a valid URL.", "#ff4d4d")
            return

        destination_path_str = self.output_dir_var.get().strip()
        if not destination_path_str:
            self.update_status("● Please enter a destination folder.", "#ff4d4d")
            return

        destination_dir = Path(destination_path_str)
        if not destination_dir.is_dir():
            self.update_status("● Folder does not exist. Please choose a valid folder.", "#ff4d4d")
            return

        # Hide 'Open in Folder' button during active download
        self.open_folder_btn.pack_forget()
        self.set_inputs_enabled(False)
        self.progress_bar.set(0)
        self.update_status("● Starting download...", "#ffd700")

        format_type = "mp3" if "MP3" in self.format_var.get() else "mp4"
        threading.Thread(
            target=self.download_process,
            args=(url, format_type, self.quality_var.get(), destination_dir),
            daemon=True,
        ).start()

    def progress_hook(self, d: dict):
        if d.get("status") == "downloading":
            downloaded = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            percent = (downloaded / total) if total > 0 else 0
            self.after(0, self.progress_bar.set, percent)

            speed_str = clean_error_message(d.get("_speed_str") or "")
            eta_str = clean_error_message(d.get("_eta_str") or "")
            info_dict = d.get("info_dict") or {}
            playlist_index = info_dict.get("playlist_index")
            n_entries = info_dict.get("n_entries")

            parts = []
            if playlist_index and n_entries:
                parts.append(f"● Item {playlist_index}/{n_entries} ({percent * 100:.1f}%)")
            else:
                parts.append(f"● Downloading: {percent * 100:.1f}%")

            if speed_str:
                parts.append(speed_str)
            if eta_str:
                parts.append(f"ETA: {eta_str}")

            self.after(0, self.update_status, " • ".join(parts), "#ffd700")

        elif d.get("status") == "finished":
            self.after(0, self.progress_bar.set, 1.0)
            self.after(0, self.update_status, "● Merging & embedding cover art...", "#ffd700")

    def download_process(self, url: str, format_type: str, quality: str, destination_dir: Path):
        try:
            with tempfile.TemporaryDirectory(prefix="ytdl_") as temp_dir:
                ydl_opts = build_ydl_options(temp_dir, format_type, quality, self.progress_hook)
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                # Only move media files (skip stray images or temp chunks)
                valid_extensions = {".mp3", ".mp4", ".m4a", ".webm", ".mkv"}
                completed = [
                    Path(temp_dir) / f for f in os.listdir(temp_dir)
                    if not f.endswith((".part", ".ytdl"))
                    and (Path(temp_dir) / f).is_file()
                    and (Path(temp_dir) / f).suffix.lower() in valid_extensions
                ]

                if not completed:
                    self.after(0, self.update_status, "● Download completed, but no media files saved.", "#ff4d4d")
                    return

                last_file = None
                for src in completed:
                    dst = resolve_unique_path(destination_dir, src.name)
                    shutil.move(str(src), str(dst))
                    last_file = dst

                    # Record to history
                    fmt_label = f"Audio ({quality})" if format_type == "mp3" else f"Video ({quality})"
                    save_history_entry(dst.stem, fmt_label, dst)

                self.last_download_path = last_file

                # Show 'Open in Folder' action button
                def on_success():
                    self.update_status(f"✔ Done! Saved to {destination_dir.name}", "#00e676")
                    self.open_folder_btn.pack(side="right", padx=(0, 8), pady=4)
                    self.reset_ui(clear_url=True)

                self.after(0, on_success)
        except Exception as error:
            cleaned = clean_error_message(str(error))
            log_error(url, cleaned)
            self.after(0, self.update_status, f"✖ Error: {cleaned}", "#ff4d4d")
            self.after(0, self.reset_ui, False)

    def set_inputs_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.download_btn.configure(state=state)
        self.url_input.configure(state=state)
        self.paste_btn.configure(state=state)
        self.folder_entry.configure(state=state)
        self.browse_btn.configure(state=state)
        self.format_btn.configure(state=state)
        self.quality_dropdown.configure(state=state)

    def reset_ui(self, clear_url: bool = False):
        self.set_inputs_enabled(True)
        if clear_url:
            self.url_var.set("")
            self.reset_preview()
        self.progress_bar.set(0)

    # --- History Window ---

    def open_history_window(self):
        """Displays download history in a sleek modal dialog."""
        history = load_history()

        hist_win = ctk.CTkToplevel(self)
        hist_win.title("Download History")
        hist_win.geometry("500x440")
        hist_win.resizable(False, False)
        hist_win.configure(fg_color=COLOR_BG)
        hist_win.grab_set()

        header = ctk.CTkFrame(hist_win, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 8))

        lbl = ctk.CTkLabel(
            header,
            text="Download History",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl.pack(side="left")

        def clear_and_refresh():
            clear_history_file()
            for widget in scroll_frame.winfo_children():
                widget.destroy()
            empty_lbl = ctk.CTkLabel(
                scroll_frame,
                text="No downloads recorded yet.",
                text_color=COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=12),
            )
            empty_lbl.pack(pady=40)

        clear_btn = ctk.CTkButton(
            header,
            text="Clear",
            width=65,
            height=28,
            fg_color="#331111",
            hover_color="#551111",
            text_color="#ff7777",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            corner_radius=6,
            command=clear_and_refresh,
        )
        clear_btn.pack(side="right")

        scroll_frame = ctk.CTkScrollableFrame(
            hist_win,
            fg_color=COLOR_CARD,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
        )
        scroll_frame.pack(padx=20, pady=(0, 16), fill="both", expand=True)

        if not history:
            empty_lbl = ctk.CTkLabel(
                scroll_frame,
                text="No downloads recorded yet.",
                text_color=COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=12),
            )
            empty_lbl.pack(pady=40)
            return

        for entry in history:
            item_frame = ctk.CTkFrame(
                scroll_frame,
                fg_color=COLOR_INPUT_BG,
                corner_radius=8,
                border_width=1,
                border_color=COLOR_CARD_BORDER,
            )
            item_frame.pack(fill="x", pady=4, padx=4)

            text_col = ctk.CTkFrame(item_frame, fg_color="transparent")
            text_col.pack(side="left", fill="both", expand=True, padx=10, pady=8)

            title_lbl = ctk.CTkLabel(
                text_col,
                text=entry.get("title", "Unknown Title"),
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=COLOR_TEXT_PRIMARY,
                anchor="w",
                wraplength=310,
                justify="left",
            )
            title_lbl.pack(anchor="w")

            meta_str = f"{entry.get('format', '')} • {entry.get('timestamp', '')}"
            meta_lbl = ctk.CTkLabel(
                text_col,
                text=meta_str,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
            )
            meta_lbl.pack(anchor="w")

            target_path = Path(entry.get("path", ""))
            open_btn = ctk.CTkButton(
                item_frame,
                text="📂 Open",
                width=65,
                height=28,
                fg_color=COLOR_BUTTON_SECONDARY,
                hover_color=COLOR_BUTTON_SEC_HOVER,
                text_color=COLOR_TEXT_PRIMARY,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                corner_radius=6,
                command=lambda p=target_path: open_in_explorer(p),
            )
            open_btn.pack(side="right", padx=10, pady=8)


def main():
    app = YTDLApp()
    app.mainloop()


if __name__ == "__main__":
    main()
