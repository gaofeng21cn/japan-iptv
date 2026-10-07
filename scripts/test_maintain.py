import http.server
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import maintain


class Responses(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/denied.m3u8':
            self.send_response(403)
            self.end_headers()
            return
        body = {
            '/master.m3u8': b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=100\ndenied.m3u8\n',
            '/empty.m3u8': b'#EXTM3U\n#EXT-X-TARGETDURATION:5\n',
            '/html.m3u8': b'<html>Just a moment...</html>',
        }[self.path]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class PlaybackFailures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Responses)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def probe(self, path):
        with patch.dict('os.environ', {'IPTV_HTTP_PROXY': ''}):
            return maintain.probe({'id': 'fixture', 'name': 'fixture',
                                   'url': f'http://127.0.0.1:{self.server.server_port}/{path}'})

    def test_master_200_child_403_is_not_playable(self):
        result = self.probe('master.m3u8')
        self.assertFalse(result['ok'])
        self.assertEqual(result['error'], 'HTTP 403')

    def test_200_empty_playlist_is_not_playable(self):
        self.assertFalse(self.probe('empty.m3u8')['ok'])

    def test_200_html_is_not_playable(self):
        self.assertFalse(self.probe('html.m3u8')['ok'])

    def test_missing_decoder_cannot_report_success(self):
        with patch.object(maintain.shutil, 'which', return_value=None):
            with self.assertRaises(ValueError):
                maintain.media_info(b'not a video')

    def test_channel_audit_counts_labels_without_claiming_playback(self):
        body = (
            '#EXTM3U\n'
            '#EXTINF:-1,NHK G\nhttp://example.test/nhkg\n'
            '#EXTINF:-1,NHK E\nhttp://example.test/nhke\n'
            '#EXTINF:-1,TBS\nhttp://example.test/tbs\n'
        ).encode()
        rows, coverage, hosts, risky = maintain.source_coverage(body)
        self.assertEqual(len(rows), 3)
        self.assertEqual(coverage['NHK G'], 1)
        self.assertEqual(coverage['NHK E'], 1)
        self.assertEqual('example.test' in hosts, True)
        self.assertEqual(risky, 0)

    def test_baseline_audit_does_not_label_http_success_as_playback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'sources.json').write_text(json.dumps([{
                'name': 'fixture', 'url': 'http://fixture.test/list.m3u',
                'kind': 'test', 'enabled': True,
            }]))
            with patch.object(maintain, 'ROOT', root), \
                 patch.object(maintain, 'curl_fetch',
                              return_value=(b'#EXTM3U\n#EXTINF:-1,TBS\nhttp://example.test/tbs\n',
                                             'http://fixture.test/list.m3u')):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(maintain.audit('test'), 0)
            report = json.loads((root / 'reports' / 'baseline-audit.json').read_text())
            self.assertTrue(report['sources'][0]['ok'])
            self.assertIn('not playback', report['scope'])


if __name__ == '__main__':
    unittest.main()
