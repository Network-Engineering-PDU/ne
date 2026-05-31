"""
    Helper for Constants, Functions and Defaults JSON for models
"""
import csv
import json
import datetime

from django.http import HttpResponse
from django.utils.timezone import make_aware
from django.utils.translation import gettext_lazy as _


def convert_str_to_datetime(s):
    """
    Convert str to datetime
    :param s: str ex: "31/12/2020 12:40" or "31/12/20 12:40"
    :return: datetime
    """
    try:
        return make_aware(datetime.datetime.strptime(s, "%d/%m/%Y %H:%M"))
    except ValueError:
        return make_aware(datetime.datetime.strptime(s, "%d/%m/%Y %H:%M"))


def convert_str_to_date(s):
    """
    Convert str to date
    :param s: str ex: "31/12/2020"
    :return: date
    """
    try:
        return datetime.datetime.strptime(s, "%d/%m/%Y").date()
    except:
        return None


def convert_datetime_to_str(d):
    """
    Convert date to string
    :param d: date ex: 31/12/2020 12:40
    :return: string
    """
    try:
        return datetime.datetime.strftime(d, "%d/%m/%Y %H:%M")
    except:
        return None


def convert_date_to_str(d):
    """
    Convert date to string
    :param d: date ex: 31/12/2020
    :return: string fmt: dd/mm/yyyy
    """
    try:
        return datetime.datetime.strftime(d, "%d/%m/%Y")
    except:
        return None


def bad_json(message=None, error=None, extradata=None):
    data = {'result': 'bad'}
    if message:
        data.update({'message': message})
    if error:
        if error == 0:
            data.update({'message': f"{_('Solicitud Incorrecta')}"})
        elif error == 1:
            data.update({'message': f"{_('Error guardando datos')}"})
        elif error == 2:
            data.update({'message': f"{_('Error actualizando datos')}"})
        elif error == 3:
            data.update({'message': f"{_('Error borrando datos')}"})
        elif error == 4:
            data.update({'message': f"{_('Ud no tiene permisos para ejecutar esta acción')}"})
        elif error == 5:
            data.update({'message': f"{_('Error generando la información')}"})
        elif error == 6:
            data.update({'message': f"{_('Credenciales Incorrectas')}"})
        elif error == 7:
            data.update({'message': f"{_('Objeto no existe')}"})
        else:
            data.update({'message': f"{_('Error de Sistema')}"})
    if extradata:
        data.update(extradata)
    return HttpResponse(json.dumps(data), content_type='application/json')


def ok_json(data=None, simple=None):
    if data:
        if not simple:
            if 'result' not in data.keys():
                data.update({'result': 'ok'})
    else:
        data = {'result': 'ok'}
    return HttpResponse(json.dumps(data), content_type='application/json')


def export_last_data_to_csv(obj, live_data=None):
    from app.models import Output

    last_data = obj.get_last_data()
    obj_name = obj.__str__()

    filename = f'{obj_name}_{datetime.datetime.now().strftime("%d%m%Y%H%M%S")}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={filename}'

    writer = csv.writer(response)

    header_cols = [
        'Name',
        'Low Limit (A)',
        'High Limit (A)',
        'Voltage (V)',
        'Current (A)',
        'Apparent Power (VA)',
        'Active Power (W)',
        'Reactive Power (VAr)',
        'Factor (W)',
        'Energy (kWh)',
        'Phase Total (º)',
        'Phase V-I (º)',
        'Frecuency (Hz)'
    ]
    if isinstance(obj, Output):
        header_cols.append('Socket Type')

    blank_value = ''

    def _fmt(val):
        return blank_value if val is None else f'{val}'

    def _has_measurements(data):
        if not data:
            return False
        keys = (
            'voltage', 'current', 'apparent_power', 'active_power',
            'reactive_power', 'power_factor', 'energy', 'phase_vi', 'frequency',
        )
        return any(data.get(k) is not None for k in keys)

    if _has_measurements(live_data):
        body_cols = [
            obj_name,
            _fmt(obj.low_limit),
            _fmt(obj.high_limit),
            _fmt(live_data.get('voltage')),
            _fmt(live_data.get('current')),
            _fmt(live_data.get('apparent_power')),
            _fmt(live_data.get('active_power')),
            _fmt(live_data.get('reactive_power')),
            _fmt(live_data.get('power_factor')),
            _fmt(live_data.get('energy')),
            _fmt(live_data.get('phase_total')),
            _fmt(live_data.get('phase_vi')),
            _fmt(live_data.get('frequency')),
        ]
    elif last_data is not None:
        body_cols = [
            obj_name,
            _fmt(obj.low_limit),
            _fmt(obj.high_limit),
            _fmt(last_data.voltage),
            _fmt(last_data.current),
            _fmt(last_data.apparent_power),
            _fmt(last_data.active_power),
            _fmt(last_data.reactive_power),
            _fmt(last_data.power_factor),
            _fmt(last_data.energy),
            _fmt(last_data.phase_total),
            _fmt(last_data.phase_vi),
            _fmt(last_data.frequency),
        ]
    else:
        body_cols = [
            obj_name,
            _fmt(obj.low_limit),
            _fmt(obj.high_limit),
        ] + [blank_value] * 10

    if isinstance(obj, Output):
        body_cols.append(obj.socket_type or blank_value)

    writer.writerow(header_cols)
    writer.writerow(body_cols)

    return response
