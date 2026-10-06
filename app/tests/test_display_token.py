import os
import tempfile
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase

from rest.display_token import ensure_display_token, load_display_token

TOKEN_HDR = {"HTTP_X_NE_DISPLAY_TOKEN": "secret-token"}


class DisplayTokenFileTests(TestCase):
    def test_created_once_with_random_value(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'display_token')
            ensure_display_token(path)
            first = load_display_token(path)
            self.assertGreater(len(first), 30)
            ensure_display_token(path)  # must not overwrite
            self.assertEqual(first, load_display_token(path))
            self.assertEqual(0o640, os.stat(path).st_mode & 0o777)

    def test_missing_file_gives_empty_token(self):
        self.assertEqual('', load_display_token('/nonexistent/display_token'))


@patch("rest.display_token.load_display_token", return_value="secret-token")
@patch("rest.sensors_scan_views.minew_scanner.start_scan", return_value={"ok": True})
@patch("rest.sensors_scan_views.minew_scanner.stop_scan", return_value={})
@patch("rest.sensors_scan_views.minew_scanner.confirm_sensors", return_value={})
class DisplayTokenScanTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_display_with_token_can_start_stop_confirm(self, confirm, stop, start, _tok):
        self.assertEqual(200, self.client.post("/api/sensors-scan/start/", **TOKEN_HDR).status_code)
        self.assertEqual(200, self.client.post("/api/sensors-scan/stop/", **TOKEN_HDR).status_code)
        r = self.client.post("/api/sensors-scan/confirm/", {"all": True}, content_type="application/json", **TOKEN_HDR)
        self.assertEqual(200, r.status_code)
        start.assert_called_once(); stop.assert_called_once(); confirm.assert_called_once()

    def test_wrong_or_missing_token_is_refused(self, confirm, stop, start, _tok):
        for hdr in ({}, {"HTTP_X_NE_DISPLAY_TOKEN": "guess"}):
            r = self.client.post("/api/sensors-scan/start/", **hdr)
            self.assertIn(r.status_code, (401, 403))
        start.assert_not_called()

    def test_no_token_file_fails_closed(self, confirm, stop, start, _tok):
        with patch("rest.display_token.load_display_token", return_value=""):
            r = self.client.post("/api/sensors-scan/start/", **TOKEN_HDR)
        self.assertIn(r.status_code, (401, 403))
        start.assert_not_called()
