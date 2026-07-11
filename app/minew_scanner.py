"""
Minew MST01 / BeaconX Pro BLE discovery and live monitoring for the sensors screen.

Used by REST /api/sensors-scan/* and pushes readings for confirmed sensors.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.sensor_ble_service import format_mac_display, normalize_mac, save_sensor_readings

try:
    import dbus
    BLUEZ_AVAILABLE = True
except ImportError:
    dbus = None  # type: ignore
    BLUEZ_AVAILABLE = False

BLUEZ_SERVICE = 'org.bluez'
ADAPTER_IFACE = 'org.bluez.Adapter1'
DEVICE_IFACE = 'org.bluez.Device1'
PROPS_IFACE = 'org.freedesktop.DBus.Properties'
OBJ_MGR_IFACE = 'org.freedesktop.DBus.ObjectManager'

MINEW_COMPANY_ID = 0x0639
BEACONX_UUID_KEY = 'feab'
FRAME_MARKER = 0xCA
CA05_FRAME = 0x05
CA00_FRAME = 0x00
MST01_NAME_BYTES = b'MST01'
N_INDOOR = 2.7
N_OPEN = 2.0

SCAN_DURATION_SEC = 60
PUSH_INTERVAL_SEC = 3
BLUEZ_POLL_INTERVAL_SEC = 0.5

_lock = threading.Lock()
_scanning = False
_discovered: Dict[str, dict] = {}
_monitored: Dict[str, str] = {}  # normalized mac -> kind
_live_cache: Dict[str, dict] = {}
_ble_stop = threading.Event()
_ble_thread: Optional[threading.Thread] = None
_monitored_loaded = False
_last_error = ''


def _distance(rssi: int, tx_1m: int = -65) -> dict:
    diff = tx_1m - rssi
    return {
        'open_m': round(10 ** (diff / (10 * N_OPEN)), 2),
        'indoor_m': round(10 ** (diff / (10 * N_INDOOR)), 2),
    }


def _parse_ca05(payload: bytes) -> Optional[dict]:
    if len(payload) < 14:
        return None
    temp_c = payload[5] + payload[6] / 256
    hum_pct = payload[7] + payload[8] / 256
    name = payload[9:14].decode('ascii', errors='replace').rstrip('\x00')
    return {
        'temperature_c': round(temp_c, 2),
        'humidity_pct': round(hum_pct, 1),
        'device_name': name,
    }


def _parse_ca00(payload: bytes) -> Optional[dict]:
    if len(payload) < 9:
        return None
    return {
        'battery_pct': payload[8],
        'battery_mv': payload[3] * 100,
    }


def _parse_mst01(mfr: bytes) -> Optional[dict]:
    if len(mfr) < 2 or mfr[0] != FRAME_MARKER:
        return None
    if mfr[1] == CA05_FRAME:
        return _parse_ca05(mfr)
    if mfr[1] == CA00_FRAME:
        return _parse_ca00(mfr)
    return None


def _parse_beaconx(svc: bytes, rssi: int) -> dict:
    result = {'device_name': 'BeaconX Pro'}
    if len(svc) < 2:
        return result

    frame_type = svc[0]
    tx_power = svc[1] - 256 if svc[1] > 127 else svc[1]
    result['tx_power_dbm'] = tx_power
    result['distance'] = _distance(rssi, tx_power)

    if frame_type == 0x40 and len(svc) >= 13:
        result['beacon_frame'] = 'iBeacon'
        result['major'] = int.from_bytes(svc[2:4], 'big')
        result['minor'] = int.from_bytes(svc[4:6], 'big')
    elif frame_type == 0x60 and len(svc) >= 6:
        result['beacon_frame'] = 'TH'
        temp_raw = int.from_bytes(svc[2:4], 'little', signed=True)
        hum_raw = int.from_bytes(svc[4:6], 'little', signed=True)
        result['temperature_c'] = round(temp_raw / 100, 2)
        result['humidity_pct'] = round(hum_raw / 100, 1)
    elif frame_type == 0x70 and len(svc) >= 8:
        result['beacon_frame'] = 'ENV'
        temp_raw = int.from_bytes(svc[2:4], 'little', signed=True)
        hum_raw = int.from_bytes(svc[4:6], 'little', signed=True)
        press_raw = int.from_bytes(svc[6:8], 'little', signed=False)
        result['temperature_c'] = round(temp_raw / 100, 2)
        result['humidity_pct'] = round(hum_raw / 100, 1)
        result['pressure_hpa'] = round(press_raw / 10, 1)
    else:
        result['beacon_frame'] = f'0x{frame_type:02x}'

    return result


def _dbus_bytes(value) -> bytes:
    if value is None:
        return b''
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    return bytes(int(x) & 0xFF for x in value)


def _manufacturer_data(props: dict) -> Dict[int, bytes]:
    raw = props.get('ManufacturerData', {}) or {}
    return {int(k): _dbus_bytes(v) for k, v in raw.items()}


def _service_data(props: dict) -> Dict[str, bytes]:
    raw = props.get('ServiceData', {}) or {}
    return {str(k).lower(): _dbus_bytes(v) for k, v in raw.items()}


def _mac_from_path(path: str) -> str:
    tail = str(path).split('/')[-1]
    if tail.startswith('dev_'):
        return tail[4:].replace('_', ':').upper()
    return tail.upper()


def _is_beaconx_props(props: dict) -> Optional[bytes]:
    for uuid_str, data in _service_data(props).items():
        if BEACONX_UUID_KEY in uuid_str.lower():
            return data
    return None


def _is_mst01_props(props: dict) -> Optional[bytes]:
    raw = _manufacturer_data(props).get(MINEW_COMPANY_ID)
    if raw and len(raw) >= 9 and raw[0] == FRAME_MARKER:
        if raw[1] == CA00_FRAME:
            return raw
        if raw[1] == CA05_FRAME and len(raw) >= 14:
            if MST01_NAME_BYTES in raw[9:14]:
                return raw
            return raw
    return None


def _bluez_exception_text(ex: Exception) -> str:
    if dbus is not None and isinstance(ex, dbus.exceptions.DBusException):
        return ex.get_dbus_message() or str(ex)
    return str(ex)


def _get_bluez_adapter(bus) -> Tuple[str, object]:
    obj_mgr = dbus.Interface(bus.get_object(BLUEZ_SERVICE, '/'), OBJ_MGR_IFACE)
    objects = obj_mgr.GetManagedObjects()
    for path, ifaces in objects.items():
        if ADAPTER_IFACE in ifaces and str(path).endswith('/hci0'):
            return str(path), dbus.Interface(
                bus.get_object(BLUEZ_SERVICE, path), ADAPTER_IFACE
            )
    for path, ifaces in objects.items():
        if ADAPTER_IFACE in ifaces:
            return str(path), dbus.Interface(
                bus.get_object(BLUEZ_SERVICE, path), ADAPTER_IFACE
            )
    raise RuntimeError('No BlueZ Bluetooth adapter found')


def _power_adapter_on(bus, adapter_path: str) -> None:
    props = dbus.Interface(bus.get_object(BLUEZ_SERVICE, adapter_path), PROPS_IFACE)
    if not bool(props.Get(ADAPTER_IFACE, 'Powered')):
        props.Set(ADAPTER_IFACE, 'Powered', dbus.Boolean(True))


def _start_discovery(adapter) -> None:
    try:
        adapter.SetDiscoveryFilter({
            'Transport': dbus.String('le'),
            'DuplicateData': dbus.Boolean(True),
        })
    except Exception as ex:
        print(f'minew bluez discovery filter warning: {_bluez_exception_text(ex)}')
    try:
        adapter.StartDiscovery()
    except Exception as ex:
        msg = _bluez_exception_text(ex)
        if 'InProgress' not in msg and 'Operation already in progress' not in msg:
            raise


def _stop_discovery(adapter) -> None:
    try:
        adapter.StopDiscovery()
    except Exception:
        pass


def _process_bluez_device(path: str, props: dict) -> None:
    mac = normalize_mac(str(props.get('Address') or _mac_from_path(path)))
    if not mac:
        return

    try:
        rssi = int(props.get('RSSI', -999))
    except (TypeError, ValueError):
        rssi = -999

    kind = None
    parsed = None
    raw = _is_mst01_props(props)
    if raw:
        kind = 'MST01'
        parsed = _parse_mst01(raw)
    else:
        svc = _is_beaconx_props(props)
        if svc:
            kind = 'BeaconX'
            parsed = _parse_beaconx(svc, rssi)

    if not kind:
        return

    name = (parsed or {}).get('device_name', kind)
    entry = {
        'mac': format_mac_display(mac),
        'mac_normalized': mac,
        'kind': kind,
        'rssi': rssi,
        'name': name,
        'last_seen': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    }
    if parsed:
        entry.update(parsed)

    with _lock:
        if _scanning:
            prev = _discovered.get(mac, {})
            prev.update(entry)
            _discovered[mac] = prev

        if mac in _monitored:
            cache = _live_cache.setdefault(mac, {'kind': kind})
            cache.update(entry)
            cache['rssi'] = rssi
            cache['last_seen'] = entry['last_seen']
            if parsed:
                cache.update(parsed)


def _poll_bluez_devices(bus) -> None:
    obj_mgr = dbus.Interface(bus.get_object(BLUEZ_SERVICE, '/'), OBJ_MGR_IFACE)
    objects = obj_mgr.GetManagedObjects()
    for path, ifaces in objects.items():
        props = ifaces.get(DEVICE_IFACE)
        if props:
            _process_bluez_device(str(path), dict(props))


def _run_bluez_loop() -> None:
    global _scanning, _last_error

    if not BLUEZ_AVAILABLE:
        _last_error = 'python3-dbus is not installed on this host'
        time.sleep(5)
        return

    bus = dbus.SystemBus()
    adapter_path, adapter = _get_bluez_adapter(bus)
    _power_adapter_on(bus, adapter_path)
    _start_discovery(adapter)
    _last_error = ''

    try:
        scan_started_at = time.monotonic()
        last_push_at = time.monotonic()
        while not _ble_stop.is_set():
            _poll_bluez_devices(bus)
            now = time.monotonic()
            with _lock:
                scanning = _scanning
                has_monitored = bool(_monitored)

            if scanning:
                if now - scan_started_at >= SCAN_DURATION_SEC:
                    with _lock:
                        _scanning = False
                    scan_started_at = now
            else:
                scan_started_at = now

            if has_monitored and not scanning:
                if now - last_push_at >= PUSH_INTERVAL_SEC:
                    _push_monitored_readings()
                    last_push_at = now

            time.sleep(BLUEZ_POLL_INTERVAL_SEC)
    finally:
        _stop_discovery(adapter)


def _reading_from_cache(mac: str) -> Optional[dict]:
    with _lock:
        cache = _live_cache.get(mac)
        if not cache:
            return None
        data = dict(cache)

    dt_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    out = {
        'mac_address': mac,
        'datetime': dt_str,
        'rssi': data.get('rssi'),
    }
    temp = data.get('temperature_c')
    if temp is not None:
        out['temperature'] = int(round(temp * 100))
    hum = data.get('humidity_pct')
    if hum is not None:
        out['humidity'] = int(round(hum))
    press = data.get('pressure_hpa')
    if press is not None:
        out['pressure'] = int(round(press * 100))
    bat = data.get('battery_mv')
    if bat is not None:
        out['battery'] = int(bat)
    if (out.get('temperature') is None and out.get('humidity') is None and
            out.get('pressure') is None and out.get('battery') is None and
            out.get('rssi') is None):
        return None
    return out


def _push_monitored_readings() -> None:
    readings = []
    with _lock:
        macs = list(_monitored.keys())
    for mac in macs:
        row = _reading_from_cache(mac)
        if row:
            readings.append(row)
    if readings:
        save_sensor_readings(readings)


def _ble_worker() -> None:
    global _last_error
    while not _ble_stop.is_set():
        try:
            _run_bluez_loop()
        except Exception as ex:
            _last_error = _bluez_exception_text(ex)
            print(f'minew bluez loop error: {_last_error}')
            time.sleep(5)


def _bluez_ready_detail() -> Tuple[bool, str]:
    if not BLUEZ_AVAILABLE:
        return False, 'python3-dbus is not installed on this host'
    try:
        bus = dbus.SystemBus()
        adapter_path, adapter = _get_bluez_adapter(bus)
        _power_adapter_on(bus, adapter_path)
        return True, f'BlueZ adapter ready: {adapter_path}'
    except Exception as ex:
        return False, _bluez_exception_text(ex)


def _ensure_ble_thread() -> None:
    global _ble_thread
    if _ble_thread and _ble_thread.is_alive():
        return
    _ble_stop.clear()
    _ble_thread = threading.Thread(target=_ble_worker, daemon=True, name='minew-ble')
    _ble_thread.start()


def _ensure_monitored_loaded() -> None:
    global _monitored_loaded
    if _monitored_loaded:
        return
    _monitored_loaded = True
    try:
        from app.models import Sensor

        with _lock:
            for sensor in Sensor.objects.all():
                mac = normalize_mac(sensor.mac_address)
                if not mac:
                    continue
                name = sensor.name or 'BLE'
                upper = name.upper()
                if 'BEACON' in upper:
                    kind = 'BeaconX'
                elif 'MST' in upper:
                    kind = 'MST01'
                else:
                    kind = 'BLE'
                _monitored[mac] = kind
                _live_cache.setdefault(mac, {
                    'kind': kind,
                    'name': name,
                    'mac': format_mac_display(mac),
                })
        if _monitored:
            _ensure_ble_thread()
    except Exception as ex:
        print(f'minew load monitored error: {ex}')


def start_scan() -> dict:
    global _scanning
    ok, detail = _bluez_ready_detail()
    if not ok:
        return {'ok': False, 'detail': detail}
    _ensure_monitored_loaded()
    _ensure_ble_thread()
    with _lock:
        _discovered.clear()
        _scanning = True
    return {'ok': True, 'detail': 'scan started', 'duration_sec': SCAN_DURATION_SEC}


def stop_scan() -> dict:
    global _scanning
    with _lock:
        _scanning = False
    return {'ok': True, 'detail': 'scan stopped'}


def get_scan_status() -> dict:
    _ensure_monitored_loaded()
    with _lock:
        devices = sorted(_discovered.values(), key=lambda d: d.get('rssi', -999), reverse=True)
        return {
            'scanning': _scanning,
            'bluez_available': BLUEZ_AVAILABLE,
            'last_error': _last_error,
            'devices': [
                {
                    'mac': d['mac'],
                    'kind': d['kind'],
                    'rssi': d.get('rssi'),
                    'name': d.get('name', d['kind']),
                    'temperature_c': d.get('temperature_c'),
                    'humidity_pct': d.get('humidity_pct'),
                }
                for d in devices
            ],
        }


def get_live_readings(mac: Optional[str] = None) -> dict:
    _ensure_monitored_loaded()
    if _monitored:
        _ensure_ble_thread()
    target = normalize_mac(mac) if mac else None
    with _lock:
        devices = []
        for norm_mac, kind in _monitored.items():
            if target and norm_mac != target:
                continue
            cache = _live_cache.get(norm_mac, {})
            devices.append({
                'mac': cache.get('mac', format_mac_display(norm_mac)),
                'mac_normalized': norm_mac,
                'kind': cache.get('kind', kind),
                'name': cache.get('name', kind),
                'rssi': cache.get('rssi'),
                'temperature_c': cache.get('temperature_c'),
                'humidity_pct': cache.get('humidity_pct'),
                'pressure_hpa': cache.get('pressure_hpa'),
                'battery_mv': cache.get('battery_mv'),
                'battery_pct': cache.get('battery_pct'),
                'last_seen': cache.get('last_seen'),
            })
    return {
        'bluez_available': BLUEZ_AVAILABLE,
        'last_error': _last_error,
        'monitoring': len(_monitored),
        'devices': devices,
    }


def confirm_sensors(macs: Optional[List[str]] = None, add_all: bool = False) -> dict:
    global _scanning
    from app.models import Sensor

    _ensure_monitored_loaded()
    with _lock:
        if add_all:
            targets = list(_discovered.keys())
        elif macs:
            targets = [normalize_mac(m) for m in macs]
        else:
            targets = []
        discovered = dict(_discovered)
        _scanning = False

    added = []
    for mac in targets:
        info = discovered.get(mac)
        if not info:
            continue
        kind = info.get('kind', 'BLE')
        name = info.get('name') or kind
        sensor, created = Sensor.objects.get_or_create(mac_address=mac)
        if created or not sensor.name:
            sensor.name = name
        sensor.is_new = False
        sensor.save()
        with _lock:
            _monitored[mac] = kind
            _live_cache[mac] = dict(info)
        added.append(format_mac_display(mac))

    if added:
        _ensure_ble_thread()
        _push_monitored_readings()

    return {'ok': True, 'added': added, 'count': len(added)}
