import datetime
import re

from django.db import transaction, IntegrityError
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from app.helpers import convert_str_to_datetime
from app.models import DataSummary, DataInput, DataOutput, Input, Output, Sensor, DataSensor
from rest.serializer import SensorSerializer


class PDUDataViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Example:
    {
        "datetime": "07/11/2022 16:21",
        "input_lines": [
            {
                "line_id": 1,
                "frequency": 50.00,
                "phase_total": 120.00,
                "phase_vi": 45.00,
                "active_power": 1.23,
                "reactive_power": 1.23,
                "apparent_power": 1.23,
                "energy": 1.23,
                "voltage": 220.00,
                "current": 5.00,
                "power_factor": 0.95
            },
            ...
        ],
        "output_lines": [
            {
                "line_id": 1,
                "frequency": 50.00,
                "phase_total": 120.00,
                "phase_vi": 45.00,
                "active_power": 1.23,
                "reactive_power": 1.23,
                "apparent_power": 1.23,
                "energy": 1.23,
                "voltage": 220.00,
                "current": 5.00,
                "power_factor": 0.95
            },
            ...
        ],
    }
    """
    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():

                datetime_txt = request.data.get('datetime', '')
                if not datetime_txt:
                    return Response({
                        'result': 'ERROR',
                        'detail': 'datetime is missing or empty'
                    }, status=status.HTTP_400_BAD_REQUEST)

                data_datetime = convert_str_to_datetime(datetime_txt)

                input_lines = request.data.get('input_lines', [])
                if not input_lines:
                    return Response({
                        'result': 'ERROR',
                        'detail': 'input_lines list is missing or empty'
                    }, status=status.HTTP_400_BAD_REQUEST)

                output_lines = request.data.get('output_lines', [])
                #TODO: This is not an error. Could not be output lines.
                #TODO: add log or something.
                # if not output_lines:
                #     return Response({
                #         'result': 'ERROR',
                #         'detail': 'output_lines list is missing or empty'
                #     }, status=status.HTTP_400_BAD_REQUEST)

                # Create DataSummary instance
                data_summary, _ = DataSummary.objects.get_or_create(data_datetime=data_datetime)

                # Inputs
                data_inputs_objects = []
                for elem in input_lines:
                    line_id = int(elem['line_id'])
                    try:
                        input_obj = Input.objects.get(line_id=line_id)
                    except Input.DoesNotExist:
                        raise Exception(f'Input does not exist with line_id: {line_id}')

                    data_inputs_objects.append(
                        DataInput(
                            data_summary=data_summary,
                            input=input_obj,
                            frequency=float(elem['frequency']),
                            phase_total=float(elem['phase_total']),
                            phase_vi=float(elem['phase_vi']),
                            active_power=float(elem['active_power']),
                            reactive_power=float(elem['reactive_power']),
                            apparent_power=float(elem['apparent_power']),
                            energy=float(elem['energy']),
                            voltage=float(elem['voltage']),
                            current=float(elem['current']),
                            power_factor=float(elem['power_factor'])
                        )
                    )

                # Outputs
                data_outputs_objects = []
                for elem in output_lines:
                    line_id = int(elem['line_id'])
                    try:
                        output_obj = Output.objects.get(line_id=line_id)
                    except Output.DoesNotExist:
                        raise Exception(f'Output does not exist with line_id: {line_id}')

                    data_outputs_objects.append(
                        DataOutput(
                            data_summary=data_summary,
                            output=output_obj,
                            frequency=float(elem['frequency']),
                            phase_total=float(elem['phase_total']),
                            phase_vi=float(elem['phase_vi']),
                            active_power=float(elem['active_power']),
                            reactive_power=float(elem['reactive_power']),
                            apparent_power=float(elem['apparent_power']),
                            energy=float(elem['energy']),
                            voltage=float(elem['voltage']),
                            current=float(elem['current']),
                            power_factor=float(elem['power_factor'])
                        )
                    )

                if data_inputs_objects:
                    for data_input_obj in data_inputs_objects:
                        data_input_obj.save()
                    print(f'Inputs data succesfully STORED! ({len(data_inputs_objects)} records)')
                if data_outputs_objects:
                    for data_output_obj in data_outputs_objects:
                        data_output_obj.save()
                    print(f'Outputs data succesfully STORED! ({len(data_outputs_objects)} records)')

                # delete old data (only keep last 60 mins of data)
                most_recent_data_datetime = DataSummary.objects.latest('data_datetime').data_datetime
                last_hour_data_datetime = most_recent_data_datetime - datetime.timedelta(minutes=60)
                DataSummary.objects.filter(data_datetime__lte=last_hour_data_datetime).delete()

                # recalculate totals (inputs and outputs)
                data_summary.update_input_totals()
                data_summary.update_output_totals()
                print('Totals Inputs and Outputs data have been UPDATED!')

                return Response({
                    'result': 'OK',
                    'detail': 'Data succesfully saved!',
                }, status=status.HTTP_200_OK)

        except Exception as ex:
            return Response({
                'result': 'ERROR',
                'detail': ex.__str__()
            }, status=status.HTTP_400_BAD_REQUEST)


class SensorsNewViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Example:
    {
        "mac_address": "
    }
    """
    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():

                mac_address = re.sub(r'[^\w]', '', request.data.get('mac_address', ''))
                if not mac_address:
                    return Response({
                        'result': 'ERROR',
                        'detail': 'mac_address is missing or empty'
                    }, status=status.HTTP_400_BAD_REQUEST)

                if Sensor.objects.filter(mac_address=mac_address).exists():
                    return Response({
                        'result': 'ERROR',
                        'detail': f'A Sensor already exist with mac_address {mac_address} in the database'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Create Sensor with flag is_new=True because was provisioned by gw and for later poling
                Sensor.objects.create(mac_address=mac_address, is_new=True)

                return Response({
                    'result': 'OK',
                    'detail': 'Sensor succesfully created!',
                }, status=status.HTTP_200_OK)

        except Exception as ex:
            return Response({
                'result': 'ERROR',
                'detail': ex.__str__()
            }, status=status.HTTP_400_BAD_REQUEST)


class SensorsDataViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer
    """
    Example:
    {
        "data": [
            {
                "mac_address": "123456abcdef",
                "datetime": "12/11/2022 10:40",
                "temperature": 2500,
                "humidity": 30,
                "pressure": 1000000,
                "rssi": -60,
                "battery": 2900
            }
        ]
    }
    """
    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():

                data = request.data.get('data', [])
                if not data:
                    return Response({
                        'result': 'ERROR',
                        'detail': 'data is missing or empty'
                    }, status=status.HTTP_400_BAD_REQUEST)

                data_sensors_objects = []
                for elem in data:
                    try:
                        sensor, _ = Sensor.objects.get_or_create(mac_address=re.sub(r'[^\w]', '', elem['mac_address']))

                        data_datetime = convert_str_to_datetime(elem['datetime'])

                        # Sensors not power (regular procedure we were doing so far)
                        try:
                            temperature = round(int(elem['temperature']) / 100, 2)
                            if temperature > 100:
                                temperature = None
                        except:
                            temperature = None

                        try:
                            humidity = int(elem['humidity'])
                            if humidity > 100:
                                humidity = None
                        except:
                            humidity = None

                        try:
                            pressure = round(int(elem['pressure']) / 100, 2)
                            if pressure == 0:
                                pressure = None
                        except:
                            pressure = None

                        try:
                            rssi = elem['rssi']
                        except:
                            rssi = None

                        try:
                            battery = round(elem['battery'] / 1000, 2)
                        except:
                            battery = None

                        # add payload to DataSensor objs
                        data_sensors_objects.append(
                            DataSensor(
                                sensor=sensor,
                                data_datetime=data_datetime,
                                temperature=temperature,
                                humidity=humidity,
                                pressure=pressure,
                                rssi=rssi,
                                battery=battery,
                            )
                        )

                        # save last time when sensor received data
                        sensor.last_data_received = data_datetime
                        sensor.last_battery_value = battery
                        sensor.save()

                    except Exception as ex:
                        print(ex.__str__())

                if data_sensors_objects:
                    DataSensor.objects.bulk_create(data_sensors_objects)

                # delete old data (only keep last 60 mins of data)
                most_recent_data_datetime = DataSensor.objects.latest('data_datetime').data_datetime
                last_hour_data_datetime = most_recent_data_datetime - datetime.timedelta(minutes=60)
                DataSensor.objects.filter(data_datetime__lte=last_hour_data_datetime).delete()

                return Response({
                    'result': 'OK',
                    'detail': 'Data succesfully saved!',
                }, status=status.HTTP_200_OK)

        except IntegrityError:
            return Response({
                'result': 'Duplication Error',
                'detail': f'Sensor {sensor} and datetime {data_datetime} already exist in the database'
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as ex:
            return Response({
                'result': 'ERROR',
                'detail': ex.__str__()
            }, status=status.HTTP_400_BAD_REQUEST)
