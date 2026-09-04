import os
import shutil
import threading
import time
import customtkinter as ctk
from yt_dlp import YoutubeDL as YTDL

# --- CONFIGURATION ---
TEMP_PATH = r'C:/Temp'
OUTPUT_PATH = r'D:/Desktop'

class YTDLApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YTDL - YouTube Downloader")
        self.geometry("500x470")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # --- UI ELEMENTS ---
        self.label_title = ctk.CTkLabel(self, text="YouTube Downloader", font=ctk.CTkFont(size=24, weight="bold"))
        self.label_title.pack(pady=(20, 10))

        self.url_input = ctk.CTkEntry(self, placeholder_text="Paste your YouTube URL here...", width=400)
        self.url_input.pack(pady=10)

        # Format Selection
        self.format_var = ctk.StringVar(value="mp3")
        self.radio_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.radio_frame.pack(pady=10)
        
        self.radio_mp3 = ctk.CTkRadioButton(self.radio_frame, text="Audio (MP3)", variable=self.format_var, value="mp3", command=self.toggle_quality)
        self.radio_mp3.pack(side="left", padx=10)
        
        self.radio_mp4 = ctk.CTkRadioButton(self.radio_frame, text="Video (MP4)", variable=self.format_var, value="mp4", command=self.toggle_quality)
        self.radio_mp4.pack(side="left", padx=10)

        # Quality Selection (only for video)
        self.quality_var = ctk.StringVar(value="best")
        self.quality_dropdown = ctk.CTkOptionMenu(
            self, variable=self.quality_var, 
            values=["best", "1080p", "720p", "480p", "360p"]
        )
        self.quality_dropdown.pack(pady=(0, 10))
        self.quality_dropdown.configure(state="disabled") # Disabled by default

        # Download Button
        self.download_btn = ctk.CTkButton(self, text="Download", font=ctk.CTkFont(weight="bold"), command=self.start_download_thread)
        self.download_btn.pack(pady=10)
        
        # Exit Button
        self.exit_btn = ctk.CTkButton(self, text="Exit", fg_color="transparent", border_width=1, command=self.destroy)
        self.exit_btn.pack(pady=(0, 20))

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 10))

        # Status Console
        self.status_label = ctk.CTkLabel(self, text="Ready.", text_color="gray", wraplength=450)
        self.status_label.pack(pady=(0, 20))

    def toggle_quality(self):
        if self.format_var.get() == "mp4":
            self.quality_dropdown.configure(state="normal")
        else:
            self.quality_dropdown.configure(state="disabled")

    def update_status(self, text, color="white"):
        self.status_label.configure(text=text, text_color=color)

    def start_download_thread(self):
        url = self.url_input.get().strip()
        if not url:
            self.update_status("Please enter a valid URL.", "red")
            return
            
        # Disable inputs while downloading
        self.download_btn.configure(state="disabled")
        self.url_input.configure(state="disabled")
        self.progress_bar.set(0)
        self.update_status("Starting download...", "yellow")

        # Start background thread
        threading.Thread(target=self.download_process, args=(url, self.format_var.get()), daemon=True).start()

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                # yt-dlp returns downloaded_bytes and total_bytes or total_bytes_estimate
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', d.get('total_bytes_estimate', 0))
                if total > 0:
                    percent = downloaded / total
                    # Update progress bar safely from thread using after
                    self.after(0, self.progress_bar.set, percent)
                    percent_str = f"{percent*100:.1f}%"
                    self.after(0, self.update_status, f"Downloading: {percent_str}", "yellow")
            except:
                pass
        elif d['status'] == 'finished':
            self.after(0, self.progress_bar.set, 1.0)
            self.after(0, self.update_status, "Download finished, processing...", "yellow")

    def get_safe_filename(self, directory, filename):
        """Prevents overwriting by adding (1), (2), etc."""
        base, ext = os.path.splitext(filename)
        counter = 1
        new_filename = filename
        while os.path.exists(os.path.join(directory, new_filename)):
            new_filename = f"{base} ({counter}){ext}"
            counter += 1
        return new_filename

    def download_process(self, url, format_type):
        os.makedirs(TEMP_PATH, exist_ok=True)
        
        # Check if D:/Desktop is accessible
        if not os.path.exists(OUTPUT_PATH):
            try:
                os.makedirs(OUTPUT_PATH, exist_ok=True)
            except Exception:
                self.after(0, self.update_status, f"Error: Cannot access {OUTPUT_PATH}", "red")
                self.after(0, self.reset_ui)
                return

        ydl_opts = {
            'outtmpl': os.path.join(TEMP_PATH, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'no_warnings': True,
        }

        if format_type == "mp3":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'
                }]
            })
        else:
            quality = self.quality_var.get()
            if quality == "best":
                format_str = 'bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/mp4'
            else:
                h = quality.replace('p', '')
                format_str = f'bestvideo[height<={h}]+bestaudio/best'
                
            ydl_opts.update({
                'outtmpl': os.path.join(TEMP_PATH, '%(title)s %(resolution)s.%(ext)s'),
                'format': format_str,
                'merge_output_format': 'mp4',
            })

        max_retries = 3
        success = False
        error_msg = ""

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    self.after(0, self.update_status, f"Retrying... (Attempt {attempt+1}/{max_retries})", "yellow")
                    time.sleep(2) # wait a bit before retry
                
                with YTDL(ydl_opts) as ydl:
                    ydl.download([url])
                success = True
                break # success, break retry loop
            except Exception as e:
                error_msg = str(e)
                # Keep trying
        
        if not success:
            self.after(0, self.update_status, f"Failed: {error_msg}", "red")
            self.after(0, self.reset_ui)
            # Log error
            with open("errors.txt", "a", encoding="utf-8") as f:
                f.write(f"Error on {url}: {error_msg}\n")
            return

        # Move files
        moved_count = 0
        try:
            for file in os.listdir(TEMP_PATH):
                # Ignore partial yt-dlp files
                if file.endswith('.part') or file.endswith('.ytdl'):
                    continue
                    
                source = os.path.join(TEMP_PATH, file)
                if os.path.isfile(source):
                    # Get safe filename to prevent overwriting
                    safe_filename = self.get_safe_filename(OUTPUT_PATH, file)
                    destination = os.path.join(OUTPUT_PATH, safe_filename)
                    
                    shutil.move(source, destination)
                    moved_count += 1
            
            if moved_count > 0:
                self.after(0, self.update_status, f"✅ Done! Moved to Desktop", "green")
            else:
                self.after(0, self.update_status, "✅ Done! (No new files to move)", "green")
        except Exception as e:
            self.after(0, self.update_status, f"Error moving files: {str(e)}", "red")
            
        self.after(0, self.reset_ui, True)

    def reset_ui(self, clear_url=False):
        self.download_btn.configure(state="normal")
        self.url_input.configure(state="normal")
        if clear_url:
            self.url_input.delete(0, 'end')
        self.progress_bar.set(0)

if __name__ == "__main__":
    app = YTDLApp()
    app.mainloop()