import json
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class ComsNetworkProxyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("network-admin", password="test")
        self.client.force_login(self.user)

    @patch("app.views.requests.get")
    def test_get_network_config_preserves_expanded_fields(self, get_mock):
        get_mock.return_value = Mock(
            status_code=200,
            json=Mock(return_value={
                "type": 3,
                "dhcp": False,
                "params": {
                    "ip": "192.168.1.100",
                    "subnet_mask": "255.255.255.0",
                    "gateway_ip": "192.168.1.1",
                    "dns": "8.8.8.8",
                    "ssid": "Ahmed",
                    "password": "",
                    "eth_interface": "eth0",
                },
                "eth_interface": "eth0",
                "nw_mode": 3,
                "lan1_ip": "192.168.1.100",
                "lan1_gateway": "192.168.1.1",
                "lan2_ip": "192.168.1.200",
                "lan2_gateway": "",
                "wifi_ip": "192.168.1.150",
                "wifi_subnet_mask": "255.255.255.0",
                "wifi_gateway": "192.168.1.1",
                "wifi_dns": "8.8.8.8",
                "ethernet_mac": "AA:BB:CC:DD:EE:01",
                "wifi_mac": "AA:BB:CC:DD:EE:02",
            }),
            text="",
        )

        response = self.client.post(reverse("coms"), {
            "endpoint": "network/interfaces",
            "method": "GET",
        })

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["result"], "ok")
        self.assertEqual(body["nw_mode"], 3)
        self.assertEqual(body["lan2_ip"], "192.168.1.200")
        self.assertEqual(body["wifi_ip"], "192.168.1.150")
        self.assertEqual(body["wifi_subnet_mask"], "255.255.255.0")
        self.assertEqual(body["eth_interface"], "eth0")

    @patch("app.views.requests.put")
    def test_put_network_config_forwards_complete_payload(self, put_mock):
        put_mock.return_value = Mock(status_code=202, text="")
        payload = {
            "type": 3,
            "dhcp": False,
            "nw_mode": 3,
            "eth_interface": "eth0",
            "lan1_ip": "192.168.1.100",
            "lan1_gateway": "192.168.1.1",
            "lan2_ip": "192.168.1.200",
            "lan2_gateway": "",
            "wifi_ip": "192.168.1.150",
            "wifi_subnet_mask": "255.255.255.0",
            "wifi_gateway": "192.168.1.1",
            "wifi_dns": "8.8.8.8",
            "params": {
                "ip": "192.168.1.100",
                "subnet_mask": "255.255.255.0",
                "gateway_ip": "192.168.1.1",
                "dns": "8.8.8.8",
                "ssid": "Ahmed",
                "password": "",
                "eth_interface": "eth0",
            },
        }

        response = self.client.post(reverse("coms"), {
            "endpoint": "network/interfaces",
            "method": "PUT",
            "payload": json.dumps(payload),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "ok")
        forwarded = put_mock.call_args.kwargs["json"]
        self.assertEqual(forwarded, payload)
        self.assertEqual(put_mock.call_args.kwargs["timeout"], 15)

    def test_network_page_uses_independent_language_catalogs(self):
        english = self.client.get("/en/coms/")
        self.assertContains(english, "Network Mode")
        self.assertContains(english, "Single LAN")
        self.assertContains(english, "Wi-Fi Configuration")
        self.assertContains(english, "The Wi\\u002DFi SSID is required.")
        self.assertNotContains(english, "Modo de Red")
        self.assertNotContains(english, "El SSID Wi\\u002DFi es obligatorio.")

        spanish = self.client.get("/es/coms/")
        self.assertContains(spanish, "Modo de Red")
        self.assertContains(spanish, "LAN Única")
        self.assertContains(spanish, "Configuración Wi-Fi")
        self.assertContains(spanish, "El SSID Wi\\u002DFi es obligatorio.")
        self.assertNotContains(spanish, "Network Mode")
        self.assertNotContains(spanish, "The Wi\\u002DFi SSID is required.")
