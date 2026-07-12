"""Shared helpers for saving BLE sensor readings into the NE database."""
import datetime
import re

from django.db import transaction

from app.helpers import convert_str_to_datetime
from app.models import DataSensor, Sensor


def normalize_mac(mac: str) -> str:
    return re.sub(r'[^\w]', '', mac).upper()


def format_mac_display(mac: str) -> str:
    raw = normalize_mac(mac)
    if len(raw) != 12:
        return mac.upper()
    return ':'.join(raw[i:i + 2] for i in range(0, 12, 2))


def save_sensor_readings(readings: list) -> int:
    """
    Persist a batch of sensor readings (same rules as SensorsDataViewSet.create).

    Each reading dict may include: mac_address, datetime, temperature, humidity,
    pressure, rssi, battery.
    Returns number of rows saved.
    """
    if not readings:
        return 0

    saved = 0
    with transaction.atomic():
        for elem in readings:
            try:
                sensor, _ = Sensor.objects.get_or_create(
                    mac_address=normalize_mac(elem['mac_address'])
                )
                data_datetime = convert_str_to_datetime(elem['datetime'])

                try:
                    temperature = round(int(elem['temperature']) / 100, 2)
                    if temperature > 100:
                        temperature = None
                except (TypeError, ValueError, KeyError):
                    temperature = None

                try:
                    humidity = int(elem['humidity'])
                    if humidity > 100:
                        humidity = None
                except (TypeError, ValueError, KeyError):
                    humidity = None

                try:
                    pressure = round(int(elem['pressure']) / 100, 2)
                    if pressure == 0:
                        pressure = None
                except (TypeError, ValueError, KeyError):
                    pressure = None

                try:
                    rssi = elem['rssi']
                except KeyError:
                    rssi = None

                try:
                    battery = round(elem['battery'] / 1000, 2)
                except (TypeError, ValueError, KeyError):
                    battery = None

                DataSensor.objects.update_or_create(
                    sensor=sensor,
                    data_datetime=data_datetime,
                    defaults={
                        'temperature': temperature,
                        'humidity': humidity,
                        'pressure': pressure,
                        'rssi': rssi,
                        'battery': battery,
                    },
                )
                if (sensor.last_data_received is None or
                        data_datetime >= sensor.last_data_received):
                    sensor.last_data_received = data_datetime
                    sensor.last_battery_value = battery
                    sensor.save()
                saved += 1
            except Exception as ex:
                print(ex)

        if saved:
            most_recent = DataSensor.objects.latest('data_datetime').data_datetime
            cutoff = most_recent - datetime.timedelta(minutes=60)
            DataSensor.objects.filter(data_datetime__lte=cutoff).delete()

    return saved
