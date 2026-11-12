import tempfile
import unittest
from pathlib import Path

from backend.core import (
    build_ydl_options,
    check_ffmpeg,
    clean_error_message,
    clear_history_file,
    extract_bitrate_number,
    extract_youtube_video_id,
    format_duration,
    get_default_download_dir,
    get_ytdlp_version,
    is_playlist_url,
    load_history,
    resolve_unique_path,
    save_history_entry,
    set_history_file_path,
)
from backend.api import DownloaderAPI


class TestBackend(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.test_hist_file = Path(self.tmp_dir.name) / "test_history.json"
        set_history_file_path(self.test_hist_file)

    def tearDown(self):
        set_history_file_path(None)
        self.tmp_dir.cleanup()

    def test_default_download_dir(self):
        download_dir = get_default_download_dir()
        self.assertIsInstance(download_dir, Path)
        self.assertTrue(download_dir.exists())

    def test_resolve_unique_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            target = resolve_unique_path(tmp_path, "music.mp3")
            self.assertEqual(target.name, "music.mp3")

            (tmp_path / "music.mp3").touch()
            target_dup = resolve_unique_path(tmp_path, "music.mp3")
            self.assertEqual(target_dup.name, "music (1).mp3")

    def test_extract_bitrate(self):
        self.assertEqual(extract_bitrate_number("320 kbps (High)"), "320")
        self.assertEqual(extract_bitrate_number("256 kbps"), "256")
        self.assertEqual(extract_bitrate_number("192 kbps (Standard)"), "192")

    def test_is_playlist_url(self):
        self.assertTrue(is_playlist_url("https://www.youtube.com/playlist?list=PLxyz123"))
        self.assertFalse(is_playlist_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))

    def test_build_ydl_options(self):
        opts = build_ydl_options("C:/fake", "mp3", "320 kbps (High)", None)
        self.assertEqual(opts["format"], "bestaudio/best")
        self.assertTrue(opts["ignoreerrors"])

    def test_history_isolated(self):
        clear_history_file()
        self.assertEqual(load_history(), [])

        save_history_entry("Sample Video", "Video (1080p)", Path("D:/Desktop/sample.mp4"))
        history = load_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["title"], "Sample Video")

        clear_history_file()
        self.assertEqual(load_history(), [])

    def test_get_ytdlp_version(self):
        ver = get_ytdlp_version()
        self.assertIsInstance(ver, str)
        self.assertNotEqual(ver, "unknown")

    def test_api_initial_state(self):
        api = DownloaderAPI()
        state = api.get_initial_state()
        self.assertIn("default_dir", state)
        self.assertIn("ffmpeg_installed", state)
        self.assertIn("history", state)


if __name__ == "__main__":
    unittest.main()
