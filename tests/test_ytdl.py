import os
import tempfile
import unittest
from pathlib import Path

from ytdl import (
    YTDLApp,
    build_ydl_options,
    check_ffmpeg,
    clean_error_message,
    clear_history_file,
    create_placeholder_image,
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


class TestYTDL(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.test_hist = Path(self.tmp_dir.name) / "test_hist.json"
        set_history_file_path(self.test_hist)

    def tearDown(self):
        set_history_file_path(None)
        self.tmp_dir.cleanup()
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

    def test_check_ffmpeg(self):
        # Checks function returns a boolean without throwing
        res = check_ffmpeg()
        self.assertIsInstance(res, bool)

    def test_extract_bitrate_number(self):
        self.assertEqual(extract_bitrate_number("320 kbps (High)"), "320")
        self.assertEqual(extract_bitrate_number("256 kbps"), "256")
        self.assertEqual(extract_bitrate_number("192 kbps (Standard)"), "192")
        self.assertEqual(extract_bitrate_number("128 kbps (Compact)"), "128")
        self.assertEqual(extract_bitrate_number("unknown"), "192")

    def test_is_playlist_url(self):
        self.assertTrue(is_playlist_url("https://www.youtube.com/playlist?list=PL1234567890"))
        self.assertTrue(is_playlist_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL1234567890"))
        self.assertFalse(is_playlist_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))

    def test_build_ydl_options_mp3_bitrate(self):
        opts = build_ydl_options("C:/temp_test", "mp3", "320 kbps (High)", None)
        self.assertEqual(opts["format"], "bestaudio/best")
        self.assertTrue(opts["no_color"])
        self.assertEqual(opts["retries"], 3)
        self.assertTrue(opts["writethumbnail"])
        self.assertTrue(opts["ignoreerrors"])

        audio_pp = [p for p in opts["postprocessors"] if p.get("key") == "FFmpegExtractAudio"][0]
        self.assertEqual(audio_pp["preferredquality"], "320")

    def test_build_ydl_options_mp4_best(self):
        opts = build_ydl_options("C:/temp_test", "mp4", "Best Available", None)
        self.assertEqual(opts["format"], "bestvideo+bestaudio/best")
        self.assertEqual(opts["merge_output_format"], "mp4")
        self.assertTrue(opts["writethumbnail"])
        pp_keys = [p["key"] for p in opts["postprocessors"]]
        self.assertIn("EmbedThumbnail", pp_keys)

    def test_build_ydl_options_mp4_resolution(self):
        opts = build_ydl_options("C:/temp_test", "mp4", "720p", None)
        self.assertIn("height<=720", opts["format"])
        self.assertEqual(opts["merge_output_format"], "mp4")
        self.assertTrue(opts["writethumbnail"])

    def test_clean_error_message(self):
        raw_error = "\x1b[0;31mERROR:\x1b[0m [generic] 'fdsff' is not a valid URL"
        cleaned = clean_error_message(raw_error)
        self.assertEqual(cleaned, "[generic] 'fdsff' is not a valid URL")

    def test_extract_youtube_video_id(self):
        self.assertEqual(
            extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )
        self.assertEqual(
            extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )
        self.assertEqual(
            extract_youtube_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )
        self.assertIsNone(extract_youtube_video_id("https://vimeo.com/1234567"))

    def test_format_duration(self):
        self.assertEqual(format_duration(65), "1:05")
        self.assertEqual(format_duration(3665), "1:01:05")
        self.assertEqual(format_duration(0), "")
        self.assertEqual(format_duration(None), "")

    def test_create_placeholder_image(self):
        img = create_placeholder_image(160, 90)
        self.assertEqual(img.size, (160, 90))

    def test_history_operations(self):
        clear_history_file()
        self.assertEqual(load_history(), [])

        save_history_entry("Test Track", "Audio (320 kbps)", Path("D:/Desktop/Test.mp3"))
        hist = load_history()
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["title"], "Test Track")
        self.assertEqual(hist[0]["format"], "Audio (320 kbps)")

        clear_history_file()
        self.assertEqual(load_history(), [])

    def test_get_ytdlp_version(self):
        ver = get_ytdlp_version()
        self.assertIsInstance(ver, str)
        self.assertNotEqual(ver, "unknown")

    def test_app_lifecycle(self):
        app = YTDLApp()
        self.assertEqual(app.format_var.get(), "Audio (MP3)")
        self.assertIn("320", app.quality_var.get())

        # Switch to Video (MP4)
        app.format_var.set("Video (MP4)")
        app.toggle_quality()
        self.assertEqual(app.quality_var.get(), "Best Available")

        # Switch back to Audio (MP3)
        app.format_var.set("Audio (MP3)")
        app.toggle_quality()
        self.assertEqual(app.quality_var.get(), "320 kbps (High)")

        # Verify initial preview state
        self.assertEqual(app.preview_title.cget("text"), "No video loaded")

        if app._preview_timer:
            app.after_cancel(app._preview_timer)
        app.withdraw()
        app.update()
        app.destroy()

    def test_invalid_folder_does_not_create_directory(self):
        app = YTDLApp()
        fake_path = Path("C:/NonExistentTestFolder_12345")
        self.assertFalse(fake_path.exists())
        app.url_var.set("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        app.output_dir_var.set(str(fake_path))
        app.start_download_thread()
        self.assertIn("Folder does not exist", app.status_label.cget("text"))
        self.assertFalse(fake_path.exists())
        if app._preview_timer:
            app.after_cancel(app._preview_timer)
        app.withdraw()
        app.update()
        app.destroy()


if __name__ == "__main__":
    unittest.main()
