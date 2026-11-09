import os
import tempfile
import unittest
from pathlib import Path

from ytdl import (
    YTDLApp,
    build_ydl_options,
    clean_error_message,
    get_default_download_dir,
    resolve_unique_path,
)


class TestYTDL(unittest.TestCase):
    def test_default_download_dir_exists(self):
        download_dir = get_default_download_dir()
        self.assertIsInstance(download_dir, Path)
        self.assertTrue(download_dir.exists())

    def test_resolve_unique_path_non_existing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            target = resolve_unique_path(tmp_path, "sample.mp4")
            self.assertEqual(target.name, "sample.mp4")

    def test_resolve_unique_path_existing_collision(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "sample.mp4").touch()
            target1 = resolve_unique_path(tmp_path, "sample.mp4")
            self.assertEqual(target1.name, "sample (1).mp4")

            (tmp_path / "sample (1).mp4").touch()
            target2 = resolve_unique_path(tmp_path, "sample.mp4")
            self.assertEqual(target2.name, "sample (2).mp4")

    def test_build_ydl_options_mp3(self):
        opts = build_ydl_options("C:/temp_test", "mp3", "best", None)
        self.assertEqual(opts["format"], "bestaudio/best")
        self.assertTrue(opts["no_color"])
        self.assertEqual(opts["retries"], 3)
        self.assertEqual(opts["postprocessors"][0]["preferredcodec"], "mp3")

    def test_build_ydl_options_mp4_best(self):
        opts = build_ydl_options("C:/temp_test", "mp4", "best", None)
        self.assertEqual(opts["format"], "bestvideo+bestaudio/best")
        self.assertEqual(opts["merge_output_format"], "mp4")

    def test_build_ydl_options_mp4_resolution(self):
        opts = build_ydl_options("C:/temp_test", "mp4", "720p", None)
        self.assertIn("height<=720", opts["format"])
        self.assertEqual(opts["merge_output_format"], "mp4")

    def test_clean_error_message(self):
        raw_error = "\x1b[0;31mERROR:\x1b[0m [generic] 'fdsff' is not a valid URL"
        cleaned = clean_error_message(raw_error)
        self.assertEqual(cleaned, "[generic] 'fdsff' is not a valid URL")

    def test_progress_calculation(self):
        # Emulate yt-dlp dictionary with total_bytes = None
        d = {
            "status": "downloading",
            "downloaded_bytes": 500,
            "total_bytes": None,
            "total_bytes_estimate": 1000,
        }
        downloaded = d.get("downloaded_bytes") or 0
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        self.assertEqual(total, 1000)
        self.assertEqual(downloaded / total, 0.5)

    def test_app_lifecycle(self):
        app = YTDLApp()
        self.assertEqual(app.format_var.get(), "mp3")
        self.assertEqual(app.quality_dropdown.cget("state"), "disabled")

        # Switch to MP4
        app.format_var.set("mp4")
        app.toggle_quality()
        self.assertEqual(app.quality_dropdown.cget("state"), "normal")

        # Switch back to MP3
        app.format_var.set("mp3")
        app.toggle_quality()
        self.assertEqual(app.quality_dropdown.cget("state"), "disabled")

        app.withdraw()
        app.update()
        app.destroy()


if __name__ == "__main__":
    unittest.main()

