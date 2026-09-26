from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class PageTests(TestCase):
    """Every page renders inside the shared shell for a logged in user."""

    def setUp(self):
        self.user = User.objects.create_user("viewer", password="x")

    def test_pages_require_login(self):
        for name in ("dashboard", "alarms", "outputs", "settings", "coms",
                     "inputs", "sensors", "users"):
            r = self.client.get(reverse(name))
            self.assertEqual(302, r.status_code, name)
            self.assertIn("/login", r["Location"], name)

    @patch("app.views.requests.get")
    def test_pages_render_with_navigation(self, get_mock):
        get_mock.return_value = Mock(status_code=404, json=Mock(return_value={}))
        self.client.force_login(self.user)
        for name in ("dashboard", "alarms", "outputs", "settings", "coms",
                     "sensors", "users"):
            r = self.client.get(reverse(name))
            self.assertEqual(200, r.status_code, name)
            html = r.content.decode()
            self.assertIn('class="ne-shell"', html, name)
            self.assertEqual(1, html.count('aria-current="page"'), name)
            # every page exposes the alarm badge fed by the API
            self.assertIn("data-alarm-count", html, name)

    def test_alarms_page_has_controls(self):
        self.client.force_login(self.user)
        html = self.client.get(reverse("alarms")).content.decode()
        self.assertIn('id="btnAckAll"', html)
        self.assertIn("alarms.js", html)

    def test_outlets_page_embeds_csv_urls_safely(self):
        from app.models import Output
        Output.objects.create(line_id=1, name="O1")
        self.client.force_login(self.user)
        html = self.client.get(reverse("outputs")).content.decode()
        self.assertIn('id="csvUrls"', html)
        self.assertIn("download_last_data", html)

    def test_settings_post_rejects_unknown_endpoints(self):
        self.client.force_login(self.user)
        for endpoint in ("settings/start-scan", "network/reset", "../etc"):
            r = self.client.post(reverse("settings"), {"endpoint": endpoint})
            self.assertEqual("bad", r.json()["result"], endpoint)

    @patch("app.views.requests.post")
    def test_settings_post_reboot_is_forwarded(self, post_mock):
        post_mock.return_value = Mock(status_code=200, text="")
        self.client.force_login(self.user)
        r = self.client.post(reverse("settings"), {"endpoint": "settings/system-reboot"})
        self.assertEqual("ok", r.json()["result"])
        self.assertTrue(post_mock.call_args[0][0].endswith("/settings/system-reboot"))

    def test_login_page_is_public(self):
        r = self.client.get(reverse("login"))
        self.assertEqual(200, r.status_code)
        self.assertNotIn("ne-shell", r.content.decode())


class NetworksNamingTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("nw", password="x"))

    def test_coms_page_is_called_networks(self):
        for prefix, label in (("/en", "Networks"), ("/es", "Redes")):
            html = self.client.get(f"{prefix}/coms/").content.decode()
            self.assertIn(f"</svg>{label}</a>", html, prefix)      # sidebar
            self.assertRegex(html, rf"<h1[^>]*>\s*{label}\s*</h1>")
            self.assertNotIn(">Coms<", html, prefix)
