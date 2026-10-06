import importlib

from django.apps import apps
from django.test import TestCase

from app.models import Sensor

migration = importlib.import_module("app.migrations.0008_sensor_kind")


class SensorKindTests(TestCase):
    def test_legacy_rows_get_their_type_from_the_name(self):
        Sensor.objects.create(mac_address="AA", name="BeaconX Pro")
        Sensor.objects.create(mac_address="BB", name="MST01")
        Sensor.objects.create(mac_address="CC", name="Room")
        migration.set_kind_from_name(apps, None)
        self.assertEqual("MOKO", Sensor.objects.get(mac_address="AA").kind)
        self.assertEqual("MST01", Sensor.objects.get(mac_address="BB").kind)
        self.assertEqual("", Sensor.objects.get(mac_address="CC").kind)

    def test_list_shows_the_sensor_type(self):
        from django.contrib.auth.models import User
        from django.urls import reverse
        self.client.force_login(User.objects.create_user("kind", password="x"))
        Sensor.objects.create(mac_address="DD", name="x", kind="MOKO")
        html = self.client.get(reverse("sensors")).content.decode()
        self.assertIn("MOKO BeaconX Pro", html)
