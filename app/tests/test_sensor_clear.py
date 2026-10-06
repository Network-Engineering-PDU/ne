import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import DataSensor, Sensor

XHR = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class ClearSensorDataTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("clear", password="x")
        self.client.force_login(self.user)
        self.a = Sensor.objects.create(mac_address="AA", name="A", last_battery_value=2.5)
        self.b = Sensor.objects.create(mac_address="BB", name="B")
        now = timezone.now()
        for i in range(3):
            DataSensor.objects.create(sensor=self.a, data_datetime=now - datetime.timedelta(seconds=i))
            DataSensor.objects.create(sensor=self.b, data_datetime=now - datetime.timedelta(seconds=i))
        self.a.last_data_received = now
        self.a.save()

    def url(self, sensor):
        return reverse("sensor_clear_data", args=[sensor.id])

    def test_clears_only_the_selected_sensor(self):
        r = self.client.post(self.url(self.a), **XHR)
        self.assertEqual({"result": "ok", "deleted": 3}, r.json())
        self.assertEqual(0, DataSensor.objects.filter(sensor=self.a).count())
        self.assertEqual(3, DataSensor.objects.filter(sensor=self.b).count())

    def test_sensor_itself_and_its_name_are_kept(self):
        self.client.post(self.url(self.a), **XHR)
        self.a.refresh_from_db()
        self.assertEqual("A", self.a.name)
        self.assertIsNone(self.a.last_data_received)
        self.assertIsNone(self.a.last_battery_value)

    def test_needs_post_and_the_ajax_header(self):
        self.assertEqual("bad", self.client.post(self.url(self.a)).json()["result"])
        self.assertEqual("bad", self.client.get(self.url(self.a), **XHR).json()["result"])
        self.assertEqual(3, DataSensor.objects.filter(sensor=self.a).count())

    def test_anonymous_cannot_clear(self):
        self.client.logout()
        r = self.client.post(self.url(self.a), **XHR)
        self.assertNotEqual(200, r.status_code)
        self.assertEqual(3, DataSensor.objects.filter(sensor=self.a).count())

    def test_unknown_sensor(self):
        r = self.client.post(reverse("sensor_clear_data", args=[9999]), **XHR)
        self.assertEqual("bad", r.json()["result"])

    def test_data_tab_filters_by_sensor(self):
        r = self.client.get(reverse("sensors") + f"?sensor={self.a.id}")
        self.assertEqual(self.a, r.context["selected_sensor"])
        self.assertEqual(3, len(r.context["data_page"]))
        self.assertTrue(all(d.sensor_id == self.a.id for d in r.context["data_page"]))
        html = r.content.decode()
        self.assertIn('id="btnClearSensorData"', html)

    def test_all_sensors_has_no_clear_button(self):
        r = self.client.get(reverse("sensors"))
        self.assertIsNone(r.context["selected_sensor"])
        self.assertNotIn('id="btnClearSensorData"', r.content.decode())
