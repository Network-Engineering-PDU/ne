from django.db import models
from django.db.models import Sum, Avg
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app.helpers import convert_datetime_to_str


class Host(models.Model):
    name = models.CharField(max_length=100)
    ip = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = _('Hosts')
        db_table = 'hosts'


class Sensor(models.Model):
    mac_address = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    last_battery_value = models.FloatField(blank=True, null=True)
    last_data_received = models.DateTimeField(blank=True, null=True)
    is_new = models.BooleanField(default=False)     # for gw provisioning logic

    def __str__(self):
        return self.mac_address

    class Meta:
        verbose_name_plural = _('Sensores')
        db_table = 'sensors'

    def get_last_data_obj(self):
        try:
            return self.datasensor_set.latest('data_datetime')
        except:
            return None


class Input(models.Model):
    line_id = models.PositiveSmallIntegerField(unique=True)
    low_limit = models.FloatField(blank=True, null=True)
    high_limit = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f'Input {self.line_id}'

    class Meta:
        verbose_name_plural = _('Inputs')
        db_table = 'inputs'

    def get_last_data(self):
        try:
            return self.datainput_set.latest('data_summary__data_datetime')
        except:
            return None

    def get_data_for_charts(self):
        return [
            {
                'date': int(x.data_summary.data_datetime.strftime("%s%f")) / 1000,
                'voltage': x.voltage,
                'current': x.current,
                'active_power': x.active_power,
                # 'reactive_power': x.reactive_power,
                'power_factor': x.power_factor,
            } for x in self.datainput_set.order_by('data_summary__data_datetime')
        ]


class Output(models.Model):
    line_id = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    socket_type = models.CharField(max_length=100, blank=True, null=True)
    low_limit = models.FloatField(blank=True, null=True)
    high_limit = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f'Output {self.line_id}'

    class Meta:
        verbose_name_plural = _('Salidas')
        db_table = 'outputs'

    def get_last_data(self):
        try:
            return self.dataoutput_set.latest('data_summary__data_datetime')
        except:
            return None


class DataSummary(models.Model):
    data_datetime = models.DateTimeField()
    # total inputs
    input_active_power_total = models.FloatField(default=0)
    input_reactive_power_total = models.FloatField(default=0)
    input_apparent_power_total = models.FloatField(default=0)
    input_energy_total = models.FloatField(default=0)
    input_current_total = models.FloatField(default=0)
    input_voltage_avg = models.FloatField(default=0)
    # totales outputs
    output_active_power_total = models.FloatField(default=0)
    output_reactive_power_total = models.FloatField(default=0)
    output_apparent_power_total = models.FloatField(default=0)
    output_energy_total = models.FloatField(default=0)
    output_current_total = models.FloatField(default=0)
    output_voltage_avg = models.FloatField(default=0)

    def __str__(self):
        return convert_datetime_to_str(self.data_datetime)

    class Meta:
        verbose_name_plural = _('Datos - Resumen')
        db_table = 'data_summary'
        ordering = ('-data_datetime', )

    def update_input_totals(self):
        try:
            objs = self.datainput_set.aggregate(
                input_active_power_total=Sum('active_power'),
                input_reactive_power_total=Sum('reactive_power'),
                input_apparent_power_total=Sum('apparent_power'),
                input_energy_total=Sum('energy'),
                input_current_total=Sum('current'),
                input_voltage_avg=Avg('voltage'),
            )
            self.input_active_power_total = objs['input_active_power_total']
            self.input_reactive_power_total = objs['input_reactive_power_total']
            self.input_apparent_power_total = objs['input_apparent_power_total']
            self.input_energy_total = objs['input_energy_total']
            self.input_current_total = objs['input_current_total']
            self.input_voltage_avg = objs['input_voltage_avg']
            self.save()
        except:
            pass

    def update_output_totals(self):
        try:
            objs = self.dataoutput_set.aggregate(
                output_active_power_total=Sum('active_power'),
                output_reactive_power_total=Sum('reactive_power'),
                output_apparent_power_total=Sum('apparent_power'),
                output_energy_total=Sum('energy'),
                output_current_total=Sum('current'),
                output_voltage_avg=Avg('voltage'),
            )
            self.output_active_power_total = objs['output_active_power_total']
            self.output_reactive_power_total = objs['output_reactive_power_total']
            self.output_apparent_power_total = objs['output_apparent_power_total']
            self.output_energy_total = objs['output_energy_total']
            self.output_current_total = objs['output_current_total']
            self.output_voltage_avg = objs['output_voltage_avg']
            self.save()
        except:
            pass


class DataDetail(models.Model):
    data_summary = models.ForeignKey(DataSummary, on_delete=models.CASCADE)
    voltage = models.FloatField(default=0)
    current = models.FloatField(default=0)
    apparent_power = models.FloatField(default=0)
    active_power = models.FloatField(default=0)
    reactive_power = models.FloatField(default=0)
    power_factor = models.FloatField(default=0)
    energy = models.FloatField(default=0)
    phase_total = models.FloatField(default=0)
    phase_vi = models.FloatField(default=0)
    frequency = models.FloatField(default=0)

    class Meta:
        abstract = True
        ordering = ('data_summary', )


class DataInput(DataDetail):
    input = models.ForeignKey(Input, on_delete=models.CASCADE)

    def __str__(self):
        return self.input.__str__()

    class Meta:
        verbose_name_plural = _('Datos - Entradas')
        db_table = 'data_inputs'


class DataOutput(DataDetail):
    output = models.ForeignKey(Output, on_delete=models.CASCADE)

    def __str__(self):
        return self.output.__str__()

    class Meta:
        verbose_name_plural = _('Datos - Salidas')
        db_table = 'data_outputs'


class DataSensor(models.Model):
    data_datetime = models.DateTimeField(blank=True, null=True)
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE)
    temperature = models.FloatField(blank=True, null=True, verbose_name=_('Temperatura (ºC)'))
    humidity = models.FloatField(blank=True, null=True, verbose_name=_('Humedad (%)'))
    pressure = models.FloatField(blank=True, null=True, verbose_name=_('Presión (pa)'))
    rssi = models.IntegerField(blank=True, null=True, verbose_name=_('Rssi (dB)'))
    battery = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return convert_datetime_to_str(self.data_datetime)

    class Meta:
        verbose_name_plural = _('Datos - Sensores')
        db_table = 'data_sensors'
        unique_together = ('data_datetime', 'sensor')
