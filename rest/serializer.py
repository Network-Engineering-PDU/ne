from rest_framework import serializers

from app.models import DataSensor, Sensor
from app.sensor_ble_service import format_mac_display


class DataSensorSerializer(serializers.ModelSerializer):

    class Meta:
        model = DataSensor
        fields = (
            'data_datetime', 'temperature', 'humidity', 'pressure', 'rssi', 'battery'
        )


class SensorSerializer(serializers.ModelSerializer):
    last_data = serializers.SerializerMethodField()

    class Meta:
        model = Sensor
        fields = (
            'id', 'mac_address', 'name', 'last_data'
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['mac_address'] = format_mac_display(instance.mac_address)
        return data

    @staticmethod
    def get_last_data(obj):
        last_data = obj.get_last_data_obj()
        return DataSensorSerializer(instance=last_data, many=False).data
