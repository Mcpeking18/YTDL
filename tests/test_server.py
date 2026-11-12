import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from server import app
from backend.core import set_history_file_path


class TestServer(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.test_hist = Path(self.tmp_dir.name) / "test_hist.json"
        set_history_file_path(self.test_hist)
        self.client = TestClient(app)

    def tearDown(self):
        set_history_file_path(None)
        self.tmp_dir.cleanup()

    def test_serve_frontend(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("YouTube Downloader", res.text)

    def test_serve_static_files(self):
        res_css = self.client.get("/style.css")
        self.assertEqual(res_css.status_code, 200)
        res_js = self.client.get("/app.js")
        self.assertEqual(res_js.status_code, 200)

    def test_api_state(self):
        res = self.client.get("/api/state")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("default_dir", data)
        self.assertIn("ffmpeg_installed", data)
        self.assertIn("presets", data)
        self.assertIn("ytdlp_version", data)

    def test_api_preview_valid_url(self):
        res = self.client.get("/api/preview?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("thumbnail", data)
        self.assertTrue(data["thumbnail"].startswith("http"))

    def test_api_progress(self):
        res = self.client.get("/api/progress")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("state", data)
        self.assertIn("percent", data)

    def test_api_download_validation(self):
        # Missing URL
        res = self.client.post("/api/download", json={"url": "", "destination": "C:/fake"})
        self.assertEqual(res.status_code, 400)

        # Invalid folder
        res2 = self.client.post("/api/download", json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "destination": "C:/NonExistentPath_XYZ123"
        })
        self.assertEqual(res2.status_code, 400)

    def test_api_history(self):
        res_get = self.client.get("/api/history")
        self.assertEqual(res_get.status_code, 200)
        self.assertIsInstance(res_get.json(), list)

        res_del = self.client.delete("/api/history")
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(res_del.json(), [])


if __name__ == "__main__":
    unittest.main()
