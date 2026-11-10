import ctypes
import os
import sys
from pathlib import Path
import webview

from backend.api import DownloaderAPI

# Set Windows taskbar AppUserModelID for branding
try:
    if sys.platform.startswith("win"):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mcpeking.ytdl.webui.1.0")
except Exception:
    pass


def main():
    api = DownloaderAPI()
    html_path = Path(__file__).parent / "web" / "index.html"
    icon_path = Path(__file__).parent / "assets" / "icon.ico"

    window = webview.create_window(
        title="YouTube Downloader",
        url=str(html_path.resolve().as_uri()),
        js_api=api,
        width=580,
        height=750,
        resizable=True,
        min_size=(460, 600),
        background_color="#0f0f0f",
    )
    api.window = window

    # Start the native webview desktop application
    webview.start(debug=False)


if __name__ == "__main__":
    main()
