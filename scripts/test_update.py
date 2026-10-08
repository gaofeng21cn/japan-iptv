import copy
import http.server
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import maintain
import update


def row(url, ok=True, incumbent=False, height=540, channel="TBS.jp"):
    return {"id": channel, "name": "TBS", "url": url, "source": "https://source.test/list.m3u",
            "incumbent": incumbent, "ok": ok,
            "checks": [{"ok": ok, "transport": "hls", "video": {
                "width": 960, "height": height, "r_frame_rate": "25/1"}}]}


class Selection(unittest.TestCase):
    def setUp(self):
        self.policy = {"channels": [{"id": "TBS.jp", "name": "TBS", "aliases": ["TBS"]},
                                    {"id": "NHK.jp", "name": "NHK G", "aliases": ["NHK G"]}],
                       "remove_after_failures": 2, "confirmations": 2, "attempts": 3}
        self.data = {"channels": [{"id": "TBS.jp", "name": "TBS", "group": "日本地上波",
                                  "url": "https://old.test/tbs", "transport": "hls"}],
                     "candidates": []}

    def test_replacement_is_automatic_and_same_upstream_is_not_backup(self):
        candidates = [row("https://old.test/tbs", False, True),
                      row("https://tbs.mov3.co/live"), row("https://tbs5.mov3.co/live"),
                      row("https://different.test/live")]
        selected, _ = update.select(self.data, candidates, {}, self.policy)
        self.assertEqual(len(selected["channels"]), 2)
        self.assertNotIn("https://old.test/tbs", [c["url"] for c in selected["channels"]])
        self.assertEqual(selected["channels"][1]["group"], "备用")

    def test_second_failed_run_removes_channel_and_recovery_resets_counter(self):
        candidates = [row("https://old.test/tbs", False, True),
                      row("https://nhk.test/live", channel="NHK.jp")]
        selected, state = update.select(self.data, candidates, {}, self.policy)
        self.assertEqual(len(selected["channels"]), 2)
        removed, _ = update.select(selected, candidates, state, self.policy)
        self.assertEqual(removed["missing"], ["TBS"])
        candidates[0] = row("https://old.test/tbs", True, True)
        recovered, state = update.select(selected, candidates, state, self.policy)
        self.assertEqual(state, {"failures": {}})
        self.assertEqual(recovered["missing"], [])

    def test_all_failed_preserves_input(self):
        before = copy.deepcopy(self.data)
        with self.assertRaises(ValueError):
            update.select(self.data, [row("https://old.test/tbs", False, True)], {}, self.policy)
        self.assertEqual(self.data, before)

    def test_two_successes_must_be_consecutive(self):
        sequence = [{"ok": True}, {"ok": False}, {"ok": True}]
        with patch.object(update, "probe_auto", side_effect=sequence), redirect_stdout(io.StringIO()):
            self.assertFalse(update.confirm(row("https://test.test/live"), self.policy)["ok"])

    def test_news_and_subchannels_are_not_main_channel(self):
        targets = [{"id": "NTV.jp", "aliases": ["NTV", "Nippon TV"]},
                   {"id": "NHK.jp", "aliases": ["NHK G"]}]
        self.assertIsNone(update.identify({"name": "NTV News24"}, targets))
        self.assertIsNone(update.identify({"name": "NHK G (Sub Ch.)"}, targets))
        self.assertEqual(update.identify({"name": "NTV (1080p)"}, targets)["id"], "NTV.jp")

    def test_missing_decode_frame_is_not_success(self):
        info = {"streams": [{"codec_type": "video", "width": 960, "height": 540}]}
        probe = subprocess.CompletedProcess([], 0, stdout=json.dumps(info).encode())
        decoder = subprocess.CompletedProcess([], 0, stdout=b"# framecrc header only\n")
        with patch.object(maintain.subprocess, "run", side_effect=[probe, decoder]), \
             patch.object(maintain.shutil, "which", return_value="/fixture/ffmpeg"):
            with self.assertRaisesRegex(ValueError, "无法解码"):
                maintain.media_info(b"fixture")

    def test_live_ts_startup_is_not_mistaken_for_slow_download(self):
        result = {"ok": True, "sample_seconds": 4.0, "read_seconds": 1.9,
                  "video": {"duration": 1.8}}
        with patch.object(maintain, "probe_ts", return_value=result):
            self.assertTrue(update.probe_auto({"transport": "mpegts"})["ok"])
        result = {"ok": True, "sample_seconds": 8.0, "read_seconds": 6.0,
                  "video": {"duration": 1.8}}
        with patch.object(maintain, "probe_ts", return_value=result):
            self.assertFalse(update.probe_auto({"transport": "mpegts"})["ok"])


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise unittest.SkipTest("需要 FFmpeg 进行真实视频解码测试")
        cls.directory = tempfile.TemporaryDirectory()
        sample = Path(cls.directory.name) / "sample.ts"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                        "testsrc=size=320x240:rate=25", "-t", "3", "-threads", "1",
                        "-c:v", "mpeg2video", "-f", "mpegts", str(sample)], check=True)
        cls.video = sample.read_bytes()

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/list.m3u":
                    body = (f'#EXTM3U\n#EXTINF:-1,TBS\nhttp://127.0.0.1:{self.server.server_port}/live.ts\n'
                            f'#EXTINF:-1,Fuji TV\nhttp://127.0.0.1:{self.server.server_port}/master.m3u8\n'
                            f'#EXTINF:-1,NHK G\nhttp://127.0.0.1:{self.server.server_port}/html\n').encode()
                elif self.path == "/master.m3u8":
                    body = b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=200000\nmedia.m3u8\n'
                elif self.path == "/media.m3u8":
                    body = b'#EXTM3U\n#EXT-X-TARGETDURATION:3\n#EXTINF:3,\nlive.ts\n'
                elif self.path == "/live.ts":
                    body = cls.video
                elif self.path == "/html":
                    body = b"<html>Not a stream</html>"
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.directory.cleanup()

    def test_real_video_to_generated_subscription_and_idempotency(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("automation.json",):
                shutil.copy(update.ROOT / name, root / name)
            source = f"http://127.0.0.1:{self.server.server_port}/list.m3u"
            (root / "sources.json").write_text(json.dumps([
                {"name": "fixture", "url": source, "enabled": True},
                {"name": "disabled", "url": "http://127.0.0.1:1/list", "enabled": False}]))
            (root / "channels.json").write_text(json.dumps({"channels": [], "candidates": []}))
            (root / "README.md").write_text("Before\n<!-- CHANNELS:START -->\n<!-- CHANNELS:END -->\nAfter\n")
            with patch.object(update, "ROOT", root), patch.object(maintain, "ROOT", root), \
                 patch.dict("os.environ", {"IPTV_HTTP_PROXY": ""}), redirect_stdout(io.StringIO()):
                dry = update.update("fixture", dry_run=True)
                self.assertEqual(dry["playable"], 2)
                self.assertFalse((root / "playlist.m3u").exists())
                update.update("fixture")
                paths = [root / n for n in ("playlist.m3u", "channels.json", "README.md", "automation-state.json")]
                snapshot = [p.read_bytes() for p in paths]
                update.update("fixture")
                self.assertEqual(snapshot, [p.read_bytes() for p in paths])
                maintain.build(check=True)
            result = json.loads((root / "channels.json").read_text())
            self.assertEqual([c["name"] for c in result["channels"]], ["TBS", "フジテレビ"])
            self.assertEqual(result["channels"][0]["transport"], "mpegts")
            self.assertEqual(result["channels"][1]["transport"], "hls")
            self.assertEqual(result["channels"][0]["resolution"], "320×240")
            self.assertIn("After", (root / "README.md").read_text())
            report = json.loads((root / "reports/update.json").read_text())
            self.assertEqual(len(report["sources"]), 1)


if __name__ == "__main__":
    unittest.main()
