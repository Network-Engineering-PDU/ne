import datetime
import importlib
import json
import os
import time
import requests
from django.core.files.storage import FileSystemStorage

from django.utils.translation import gettext_lazy as _
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from app.helpers import bad_json, ok_json, export_last_data_to_csv
from app.models import Input, Output, Host, Sensor, DataSensor
from ne.settings import BASE_URL_PDU, MEDIA_ROOT


def add_global_data(request, data):
    data['user'] = request.user
    data['remoteaddr'] = request.META['REMOTE_ADDR']
    data['now'] = datetime.datetime.now()
    data['BASE_URL_PDU'] = BASE_URL_PDU
    data['lang_code'] = request.LANGUAGE_CODE.lower()


def get_pdu_base_urls():
    candidates = [
        BASE_URL_PDU.rstrip('/'),
        'http://127.0.0.1:8001',
    ]
    seen = set()
    for url in candidates:
        if url and url not in seen:
            seen.add(url)
            yield url


def get_pdu_local_data(endpoint):
    for base_url in get_pdu_base_urls():
        try:
            response = requests.get(
                f"{base_url}/{endpoint}",
                verify=False,
                timeout=5,
            )
            if response.status_code == 200:
                return response.json()
            print(f'PDU local data non-200 [{base_url}/{endpoint}]: {response.status_code}')
        except Exception as ex:
            print(f'PDU local data error [{base_url}/{endpoint}]: {ex}')
    return None


def normalize_phase_vi(ph):
    if ph is None:
        return 0
    if ph > 180.0:
        ph -= 360.0
    elif ph < -180.0:
        ph += 360.0
    if abs(ph) > 90.0:
        ph = ph - 180.0 if ph > 0 else ph + 180.0
    return ph


def positive_energy(value):
    if value is None:
        return None
    return abs(value)


def recalculate_power_from_phase(data):
    """Recompute P/Q/S/PF from V,I and corrected phase (matches pmb.py logic)."""
    if not isinstance(data, dict):
        return data

    import math

    ph = data.get('phase_vi', data.get('phase', 0)) or 0
    ph = normalize_phase_vi(ph)

    voltage = data.get('voltage') or 0
    current = data.get('current') or 0

    if voltage and current:
        data['phase_vi'] = ph
        data['phase'] = ph
        data['active_power'] = voltage * current * math.cos(math.radians(ph))
        data['reactive_power'] = voltage * current * math.sin(math.radians(ph))
        data['apparent_power'] = voltage * current
        data['power_factor'] = math.cos(math.radians(ph))

    # Energy is cumulative — always report magnitude
    if data.get('energy') is not None:
        data['energy'] = positive_energy(data['energy'])

    return data


def normalize_pdu_last_data(data):
    if data is None:
        return None
    if isinstance(data, dict):
        if 'phase' in data and 'phase_vi' not in data:
            data['phase_vi'] = data['phase']
        if 'phase_total' not in data:
            data['phase_total'] = data.get('phase_total', 0)
        return recalculate_power_from_phase(data)
    return data


def map_pdu_input_to_ui(pdu_data, input_obj):
    """
    Map PDU API JSON to the structure used by inputs.html and live_inputs.js.

    PDU response example (inputs/0/data = Input 1):
        voltage, current, active_power, reactive_power, apparent_power,
        power_factor, phase, frequency, energy
    """
    pdu_data = normalize_pdu_last_data(pdu_data) or {}
    return {
        'id': input_obj.id,
        'line_id': input_obj.line_id,
        'name': str(input_obj),
        'voltage': pdu_data.get('voltage'),
        'current': pdu_data.get('current'),
        'apparent_power': pdu_data.get('apparent_power'),
        'active_power': pdu_data.get('active_power'),
        'reactive_power': pdu_data.get('reactive_power'),
        'power_factor': pdu_data.get('power_factor'),
        'energy': positive_energy(pdu_data.get('energy')),
        'phase_vi': pdu_data.get('phase_vi', pdu_data.get('phase')),
        'frequency': pdu_data.get('frequency'),
        'timestamp': int(time.time() * 1000),
    }


def get_pdu_input_data(line_id):
    if not line_id or line_id < 1:
        return None
    return normalize_pdu_last_data(get_pdu_local_data(f'inputs/{line_id - 1}/data'))


def last_data_to_dict(last_data):
    if last_data is None:
        return {}
    if isinstance(last_data, dict):
        return normalize_pdu_last_data(last_data) or {}
    return {
        'voltage': last_data.voltage,
        'current': last_data.current,
        'apparent_power': last_data.apparent_power,
        'active_power': last_data.active_power,
        'reactive_power': last_data.reactive_power,
        'power_factor': last_data.power_factor,
        'energy': positive_energy(last_data.energy),
        'phase_vi': last_data.phase_vi,
        'frequency': last_data.frequency,
    }


def build_input_live_record(input_obj):
    pdu_data = get_pdu_input_data(input_obj.line_id)
    if pdu_data:
        return map_pdu_input_to_ui(pdu_data, input_obj)

    last_data = input_obj.get_last_data()
    if last_data:
        return {
            'id': input_obj.id,
            'line_id': input_obj.line_id,
            'name': str(input_obj),
            'voltage': last_data.voltage,
            'current': last_data.current,
            'apparent_power': last_data.apparent_power,
            'active_power': last_data.active_power,
            'reactive_power': last_data.reactive_power,
            'power_factor': last_data.power_factor,
            'energy': positive_energy(last_data.energy),
            'phase_vi': last_data.phase_vi,
            'frequency': last_data.frequency,
            'timestamp': int(last_data.data_summary.data_datetime.timestamp() * 1000),
        }

    return map_pdu_input_to_ui({}, input_obj)


def login_user(request):
    data = {'title': _('Ingreso')}
    add_global_data(request, data)

    if not data['user'].is_anonymous:
        return HttpResponseRedirect(reverse('dashboard'))

    if request.method == 'POST':
        try:
            username = request.POST['username']
            password = request.POST['password']
            next = request.POST.get('next', '')
            
            user = authenticate(username=username.lower(), password=password)
            if user is not None:
                login(request, user)
                redirect_to = next if next else reverse('dashboard')
                return ok_json(data={'redirect_to': redirect_to})

            return bad_json(error=_('Credenciales Incorrectas'))

        except Exception:
            return bad_json(error=_('Error de Sistema'))

    data['next'] = request.GET.get('next', '')
    return render(request, 'login.html', data)


def logout_user(request):
    logout(request)
    return HttpResponseRedirect(reverse('login'))


def forgot_password(request):
    data = {'title': _('Olvidar Contraseña')}
    add_global_data(request, data)
    return render(request, 'forgot_password.html', data)


@login_required()
def dashboard(request):
    data = {'title': _('Dashboard')}
    add_global_data(request, data)
    return render(request, 'dashboard.html', data)


@login_required()
def inputs(request):
    data = {'title': _('Entradas')}
    add_global_data(request, data)
    data['inputs'] = inputs = Input.objects.all()
    data['data_for_charts'] = []
    for x in inputs:
        items = x.get_data_for_charts()
        if not items:
            pdu_last = get_pdu_input_data(x.line_id)
            if pdu_last:
                items = [{
                    'date': int(time.time() * 1000),
                    'voltage': pdu_last.get('voltage', 0),
                    'current': pdu_last.get('current', 0),
                    'active_power': pdu_last.get('active_power', 0),
                    'power_factor': pdu_last.get('power_factor', 0),
                }]
        data['data_for_charts'].append({
            'name': x.__str__(),
            'items': items,
        })
    data['inputs_live'] = [
        {'input': input_obj, 'live': build_input_live_record(input_obj)}
        for input_obj in inputs
    ]
    return render(request, 'inputs.html', data)


@login_required()
def get_inputs_live_data(request):
    try:
        inputs_data = [
            build_input_live_record(input_obj)
            for input_obj in Input.objects.all()
        ]
        return ok_json(data={'inputs': inputs_data})
    except Exception as ex:
        print(ex.__str__())
        return bad_json(message=ex.__str__())


@login_required()
def update_limits(request):
    data = {'title': _('Actualizar Limites')}
    add_global_data(request, data)

    try:
        with transaction.atomic():

            model_name = request.POST.get('model_name')
            if not model_name:
                return bad_json(message=_('model_name es requerido'))

            obj_id = request.POST.get('obj_id')
            if not model_name:
                return bad_json(message=_('obj_id es requerido'))

            low_limit = request.POST.get('low_limit')
            if low_limit is None:
                return bad_json(message=_('low limit es requerido'))

            high_limit = request.POST.get('high_limit')
            if high_limit is None:
                return bad_json(message=_('high limit es requerido'))

            handler_module = importlib.import_module('app.models')
            model = getattr(handler_module, model_name)
            obj = model.objects.get(id=obj_id)
            obj.low_limit = float(low_limit)
            obj.high_limit = float(high_limit)
            obj.save()

            return ok_json()

    except Exception as ex:
        print(ex.__str__())
        return bad_json(message=ex.__str__())


@login_required()
def input_download_last_data(request, input_id):
    data = {'title': _('Entrada - Descargar Ultimos Datos')}
    add_global_data(request, data)
    input_obj = Input.objects.get(id=input_id)
    live_data = build_input_live_record(input_obj)
    return export_last_data_to_csv(input_obj, live_data=live_data)


@login_required()
def outputs(request):
    data = {'title': _('Salidas')}
    add_global_data(request, data)

    if request.method == 'POST':
        # GET request (settings/license)
        response = requests.get(f'{BASE_URL_PDU}/settings/license', verify=False)
        if response.status_code == 200:
            resp = response.json()
            return ok_json(data={
                'type_id': resp['type_id'],
            })

        return bad_json(message=f'Error in GET settings/license: {response.text}')

    data['outputs'] = Output.objects.all()
    return render(request, 'outputs.html', data)


@login_required()
def output_download_last_data(request, output_id):
    data = {'title': _('Salida - Descargar Ultimos Datos')}
    add_global_data(request, data)
    output = Output.objects.get(id=output_id)
    response = export_last_data_to_csv(output)
    return response


@login_required()
def settings(request):
    data = {'title': _('Configuraciones')}
    add_global_data(request, data)

    if request.method == 'POST':
        # PDU endpoint to be executed from backend because issue when is called from frontend
        endpoint = request.POST['endpoint']

        if endpoint in [
            'settings/start-scan', 'settings/stop-scan',
            'settings/system-reboot', 'settings/factory-reset',
            'settings/swupdate', 'settings/ca-cert', 'settings/ca-key',
        ]:
            # POST (for all above endpoints)
            try:
                # these endpoints will send a file
                if endpoint in ['settings/ca-cert', 'settings/ca-key', 'settings/swupdate']:
                    file = request.FILES.get('file')
                    if not file:
                        return bad_json(message=f"{_('File es requerido')}")
                    # Validate extensions for certs files
                    if endpoint == 'settings/ca-cert' and not file.name.endswith('.crt'):
                        return bad_json(message=f"{_('Extensión Incorrecta. Tiene que ser .crt')}")
                    if endpoint == 'settings/ca-key' and not file.name.endswith('.key'):
                        return bad_json(message=f"{_('Extensión Incorrecta. Tiene que ser .key')}")

                    files = {'file': (file.name, file)}

                    if endpoint == 'settings/swupdate':
                        try:
                            # Crea una instancia de FileSystemStorage con la ubicación deseada
                            fs = FileSystemStorage(location=os.path.join(MEDIA_ROOT))
                            # Guarda el archivo
                            filename = fs.save(file.name, file)
                            filename_path = os.path.join(MEDIA_ROOT, filename)
                            response = requests.post(f'{BASE_URL_PDU}/{endpoint}', json={"filename": filename_path}, verify=False)
                            if response.status_code == 200:
                                resp = response.json()
                                if resp.get('is_pending'):
                                    message = _("Update uploaded. Confirm it on the PDU display.")
                                else:
                                    message = _("Update uploaded. Device update will start shortly.")
                                return ok_json(data={'message': f"{message}"})

                            return bad_json(message=f'Error in POST {endpoint}: {response.text}')

                        except Exception as ex:
                            return bad_json(message=f'Error in POST {endpoint}: {ex.__str__()}')
                    else:
                        response = requests.post(f'{BASE_URL_PDU}/{endpoint}', files=files, verify=False)

                        if response.status_code == 200:
                            return ok_json(data={'message': f"{_('Cambios guardados correctamente')}"})

                # rest of the endpoints (not files associate)
                else:
                    response = requests.post(f'{BASE_URL_PDU}/{endpoint}', verify=False)
                    if response.status_code == 200:
                        return ok_json(data={'message': f"{_('Cambios guardados correctamente')}"})

                return bad_json(message=f'Error in POST {endpoint}: {response.text}')
            except Exception as ex:
                return bad_json(message=f'Error in POST {endpoint}: {ex.__str__()}')

        elif endpoint in ['settings/system-info', 'settings/pdu-info', 'settings/snmp-nms']:
            # GET & PUT only for settings/snmp-nms
            method = request.POST['method']
            try:
                if method == 'GET':
                    # dynamic GET request
                    response = requests.get(f'{BASE_URL_PDU}/{endpoint}', verify=False)
                    if response.status_code == 200:
                        resp = response.json()
                        # settings/system-info
                        if endpoint == 'settings/system-info':
                            return ok_json(data={
                                'message': f"{_('Cambios guardados correctamente')}",
                                'product_name': resp['product_name'],
                                'product_pn': resp['product_pn'],
                                'product_sn': resp['product_sn'],
                                'lan_mac': resp['lan_mac'],
                                'sw_version': resp['sw_version']
                            })
                        elif endpoint == 'settings/pdu-info':
                            return ok_json(data={
                                'message': f"{_('Cambios guardados correctamente')}",
                                'outlet_count': resp['outlet_count'],
                                'rated_current': resp['rated_current'],
                                'controller': resp['controller'],
                                'type': resp['type']
                            })
                        elif endpoint == 'settings/snmp-nms':
                            return ok_json(data={
                                'message': f"{_('Cambios guardados correctamente')}",
                                'system_name': resp['system_name'],
                                'system_contact': resp['system_contact'],
                                'system_location': resp['system_location'],
                            })

                    return bad_json(message=f'Error in GET {endpoint}: {response.text}')
                # PUT
                else:
                    # dynamic PUT request with payloads (for all endpoints)
                    payload = json.loads(request.POST['payload'])
                    response = requests.put(f'{BASE_URL_PDU}/{endpoint}', json=payload, verify=False)
                    if response.status_code == 200:
                        return ok_json(data={'message': f"{_('Cambios guardados correctamente')}"})
                    return bad_json(message=f'Error in {method} {endpoint}: {response.text}')

            except Exception as ex:
                return bad_json(message=f'Error in GET {endpoint}: {ex.__str__()}')

    return render(request, 'settings.html', data)


@login_required()
def coms(request):
    data = {'title': _('Coms')}
    add_global_data(request, data)

    if request.method == 'POST':
        # PDU endpoint to be executed from backend because issue when is called from frontend
        endpoint = request.POST['endpoint']
        method = request.POST['method']

        if endpoint in [
            'network/services', 'network/interfaces', 'network/snmp/settings', 'network/snmp/detailed-settings',
            'settings/start-ssh', 'settings/stop-ssh', 'settings/start-snmp', 'settings/stop-snmp',
            'settings/start-modbus', 'settings/stop-modbus', 'settings/modbus'
        ]:
            # GET, POST and PUT (for above network endpoints)
            try:
                if method == 'GET':
                    # dynamic GET request
                    response = requests.get(f'{BASE_URL_PDU}/{endpoint}', verify=False)
                    if response.status_code == 200:
                        resp = response.json()
                        # network/services
                        if endpoint == 'network/services':
                            return ok_json(data={
                                'ssh': resp['ssh'],
                                'snmp': resp['snmp'],
                                'modbus': resp['modbus']
                            })
                        # settings/modbus
                        elif endpoint == 'settings/modbus':
                            return ok_json(data={
                                'addr': resp['addr']
                            })
                        # network/interfaces
                        elif endpoint == 'network/interfaces':
                            # new types and logic based on type and dhcp
                            type = resp['type']
                            if type == 2:   # ETH_DHCP
                                resp['type'] = True
                                resp['dhcp'] = True
                            elif type == 3: # ETH_STATIC
                                resp['type'] = True
                                resp['dhcp'] = False
                            elif type == 4:  # WIFI_DHCP
                                resp['type'] = False
                                resp['dhcp'] = True
                            else:   # WIFI_STATIC (5)
                                resp['type'] = False
                                resp['dhcp'] = False

                            return ok_json(data={
                                'message': f"{_('Cambios guardados correctamente')}",
                                'type': type,
                                'dhcp': resp['dhcp'],
                                'ethernet_mac': resp['ethernet_mac'],
                                'wifi_mac': resp['wifi_mac'],
                                'params': resp['params']
                            })
                        elif endpoint == 'network/snmp/settings':
                            return ok_json(data={
                                'message': f"{_('Cambios guardados correctamente')}",
                                'beep': resp['beep'],
                                'relay': resp['relay'],
                                'trap_alarm': resp['trap_alarm'],
                                'email_alarm': resp['email_alarm'],
                                'refresh_period': resp['refresh_period'],
                                'life_time': resp['life_time'],
                                'datetime': resp['datetime'],
                                'modbus_address': resp['modbus_address'],
                            })
                        elif endpoint == 'network/snmp/detailed-settings':
                            return ok_json(data={
                                'message': f"{_('Cambios guardados correctamente')}",
                                'port': resp['port'],
                                'trap': resp['trap'],
                                'snmp_v1_v2c': resp['snmp_v1_v2c'],
                                'snmp_v3': None,    # revisar si se usa este obj pq no esta en el response
                            })

                    return bad_json(message=f'Error in {method} {endpoint}: {response.text}')

                # services enable or disable (ssh and snmp) and modbus_addr value
                elif method == 'POST':
                    if endpoint == 'settings/modbus':
                        # PUT para actualizar modbus
                        modbus_addr = request.POST.get('modbus_addr')
                        if modbus_addr:
                            try:
                                addr = int(modbus_addr)
                            except:
                                addr = None
                            if addr:
                                response = requests.put(f'{BASE_URL_PDU}/{endpoint}', json={'addr': addr}, verify=False)
                                if response.status_code == 200:
                                    return ok_json(data={'message': f"{_('Cambios guardados correctamente')}"})
                                return bad_json(message=f'Error in {method} {endpoint}: {response.text}')
                    else:
                        response = requests.post(f'{BASE_URL_PDU}/{endpoint}', verify=False)
                        if response.status_code == 200:
                            return ok_json(data={'message': f"{_('Cambios guardados correctamente')}"})
                        return bad_json(message=f'Error in {method} {endpoint}: {response.text}')

                # PUT
                else:
                    # dynamic PUT request with payloads (for all endpoints)
                    payload = json.loads(request.POST['payload'])
                    if endpoint == 'network/interfaces':
                        # new types and logic based on type and dhcp
                        if payload['type'] == 'ethernet' and payload['dhcp']:
                            payload['type'] = 2  # ETH_DHCP
                        elif payload['type'] == 'ethernet' and not payload['dhcp']:
                            payload['type'] = 3 # ETH_STATIC
                        elif payload['type'] != 'ethernet' and payload['dhcp']:
                            payload['type'] = 4 # WIFI_DHCP
                        else:
                            payload['type'] = 5  # WIFI_STATIC
                    response = requests.put(f'{BASE_URL_PDU}/{endpoint}', json=payload, verify=False)
                    if response.status_code == 200:
                        return ok_json(data={'message': f"{_('Cambios guardados correctamente')}"})
                    return bad_json(message=f'Error in {method} {endpoint}: {response.text}')

            except Exception as ex:
                return bad_json(message=f'Error in {method} {endpoint}: {ex.__str__()}')

    data['hosts'] = Host.objects.all()
    return render(request, 'coms.html', data)


@login_required()
def hosts(request):
    data = {'title': _('Hosts')}
    add_global_data(request, data)

    action = request.POST.get('action', '')
    if not action:
        return bad_json(message=_('action es requerido'))

    try:
        with transaction.atomic():

            host_id = int(request.POST.get('id'))
            name = request.POST.get('name')
            ip = request.POST.get('ip')

            if action in ['edit', 'delete']:
                if not host_id:
                    return bad_json(message=_('host_id es requerido'))

            if action in ['add', 'edit']:
                if not name:
                    return bad_json(message=_('name es requerido'))
                if not ip:
                    return bad_json(message=_('ip es requerido'))
                if Host.objects.exclude(id=host_id).filter(ip=ip).exists():
                    return bad_json(message=_('La IP está siendo usada por otro host'))

            if action == 'add':
                Host.objects.create(name=name, ip=ip)
                suffix = _('creado')

            elif action == 'edit':
                host = Host.objects.get(id=host_id)
                host.name = name
                host.ip = ip
                host.save()
                suffix = _('actualizado')

            else:
                host = Host.objects.get(id=host_id)
                host.delete()
                suffix = _('borrado')

            time.sleep(1)
            return ok_json(data={'message': _('Host exitosamente') + f' {suffix}'})

    except Exception as ex:
        print(ex.__str__())
        return bad_json(message=ex.__str__())


@login_required()
def sensors(request):
    data = {'title': _('Sensores')}
    add_global_data(request, data)
    data['sensors'] = Sensor.objects.all()
    data['data_sensors'] = DataSensor.objects.order_by('-data_datetime')
    return render(request, 'sensors.html', data)


@login_required()
def sensor_update_name(request, sensor_id):
    data = {'title': _('Sensor - Actualizar Nombre')}
    add_global_data(request, data)
    try:
        sensor = Sensor.objects.get(id=sensor_id)
        sensor.name = request.POST.get('name', '')
        sensor.save()
        return ok_json()

    except Exception as ex:
        print(ex.__str__())
        return bad_json(message=ex.__str__())


@login_required()
def check_new_sensor(request):
    data = {'title': _('Sensor - Comprobar Nuevo')}
    add_global_data(request, data)
    if Sensor.objects.filter(is_new=True).exists():
        return ok_json()
    return bad_json(error=7)


@login_required()
def users(request):
    data = {'title': _('Usuarios')}
    add_global_data(request, data)
    data['users'] = User.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if not action:
            return bad_json(message=_('action es requerido'))

        try:
            with transaction.atomic():

                user_id = int(request.POST.get('id'))
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                username = request.POST.get('username')
                password = request.POST.get('password')

                if action in ['edit', 'delete']:
                    if not user_id:
                        return bad_json(message=_('user_id es requerido'))

                if action in ['add', 'edit']:
                    if not first_name:
                        return bad_json(message=_('first_name es requerido'))
                    if not last_name:
                        return bad_json(message=_('last_name es requerido'))
                    if not username:
                        return bad_json(message=_('username es requerido'))
                    if not password:
                        return bad_json(message=_('password es requerido'))
                    if User.objects.exclude(id=user_id).filter(username=username).exists():
                        return bad_json(message=_('El nombre de usuario es usado por otro usuario'))

                if action == 'add':
                    user = User(
                        username=username,
                        first_name=first_name,
                        last_name=last_name
                    )
                    user.set_password(password)
                    user.save()
                    suffix = _('creado')
                    suffix = _('creado')

                elif action == 'edit':
                    user = User.objects.get(id=user_id)
                    user.username = username
                    user.first_name = first_name
                    user.last_name = last_name
                    user.set_password(password)
                    user.save()
                    suffix = _('actualizado')

                else:
                    user = User.objects.get(id=user_id)
                    user.delete()
                    suffix = _('borrado')

                time.sleep(1)
                return ok_json(data={'message': _('Usuario satisfactoriamente') + f' {suffix}'})

        except Exception as ex:
            print(ex.__str__())
            return bad_json(message=ex.__str__())

    return render(request, 'users.html', data)
