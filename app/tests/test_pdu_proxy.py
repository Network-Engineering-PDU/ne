from unittest.mock import Mock, patch

import requests
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from app import pdu_proxy

XHR = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def api_response(body=b'{"ok": true}', status=200):
    return Mock(content=body, status_code=status,
                headers={"Content-Type": "application/json"})


class AllowlistTests(TestCase):
    def test_allowed_and_denied_paths(self):
        allowed = [
            ("GET", "outputs"), ("GET", "outputs/data"),
            ("PUT", "outputs/3/switch-status"), ("GET", "alarms"),
            ("POST", "alarms/ack"), ("PUT", "display-config"),
            ("POST", "settings/bluetooth/devices/AA:BB:CC:DD:EE:FF/pair"),
            ("PUT", "settings/pdu-info"),
            ("GET", "network/snmp/display-settings"),
            ("PUT", "network/snmp/display-settings"),
            ("PUT", "settings/modbus"),
            ("POST", "settings/start-modbus"),
        ]
        denied = [
            ("DELETE", "outputs/3/switch-status"),
            ("POST", "settings/system-reboot"),    # not exposed here
            ("POST", "settings/factory-reset"),
            ("GET", "settings/../settings/factory-reset"),
            ("GET", "outputs/1234/data"),
            ("POST", "settings/bluetooth/devices/not-a-mac/pair"),
            ("POST", "settings/bluetooth/devices/AA:BB:CC:DD:EE:FF/../x"),
            ("GET", "network/interfaces"),
            ("GET", "network/snmp/detailed-settings"),   # raw passwords live there
            ("POST", "settings/start-ssh"),
            ("PUT", "alarms"),
            ("GET", "openapi.json"),
        ]
        for method, path in allowed:
            self.assertTrue(pdu_proxy.is_allowed(method, path), (method, path))
        for method, path in denied:
            self.assertFalse(pdu_proxy.is_allowed(method, path), (method, path))


class ProxyViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("op", password="x")
        self.url = lambda p: reverse("pdu_proxy", kwargs={"path": p})

    def test_requires_login_and_returns_401_json(self):
        r = self.client.get(self.url("alarms"))
        self.assertEqual(401, r.status_code)
        self.assertEqual("Unauthorized", r.json()["message"])

    @patch("app.pdu_proxy.requests.request")
    def test_get_is_forwarded(self, request_mock):
        self.client.force_login(self.user)
        request_mock.return_value = api_response()
        r = self.client.get(self.url("alarms"))
        self.assertEqual(200, r.status_code)
        self.assertEqual({"ok": True}, r.json())
        self.assertEqual("GET", request_mock.call_args[0][0])
        self.assertTrue(request_mock.call_args[0][1].endswith("/alarms"))

    @patch("app.pdu_proxy.requests.request")
    def test_collection_routes_get_trailing_slash(self, request_mock):
        self.client.force_login(self.user)
        request_mock.return_value = api_response()
        self.client.get(self.url("outputs"))
        self.assertTrue(request_mock.call_args[0][1].endswith("/outputs/"))

    @patch("app.pdu_proxy.requests.request")
    def test_write_needs_ajax_header_and_forwards_body(self, request_mock):
        self.client.force_login(self.user)
        request_mock.return_value = api_response(b"null")
        body = '{"switch_status": true}'
        r = self.client.put(self.url("outputs/2/switch-status"), body,
                            content_type="application/json")
        self.assertEqual(403, r.status_code)
        request_mock.assert_not_called()
        r = self.client.put(self.url("outputs/2/switch-status"), body,
                            content_type="application/json", **XHR)
        self.assertEqual(200, r.status_code)
        self.assertEqual(body.encode(), request_mock.call_args[1]["data"])

    @patch("app.pdu_proxy.requests.request")
    def test_not_allowed_path_never_reaches_the_api(self, request_mock):
        self.client.force_login(self.user)
        r = self.client.post(self.url("settings/factory-reset"), **XHR)
        self.assertEqual(404, r.status_code)
        request_mock.assert_not_called()

    @patch("app.pdu_proxy.requests.request")
    def test_only_whitelisted_query_params_are_forwarded(self, request_mock):
        self.client.force_login(self.user)
        request_mock.return_value = api_response()
        self.client.get(self.url("settings/update-status") + "?refresh=true&x=1")
        self.assertEqual({"refresh": "true"}, request_mock.call_args[1]["params"])

    @patch("app.pdu_proxy.requests.request")
    def test_api_status_and_unreachable(self, request_mock):
        self.client.force_login(self.user)
        request_mock.return_value = api_response(b'{"detail":"x"}', 422)
        self.assertEqual(422, self.client.get(self.url("alarms")).status_code)
        request_mock.reset_mock()
        request_mock.side_effect = requests.ConnectionError("down")
        r = self.client.get(self.url("alarms"))
        self.assertEqual(502, r.status_code)
        # the configured PDU URL and the localhost fallback were both tried
        self.assertEqual(len(list(pdu_proxy.get_pdu_base_urls())),
                         request_mock.call_count)
