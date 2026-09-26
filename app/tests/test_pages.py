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


class StaticVersionTests(TestCase):
    """Scripts and styles are versioned so browsers never run stale copies."""

    def test_static_v_appends_the_file_modification_time(self):
        import os
        from django.contrib.staticfiles import finders
        from app.templatetags.extras import static_v

        url = static_v("js/app/outputs.js")
        expected = int(os.path.getmtime(finders.find("js/app/outputs.js")))
        self.assertEqual(f"/static/js/app/outputs.js?v={expected}", url)

    def test_static_v_leaves_missing_files_unversioned(self):
        from app.templatetags.extras import static_v
        self.assertEqual("/static/js/app/nope.js", static_v("js/app/nope.js"))

    def test_pages_use_versioned_urls(self):
        self.client.force_login(User.objects.create_user("v", password="x"))
        for name in ("dashboard", "outputs", "alarms", "settings"):
            html = self.client.get(reverse(name)).content.decode()
            self.assertRegex(html, r'src="/static/js/app/ne\.js\?v=\d+"', name)
            self.assertRegex(html, r'href="/static/css/app\.css\?v=\d+"', name)
            self.assertNotRegex(html, r'\?v=\d+\?v=', name)


class SensorsPageTests(TestCase):
    """The sensors page must not render every stored reading."""

    def setUp(self):
        import datetime
        from django.utils import timezone
        from app.models import DataSensor, Sensor

        self.client.force_login(User.objects.create_user("s", password="x"))
        sensors = [Sensor.objects.create(mac_address=f"AA:BB:CC:DD:EE:0{i}") for i in range(3)]
        base = timezone.now()
        DataSensor.objects.bulk_create([
            DataSensor(data_datetime=base - datetime.timedelta(seconds=n),
                       sensor=sensors[n % 3], temperature=20 + n / 1000)
            for n in range(250)
        ])

    def test_only_the_latest_readings_are_rendered(self):
        r = self.client.get(reverse("sensors"))
        html = r.content.decode()
        page = r.context["data_page"]
        self.assertEqual(100, len(page))
        self.assertEqual(250, page.paginator.count)
        # 100 reading rows (each has a temperature cell) instead of all 250
        self.assertEqual(100, html.count("<td class=\"text-center\">2"))
        self.assertIn("1-100", html)
        self.assertIn("250", html)
        self.assertIn("?page=2", html)
        self.assertNotIn("?page=0", html)

    def test_paging_and_order(self):
        r = self.client.get(reverse("sensors") + "?page=3")
        page = r.context["data_page"]
        self.assertEqual(50, len(page))
        self.assertFalse(page.has_next())
        times = [d.data_datetime for d in page]
        self.assertEqual(times, sorted(times, reverse=True))
        # a bad page number falls back to a valid page instead of an error
        self.assertEqual(200, self.client.get(reverse("sensors") + "?page=abc").status_code)
        self.assertEqual(200, self.client.get(reverse("sensors") + "?page=999").status_code)

    def test_query_count_does_not_grow_with_the_readings(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as q:
            self.client.get(reverse("sensors"))
        self.assertLess(len(q), 12, [x["sql"][:80] for x in q])
