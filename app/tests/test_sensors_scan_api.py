from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase

XHR = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class SensorsScanApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("scan", password="x")
        # Like a browser: the default test client skips CSRF checks, which hid this bug
        self.client = Client(enforce_csrf_checks=True)

    @patch("rest.sensors_scan_views.minew_scanner.start_scan", return_value={"ok": True})
    def test_logged_in_page_can_start_a_scan_without_a_csrf_token(self, start):
        # This is the request sensors.js makes; it used to fail with
        # "CSRF Failed: CSRF cookie not set."
        self.client.force_login(self.user)
        r = self.client.post("/api/sensors-scan/start/", **XHR)
        self.assertEqual(200, r.status_code, r.content)
        start.assert_called_once()

    @patch("rest.sensors_scan_views.minew_scanner.start_scan", return_value={"ok": True})
    def test_write_needs_the_ajax_header(self, start):
        self.client.force_login(self.user)
        r = self.client.post("/api/sensors-scan/start/")
        self.assertEqual(403, r.status_code)
        start.assert_not_called()

    @patch("rest.sensors_scan_views.minew_scanner.start_scan", return_value={"ok": True})
    @patch("rest.sensors_scan_views.minew_scanner.stop_scan", return_value={})
    @patch("rest.sensors_scan_views.minew_scanner.confirm_sensors", return_value={})
    def test_anonymous_cannot_change_anything(self, confirm, stop, start):
        for path, body in (("start", None), ("stop", None), ("confirm", {"all": True})):
            r = self.client.post(f"/api/sensors-scan/{path}/", body, content_type="application/json", **XHR)
            self.assertIn(r.status_code, (401, 403), path)
        start.assert_not_called(); stop.assert_not_called(); confirm.assert_not_called()

    @patch("rest.sensors_scan_views.minew_scanner.get_live_readings", return_value={"sensors": []})
    @patch("rest.sensors_scan_views.minew_scanner.get_scan_status", return_value={"devices": []})
    def test_reads_stay_open_for_the_snmp_service(self, status, live):
        self.assertEqual(200, self.client.get("/api/sensors-scan/live/").status_code)
        self.assertEqual(200, self.client.get("/api/sensors-scan/discovered/").status_code)

    @patch("rest.sensors_scan_views.minew_scanner.confirm_sensors", return_value={"added": 1})
    def test_confirm_from_the_page(self, confirm):
        self.client.force_login(self.user)
        r = self.client.post("/api/sensors-scan/confirm/", {"macs": ["AA:BB"]}, content_type="application/json", **XHR)
        self.assertEqual(200, r.status_code, r.content)
        confirm.assert_called_once()
