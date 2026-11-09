import io
import os
import re
import shutil
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageDraw
from yt_dlp import YoutubeDL

# --- YouTube Theme Palette ---
COLOR_BG = "#0f0f0f"            # YouTube Dark Canvas
COLOR_CARD = "#181818"          # Raised Card Surface
COLOR_CARD_BORDER = "#282828"   # Subtle Hairline Border
COLOR_INPUT_BG = "#121212"      # Input Field Background
COLOR_INPUT_BORDER = "#333333"  # Input Field Border
COLOR_RED = "#ff0000"           # Iconic YouTube Red
COLOR_RED_HOVER = "#cc0000"     # Darker Red on Hover
COLOR_BUTTON_SECONDARY = "#272727"
COLOR_BUTTON_SEC_HOVER = "#383838"
COLOR_TEXT_PRIMARY = "#ffffff"  # Crisp White Text
COLOR_TEXT_SECONDARY = "#aaaaaa" # Muted Gray for Labels
COLOR_TEXT_MUTED = "#717171"    # Status Gray


# --- Helper Functions ---

def get_default_download_dir() -> Path:
    """Finds Desktop or Downloads folder across Windows/Mac/Linux."""
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


def format_duration(seconds: int | float | None) -> str:
    """Formats duration in seconds to standard MM:SS or HH:MM:SS."""
    if not seconds:
        return ""
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    return f"{hours}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins}:{secs:02d}"


def create_placeholder_image(width: int = 120, height: int = 68) -> Image.Image:
    """Draws a sleek placeholder image with a muted play icon."""
    img = Image.new("RGB", (width, height), color="#202020")
    draw = ImageDraw.Draw(img)
    cx, cy = width // 2, height // 2
    draw.polygon([(cx - 6, cy - 9), (cx - 6, cy + 9), (cx + 9, cy)], fill="#3f3f3f")
    return img


def fetch_image_from_url(image_url: str, target_size=(120, 68)) -> Image.Image | None:
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


def build_ydl_options(temp_dir: str, format_type: str, quality: str, progress_hook) -> dict:
    """Builds yt-dlp configuration for audio (mp3) or video (mp4)."""
    options = {
        "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "windowsfilenames": True,
        "retries": 3,
        "fragment_retries": 3,
    }
    if format_type == "mp3":
        options.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        if quality == "best":
            format_str = "bestvideo+bestaudio/best"
        else:
            height = quality.replace("p", "")
            format_str = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
        options.update({"format": format_str, "merge_output_format": "mp4"})
    return options


def clean_error_message(raw_error: str) -> str:
    """Strips terminal color codes and cleans up error strings."""
    cleaned = re.sub(r"\x1b\[[0-9;]*m", "", raw_error).strip()
    return cleaned[6:].strip() if cleaned.startswith("ERROR:") else cleaned


def log_error(url: str, error_message: str) -> None:
    """Appends timestamped error details to 'errors.txt'."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open("errors.txt", "a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] URL: {url} | Error: {error_message}\n")


# --- Main Application ---

class YTDLApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window setup: Compact, fits comfortably on any screen scaling
        self.title("YouTube Downloader")
        self.geometry("500x570")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=COLOR_BG)

        self._preview_timer = None
        self._current_preview_url = ""

        # Header with YouTube red play badge
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(pady=(14, 8))

        self.logo_badge = ctk.CTkLabel(
            self.header_frame,
            text=" ▶ ",
            fg_color=COLOR_RED,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=6,
            font=ctk.CTkFont(size=13, weight="bold"),
            width=32,
            height=22,
        )
        self.logo_badge.pack(side="left", padx=(0, 8))

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="YouTube Downloader",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.title_label.pack(side="left")

        # Raised card container
        self.card = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
        )
        self.card.pack(padx=20, pady=(0, 14), fill="both", expand=True)

        # 1. URL Input
        self.url_label = ctk.CTkLabel(
            self.card,
            text="Video or Playlist URL",
            text_color=COLOR_TEXT_SECONDARY,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
        )
        self.url_label.pack(anchor="w", padx=20, pady=(12, 3))

        self.url_var = ctk.StringVar()
        self.url_var.trace_add("write", self.on_url_input_changed)

        self.url_input = ctk.CTkEntry(
            self.card,
            textvariable=self.url_var,
            placeholder_text="Paste YouTube link here...",
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_INPUT_BORDER,
            text_color=COLOR_TEXT_PRIMARY,
            placeholder_text_color=COLOR_TEXT_MUTED,
            corner_radius=6,
            height=32,
        )
        self.url_input.pack(padx=20, pady=(0, 8), fill="x")

        # 2. Thumbnail & Metadata Preview Card (Compact)
        self.preview_card = ctk.CTkFrame(
            self.card,
            fg_color=COLOR_INPUT_BG,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
        )
        self.preview_card.pack(padx=20, pady=(0, 10), fill="x")

        self._placeholder_pil = create_placeholder_image(120, 68)
        self.thumbnail_ctk_image = ctk.CTkImage(
            light_image=self._placeholder_pil,
            dark_image=self._placeholder_pil,
            size=(120, 68),
        )
        self.thumbnail_label = ctk.CTkLabel(
            self.preview_card,
            image=self.thumbnail_ctk_image,
            text="",
            corner_radius=4,
        )
        self.thumbnail_label.pack(side="left", padx=8, pady=8)

        self.info_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.info_frame.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)

        self.preview_title = ctk.CTkLabel(
            self.info_frame,
            text="No video loaded",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            wraplength=230,
            justify="left",
            anchor="w",
        )
        self.preview_title.pack(anchor="w", pady=(2, 2))

        self.preview_details = ctk.CTkLabel(
            self.info_frame,
            text="Paste link above to preview",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLOR_TEXT_MUTED,
            wraplength=230,
            justify="left",
            anchor="w",
        )
        self.preview_details.pack(anchor="w")

        # 3. Save Destination
        self.loc_label = ctk.CTkLabel(
            self.card,
            text="Save Destination",
            text_color=COLOR_TEXT_SECONDARY,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
        )
        self.loc_label.pack(anchor="w", padx=20, pady=(0, 3))

        self.folder_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.folder_frame.pack(padx=20, pady=(0, 10), fill="x")

        self.output_dir_var = ctk.StringVar(value=str(get_default_download_dir()))
        self.folder_entry = ctk.CTkEntry(
            self.folder_frame,
            textvariable=self.output_dir_var,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_INPUT_BORDER,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=6,
            height=32,
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.browse_btn = ctk.CTkButton(
            self.folder_frame,
            text="Browse",
            width=76,
            height=32,
            fg_color=COLOR_BUTTON_SECONDARY,
            hover_color=COLOR_BUTTON_SEC_HOVER,
            border_color=COLOR_INPUT_BORDER,
            border_width=1,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=6,
            command=self.browse_folder,
        )
        self.browse_btn.pack(side="right")

        # 4. Format & Quality Controls
        self.controls_row = ctk.CTkFrame(self.card, fg_color="transparent")
        self.controls_row.pack(padx=20, pady=(0, 12), fill="x")

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
            corner_radius=6,
            height=32,
            command=self.toggle_quality,
        )
        self.format_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.quality_var = ctk.StringVar(value="best")
        self.quality_dropdown = ctk.CTkOptionMenu(
            self.controls_row,
            variable=self.quality_var,
            values=["best", "1080p", "720p", "480p", "360p"],
            fg_color=COLOR_BUTTON_SECONDARY,
            button_color=COLOR_INPUT_BORDER,
            button_hover_color=COLOR_BUTTON_SEC_HOVER,
            dropdown_fg_color=COLOR_CARD,
            dropdown_hover_color=COLOR_RED,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=6,
            width=110,
            height=32,
        )
        self.quality_dropdown.pack(side="right")
        self.quality_dropdown.configure(state="disabled")

        # 5. Download Button
        self.download_btn = ctk.CTkButton(
            self.card,
            text="Download",
            fg_color=COLOR_RED,
            hover_color=COLOR_RED_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            corner_radius=18,
            height=36,
            command=self.start_download_thread,
        )
        self.download_btn.pack(padx=20, pady=(0, 10), fill="x")

        # 6. Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            self.card,
            height=5,
            progress_color=COLOR_RED,
            fg_color=COLOR_BUTTON_SECONDARY,
            corner_radius=2,
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(padx=20, pady=(0, 10), fill="x")

        # 7. Status Pill
        self.status_card = ctk.CTkFrame(
            self.card,
            fg_color=COLOR_INPUT_BG,
            corner_radius=6,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            height=28,
        )
        self.status_card.pack(padx=20, pady=(0, 12), fill="x")

        self.status_label = ctk.CTkLabel(
            self.status_card,
            text="● Ready",
            text_color=COLOR_TEXT_SECONDARY,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.status_label.pack(pady=4)

    # --- Preview Logic ---

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
        self.update_status("● Loading video preview...", "#ffd700")
        threading.Thread(target=self._fetch_preview_worker, args=(url,), daemon=True).start()

    def _fetch_preview_worker(self, url: str):
        """Fetches thumbnail and info in background thread."""
        video_id = extract_youtube_video_id(url)
        thumbnail_img = None

        if video_id:
            thumb_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
            thumbnail_img = fetch_image_from_url(thumb_url, (120, 68))
            if thumbnail_img:
                self.after(0, self._update_preview_image, thumbnail_img)

        try:
            ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": True}
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info:
                return

            title = info.get("title") or "Unknown Video"
            channel = info.get("uploader") or info.get("channel") or ""
            dur_str = format_duration(info.get("duration"))
            details_parts = [p for p in (channel, dur_str) if p]
            details = " • ".join(details_parts) if details_parts else "YouTube Video"

            if thumbnail_img is None and info.get("thumbnail"):
                thumbnail_img = fetch_image_from_url(info["thumbnail"], (120, 68))
                if thumbnail_img:
                    self.after(0, self._update_preview_image, thumbnail_img)

            self.after(0, self._update_preview_info, title, details)
            self.after(0, self.update_status, "● Ready to download", "#00e676")
        except Exception:
            if not thumbnail_img:
                self.after(0, self.reset_preview, "Could not load preview", "Check URL")
            self.after(0, self.update_status, "● Ready", COLOR_TEXT_SECONDARY)

    def _update_preview_image(self, pil_image: Image.Image):
        ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(120, 68))
        self.thumbnail_label.configure(image=ctk_img)
        self.thumbnail_label.image = ctk_img

    def _update_preview_info(self, title: str, details: str):
        self.preview_title.configure(text=title)
        self.preview_details.configure(text=details)

    def reset_preview(self, title: str = "No video loaded", details: str = "Paste link above to preview"):
        self._current_preview_url = ""
        self._update_preview_image(self._placeholder_pil)
        self.preview_title.configure(text=title)
        self.preview_details.configure(text=details)

    # --- UI & Download Handlers ---

    def browse_folder(self):
        selected_dir = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if selected_dir:
            self.output_dir_var.set(selected_dir)

    def toggle_quality(self, _value=None):
        if "MP4" in self.format_var.get():
            self.quality_dropdown.configure(state="normal")
        else:
            self.quality_dropdown.configure(state="disabled")

    def update_status(self, text: str, color: str = COLOR_TEXT_SECONDARY):
        self.status_label.configure(text=text, text_color=color)

    def start_download_thread(self):
        url = self.url_input.get().strip()
        if not url:
            self.update_status("● Please enter a valid URL.", "#ff4d4d")
            return

        destination_dir = Path(self.output_dir_var.get().strip())
        if not destination_dir.is_dir():
            try:
                destination_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                self.update_status(f"● Cannot access folder: {destination_dir.name}", "#ff4d4d")
                return

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
            if total > 0:
                percent = downloaded / total
                self.after(0, self.progress_bar.set, percent)
                self.after(0, self.update_status, f"● Downloading: {percent * 100:.1f}%", "#ffd700")
        elif d.get("status") == "finished":
            self.after(0, self.progress_bar.set, 1.0)
            self.after(0, self.update_status, "● Download complete, converting...", "#ffd700")

    def download_process(self, url: str, format_type: str, quality: str, destination_dir: Path):
        try:
            with tempfile.TemporaryDirectory(prefix="ytdl_") as temp_dir:
                ydl_opts = build_ydl_options(temp_dir, format_type, quality, self.progress_hook)
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                completed = [
                    Path(temp_dir) / f for f in os.listdir(temp_dir)
                    if not f.endswith((".part", ".ytdl")) and (Path(temp_dir) / f).is_file()
                ]

                if not completed:
                    self.after(0, self.update_status, "● Download completed, but no files saved.", "#ff4d4d")
                    return

                for src in completed:
                    dst = resolve_unique_path(destination_dir, src.name)
                    shutil.move(str(src), str(dst))

                self.after(0, self.update_status, f"✔ Done! Saved to {destination_dir.name}", "#00e676")
                self.after(0, self.reset_ui, True)
        except Exception as error:
            cleaned = clean_error_message(str(error))
            log_error(url, cleaned)
            self.after(0, self.update_status, f"✖ Error: {cleaned}", "#ff4d4d")
            self.after(0, self.reset_ui, False)

    def set_inputs_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.download_btn.configure(state=state)
        self.url_input.configure(state=state)
        self.folder_entry.configure(state=state)
        self.browse_btn.configure(state=state)
        self.format_btn.configure(state=state)

    def reset_ui(self, clear_url: bool = False):
        self.set_inputs_enabled(True)
        if clear_url:
            self.url_var.set("")
            self.reset_preview()
        self.progress_bar.set(0)


def main():
    app = YTDLApp()
    app.mainloop()


if __name__ == "__main__":
    main()
