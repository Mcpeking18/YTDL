import os
import re
import shutil
import tempfile
import threading
import time
from pathlib import Path
from tkinter import filedialog

# Modern UI library based on Tkinter
import customtkinter as ctk

# Core YouTube downloader library
from yt_dlp import YoutubeDL


# =====================================================================
# HELPER FUNCTIONS (Path resolution, safe naming, yt-dlp options)
# =====================================================================

def get_default_download_dir() -> Path:
    """
    Finds a sensible default download directory on the user's computer.
    Checks Desktop first, falls back to Downloads, or user home folder.
    """
    desktop = Path.home() / "Desktop"
    if desktop.is_dir():
        return desktop
    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        return downloads
    return Path.home()


def resolve_unique_path(directory: Path, filename: str) -> Path:
    """
    Prevents overwriting existing files by appending (1), (2), etc.
    Example: 'song.mp3' -> 'song (1).mp3' if 'song.mp3' already exists.
    """
    destination = directory / filename
    if not destination.exists():
        return destination

    stem = destination.stem    # Filename without extension (e.g., 'song')
    suffix = destination.suffix  # File extension (e.g., '.mp3')
    counter = 1

    # Keep incrementing counter until an unused filename is found
    while True:
        candidate = directory / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def build_ydl_options(
    temp_dir: str,
    format_type: str,
    quality: str,
    progress_hook,
) -> dict:
    """
    Builds the configuration dictionary passed to yt-dlp.
    Configures output templates, audio/video formats, and retries.
    """
    options = {
        # Save output in temporary directory with the video title as filename
        "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
        # Callback function that reports download progress
        "progress_hooks": [progress_hook],
        # Keep terminal quiet and clean
        "quiet": True,
        "no_warnings": True,
        "no_color": True,            # Prevents raw terminal color codes in output
        "windowsfilenames": True,     # Sanitizes characters not allowed in Windows filenames
        "retries": 3,                 # Automatically retry network drops 3 times
        "fragment_retries": 3,
    }

    # Audio Download: Extract audio track and convert to MP3 using FFmpeg
    if format_type == "mp3":
        options.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",  # 192 kbps bitrate
            }],
        })
    # Video Download: Merge best video and best audio into an MP4 container
    else:
        if quality == "best":
            format_str = "bestvideo+bestaudio/best"
        else:
            # Strip 'p' (e.g., '1080p' -> '1080') for height filter
            height = quality.replace("p", "")
            format_str = (
                f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
            )

        options.update({
            "format": format_str,
            "merge_output_format": "mp4",  # Ensure the merged file is always an MP4
        })

    return options


def clean_error_message(raw_error: str) -> str:
    """
    Strips raw terminal ANSI color codes and cleans up error messages
    so they display nicely in the GUI and log files.
    """
    cleaned = re.sub(r"\x1b\[[0-9;]*m", "", raw_error).strip()
    if cleaned.startswith("ERROR:"):
        cleaned = cleaned[6:].strip()
    return cleaned


def log_error(url: str, error_message: str) -> None:
    """
    Appends error details with a timestamp to 'errors.txt' for debugging.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open("errors.txt", "a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] URL: {url} | Error: {error_message}\n")


# =====================================================================
# MAIN GUI APPLICATION CLASS
# =====================================================================

class YTDLApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("YTDL - YouTube Downloader")
        self.geometry("520x520")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --- UI ELEMENTS ---

        # 1. Main Title Header
        self.label_title = ctk.CTkLabel(
            self, text="YouTube Downloader", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.label_title.pack(pady=(20, 10))

        # 2. URL Input Entry
        self.url_input = ctk.CTkEntry(
            self, placeholder_text="Paste your YouTube URL here...", width=420
        )
        self.url_input.pack(pady=8)

        # 3. Output Folder Selection (Path entry + Browse button)
        self.output_dir_var = ctk.StringVar(value=str(get_default_download_dir()))
        self.folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.folder_frame.pack(pady=8)

        self.folder_entry = ctk.CTkEntry(
            self.folder_frame, textvariable=self.output_dir_var, width=320
        )
        self.folder_entry.pack(side="left", padx=(0, 10))

        self.browse_btn = ctk.CTkButton(
            self.folder_frame, text="Browse", width=90, command=self.browse_folder
        )
        self.browse_btn.pack(side="left")

        # 4. Format Selection Radio Buttons (Audio MP3 vs Video MP4)
        self.format_var = ctk.StringVar(value="mp3")
        self.radio_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.radio_frame.pack(pady=8)

        self.radio_mp3 = ctk.CTkRadioButton(
            self.radio_frame,
            text="Audio (MP3)",
            variable=self.format_var,
            value="mp3",
            command=self.toggle_quality,
        )
        self.radio_mp3.pack(side="left", padx=12)

        self.radio_mp4 = ctk.CTkRadioButton(
            self.radio_frame,
            text="Video (MP4)",
            variable=self.format_var,
            value="mp4",
            command=self.toggle_quality,
        )
        self.radio_mp4.pack(side="left", padx=12)

        # 5. Video Quality Dropdown Menu (Disabled by default when Audio is selected)
        self.quality_var = ctk.StringVar(value="best")
        self.quality_dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.quality_var,
            values=["best", "1080p", "720p", "480p", "360p"],
            width=200,
        )
        self.quality_dropdown.pack(pady=(0, 10))
        self.quality_dropdown.configure(state="disabled")

        # 6. Action Buttons (Download & Exit)
        self.download_btn = ctk.CTkButton(
            self,
            text="Download",
            font=ctk.CTkFont(weight="bold"),
            command=self.start_download_thread,
            width=200,
        )
        self.download_btn.pack(pady=10)

        self.exit_btn = ctk.CTkButton(
            self,
            text="Exit",
            fg_color="transparent",
            border_width=1,
            command=self.destroy,
            width=200,
        )
        self.exit_btn.pack(pady=(0, 16))

        # 7. Live Download Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self, width=420)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 10))

        # 8. Status Console Label
        self.status_label = ctk.CTkLabel(
            self, text="Ready.", text_color="gray", wraplength=460
        )
        self.status_label.pack(pady=(0, 20))

    # --- UI INTERACTION METHODS ---

    def browse_folder(self):
        """Opens a folder dialog so user can choose where to save files."""
        selected_dir = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if selected_dir:
            self.output_dir_var.set(selected_dir)

    def toggle_quality(self):
        """Enables the resolution dropdown only when Video (MP4) is chosen."""
        if self.format_var.get() == "mp4":
            self.quality_dropdown.configure(state="normal")
        else:
            self.quality_dropdown.configure(state="disabled")

    def update_status(self, text: str, color: str = "white"):
        """Updates the status label text and text color."""
        self.status_label.configure(text=text, text_color=color)

    def start_download_thread(self):
        """
        Validates user input, disables buttons to avoid double-clicks,
        and launches the download in a background worker thread.
        (Using a thread prevents the GUI window from freezing/crashing!)
        """
        url = self.url_input.get().strip()
        if not url:
            self.update_status("Please enter a valid URL.", "red")
            return

        destination_dir = Path(self.output_dir_var.get().strip())
        if not destination_dir.is_dir():
            try:
                destination_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                self.update_status(f"Cannot access output directory: {destination_dir}", "red")
                return

        # Disable input controls while download is active
        self.set_inputs_enabled(False)
        self.progress_bar.set(0)
        self.update_status("Starting download...", "yellow")

        # Start download process in a separate daemon thread
        threading.Thread(
            target=self.download_process,
            args=(url, self.format_var.get(), self.quality_var.get(), destination_dir),
            daemon=True,
        ).start()

    def progress_hook(self, d: dict):
        """
        Called repeatedly by yt-dlp with download metrics.
        Uses self.after(0, ...) to schedule GUI updates safely on the main Tkinter thread.
        """
        if d.get("status") == "downloading":
            downloaded = d.get("downloaded_bytes") or 0
            # Total bytes can be in 'total_bytes' or estimated in 'total_bytes_estimate'
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            if total > 0:
                percent = downloaded / total
                # Update progress bar (0.0 to 1.0)
                self.after(0, self.progress_bar.set, percent)
                # Update percentage string
                self.after(
                    0,
                    self.update_status,
                    f"Downloading: {percent * 100:.1f}%",
                    "yellow",
                )
        elif d.get("status") == "finished":
            self.after(0, self.progress_bar.set, 1.0)
            self.after(0, self.update_status, "Download complete, processing...", "yellow")

    def download_process(
        self,
        url: str,
        format_type: str,
        quality: str,
        destination_dir: Path,
    ):
        """
        Runs in the background thread:
        1. Creates an isolated temporary directory.
        2. Downloads and converts audio/video inside temp.
        3. Moves completed files to user's destination with duplicate protection.
        4. Cleans up temp directory automatically when finished.
        """
        try:
            # Isolated temp directory automatically deletes itself when block finishes
            with tempfile.TemporaryDirectory(prefix="ytdl_") as temp_dir:
                ydl_opts = build_ydl_options(
                    temp_dir,
                    format_type,
                    quality,
                    self.progress_hook,
                )

                # Execute yt-dlp download
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                # Find finished downloaded files (ignoring incomplete .part or .ytdl files)
                completed_files = [
                    Path(temp_dir) / file_name
                    for file_name in os.listdir(temp_dir)
                    if not file_name.endswith((".part", ".ytdl"))
                    and (Path(temp_dir) / file_name).is_file()
                ]

                if not completed_files:
                    self.after(
                        0,
                        self.update_status,
                        "Download completed, but no output files were found.",
                        "red",
                    )
                    return

                # Move each finished file into destination folder
                for source_file in completed_files:
                    target_file = resolve_unique_path(destination_dir, source_file.name)
                    shutil.move(str(source_file), str(target_file))

                # Update UI on success
                self.after(
                    0,
                    self.update_status,
                    f"✅ Done! Saved to {destination_dir.name}",
                    "green",
                )
                self.after(0, self.reset_ui, True)
                return

        except Exception as error:
            # Handle download or network errors cleanly
            cleaned_message = clean_error_message(str(error))
            log_error(url, cleaned_message)
            self.after(0, self.update_status, f"Failed: {cleaned_message}", "red")
            self.after(0, self.reset_ui, False)

    def set_inputs_enabled(self, enabled: bool):
        """Enables or disables interactive inputs during download."""
        state = "normal" if enabled else "disabled"
        self.download_btn.configure(state=state)
        self.url_input.configure(state=state)
        self.folder_entry.configure(state=state)
        self.browse_btn.configure(state=state)

    def reset_ui(self, clear_url: bool = False):
        """Restores UI inputs and resets progress bar back to ready state."""
        self.set_inputs_enabled(True)
        if clear_url:
            self.url_input.delete(0, "end")
        self.progress_bar.set(0)


# =====================================================================
# SCRIPT ENTRY POINT
# =====================================================================

def main():
    """Main function to instantiate and run the GUI application."""
    app = YTDLApp()
    app.mainloop()


if __name__ == "__main__":
    main()
