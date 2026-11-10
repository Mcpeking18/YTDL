import asyncio
import os
import shutil
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from yt_dlp import YoutubeDL

from backend.core import (
    build_ydl_options,
    check_ffmpeg,
    clean_error_message,
    clear_history_file,
    fetch_metadata_preview,
    get_common_folder_presets,
    get_default_download_dir,
    load_history,
    log_error,
    open_folder_picker,
    open_in_explorer,
    resolve_unique_path,
    save_history_entry,
)

ROOT_DIR = Path(__file__).parent
WEB_DIR = ROOT_DIR / "web"
ASSETS_DIR = ROOT_DIR / "assets"

app = FastAPI(title="YTDL Web Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Download Job State
job_state = {
    "state": "idle",       # "idle", "downloading", "processing", "success", "error"
    "percent": 0.0,
    "speed": "",
    "eta": "",
    "item_index": None,
    "item_total": None,
    "message": "Ready to download",
    "last_file": "",
    "last_dir": "",
    "error": "",
}


class DownloadRequest(BaseModel):
    url: str
    format: str = "mp3"
    quality: str = "320 kbps (High)"
    destination: str = ""


class OpenFolderRequest(BaseModel):
    path: str = ""


@app.get("/api/state")
def get_state():
    """Returns application setup context, presets, and history."""
    return {
        "default_dir": str(get_default_download_dir()),
        "ffmpeg_installed": check_ffmpeg(),
        "presets": get_common_folder_presets(),
        "history": load_history(),
    }


@app.get("/api/preview")
def get_preview(url: str = Query(..., description="YouTube URL")):
    """Extracts metadata and thumbnail for live preview."""
    return fetch_metadata_preview(url)


@app.post("/api/browse")
async def browse_folder(initial_dir: str = Query(default="")):
    """Opens native Windows folder selection dialog."""
    loop = asyncio.get_event_loop()
    selected = await loop.run_in_executor(None, open_folder_picker, initial_dir)
    return {"selected": selected}


def run_download_worker(url: str, format_type: str, quality: str, destination_dir: Path):
    global job_state

    def progress_hook(d: dict):
        global job_state
        if d.get("status") == "downloading":
            downloaded = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            percent = (downloaded / total * 100) if total > 0 else 0
            speed = clean_error_message(d.get("_speed_str") or "")
            eta = clean_error_message(d.get("_eta_str") or "")
            info = d.get("info_dict") or {}

            job_state.update({
                "state": "downloading",
                "percent": round(percent, 1),
                "speed": speed,
                "eta": eta,
                "item_index": info.get("playlist_index"),
                "item_total": info.get("n_entries"),
                "message": f"Downloading: {round(percent, 1)}%",
            })
        elif d.get("status") == "finished":
            job_state.update({
                "state": "processing",
                "percent": 100.0,
                "message": "Merging streams & embedding cover art...",
            })

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
                job_state.update({
                    "state": "error",
                    "error": "Download completed, but no media files were generated.",
                })
                return

            last_file = None
            for src in completed:
                dst = resolve_unique_path(destination_dir, src.name)
                shutil.move(str(src), str(dst))
                last_file = dst

                fmt_label = f"Audio ({quality})" if format_type == "mp3" else f"Video ({quality})"
                save_history_entry(dst.stem, fmt_label, dst)

            job_state.update({
                "state": "success",
                "percent": 100.0,
                "last_file": str(last_file),
                "last_dir": destination_dir.name,
                "message": f"Saved to {destination_dir.name}",
            })

    except Exception as error:
        cleaned = clean_error_message(str(error))
        log_error(url, cleaned)
        job_state.update({
            "state": "error",
            "error": cleaned,
            "message": f"Error: {cleaned}",
        })


@app.post("/api/download")
def start_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    """Starts the download in the background."""
    global job_state

    if job_state["state"] in ("downloading", "processing"):
        return JSONResponse(status_code=400, content={"success": False, "error": "A download is already running."})

    url = req.url.strip()
    if not url:
        return JSONResponse(status_code=400, content={"success": False, "error": "Please provide a valid URL."})

    dest_str = req.destination.strip() or str(get_default_download_dir())
    destination_dir = Path(dest_str)
    if not destination_dir.is_dir():
        return JSONResponse(status_code=400, content={"success": False, "error": "Destination folder does not exist."})

    job_state = {
        "state": "downloading",
        "percent": 0.0,
        "speed": "",
        "eta": "",
        "item_index": None,
        "item_total": None,
        "message": "Starting download...",
        "last_file": "",
        "last_dir": destination_dir.name,
        "error": "",
    }

    fmt_type = "mp3" if "mp3" in req.format.lower() else "mp4"
    background_tasks.add_task(run_download_worker, url, fmt_type, req.quality, destination_dir)
    return {"success": True, "message": "Download started"}


@app.get("/api/progress")
def get_progress():
    """Polls real-time download progress."""
    global job_state
    return job_state


@app.post("/api/open-folder")
def open_folder(req: OpenFolderRequest):
    """Opens Windows Explorer at the target file or directory."""
    target = req.path.strip() or job_state.get("last_file")
    if target:
        open_in_explorer(Path(target))
        return {"success": True}
    return {"success": False, "error": "No file path specified"}


@app.get("/api/history")
def get_history():
    """Returns the history of downloads."""
    return load_history()


@app.delete("/api/history")
def clear_history():
    """Clears history file."""
    clear_history_file()
    return []


# Mount assets folder
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

# Serve frontend
@app.get("/")
def serve_index():
    return FileResponse(str(WEB_DIR / "index.html"))

@app.get("/style.css")
def serve_css():
    return FileResponse(str(WEB_DIR / "style.css"))

@app.get("/app.js")
def serve_js():
    return FileResponse(str(WEB_DIR / "app.js"))


def start_server(host="127.0.0.1", port=8000, open_browser=True):
    """Starts the FastAPI Uvicorn live server and opens default browser."""
    url = f"http://{host}:{port}"
    print(f"\n🚀 YTDL Live Server running at: {url}")
    print(f"👉 Press Ctrl+C to stop the server.\n")

    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    start_server()
