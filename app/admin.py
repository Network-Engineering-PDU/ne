from django.contrib import admin

from app.helpers import convert_datetime_to_str
from app.models import (
    DataSummary, DataInput, DataOutput, DataSensor,
    Host, Input, Output, Sensor
)


class BaseModelAdmin(admin.ModelAdmin):
    list_per_page = 20

    # methods to format dates
    def get_data_datetime(self, obj):
        if obj.data_datetime:
            return convert_datetime_to_str(obj.data_datetime)
        return ''

    get_data_datetime.short_description = 'datetime'


@admin.register(Host)
class HostAdmin(BaseModelAdmin):
    list_display = (
        'name',
        'ip',
    )
    search_fields = (
        'name',
        'ip'
    )


@admin.register(Sensor)
class SensorAdmin(BaseModelAdmin):
    list_display = (
        'mac_address',
        'name',
        'last_battery_value',
        'last_data_received',
        'is_new'
    )
    search_fields = (
        'mac_address',
        'name'
    )
    list_filter = (
        'is_new',
    )


@admin.register(Input)
class InputAdmin(BaseModelAdmin):
    list_display = (
        'line_id',
        'low_limit',
        'high_limit',
    )
    search_fields = (
        'line_id',
    )


@admin.register(Output)
class OutputAdmin(BaseModelAdmin):
    list_display = (
        'line_id',
        'name',
        'socket_type',
        'low_limit',
        'high_limit',
    )
    search_fields = (
        'line_id',
    )


@admin.register(DataSummary)
class DataSummaryAdmin(BaseModelAdmin):
    list_display = (
        'get_data_datetime',
        # inputs totals
        'input_active_power_total',
        'input_reactive_power_total',
        'input_apparent_power_total',
        'input_energy_total',
        'input_current_total',
        'input_voltage_avg',
        # outputs totals
        'output_active_power_total',
        'output_reactive_power_total',
        'output_apparent_power_total',
        'output_energy_total',
        'output_current_total',
        'output_voltage_avg',
    )


@admin.register(DataInput)
class DataInputAdmin(BaseModelAdmin):
    list_display = (
        'data_summary',
        'input',
        'frequency',
        'phase_total',
        'phase_vi',
        'active_power',
        'reactive_power',
        'apparent_power',
        'energy',
        'voltage',
        'current',
        'power_factor'
    )


@admin.register(DataOutput)
class DataOutputAdmin(BaseModelAdmin):
    list_display = (
        'data_summary',
        'output',
        'frequency',
        'phase_total',
        'phase_vi',
        'active_power',
        'reactive_power',
        'apparent_power',
        'energy',
        'voltage',
        'current',
        'power_factor'
    )


@admin.register(DataSensor)
class DataSensorAdmin(BaseModelAdmin):
    list_display = (
        'data_datetime',
        'sensor',
        'temperature',
        'humidity',
        'pressure',
        'rssi',
        'battery',
        'created_at',
    )
