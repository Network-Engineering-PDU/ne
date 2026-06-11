from rest_framework import serializers

from app.models import DataSensor, Sensor


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

    @staticmethod
    def get_last_data(obj):
        last_data = obj.get_last_data_obj()
        return DataSensorSerializer(instance=last_data, many=False).data
