"""
Minew MST01 / BeaconX Pro BLE discovery and monitoring for the NE sensors screen.

Used by REST /api/sensors-scan/* and pushes live data for confirmed sensors.
"""
from __future__ import annotations

import asyncio
import re
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from app.sensor_ble_service import format_mac_display, normalize_mac, save_sensor_readings

try:
    from bleak import BleakScanner
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    BLEDevice = object  # type: ignore
    AdvertisementData = object  # type: ignore

MINEW_COMPANY_ID = 0x0639
BEACONX_UUID_KEY = 'feab'
FRAME_MARKER = 0xCA
CA05_FRAME = 0x05
CA00_FRAME = 0x00
MST01_NAME_BYTES = b'MST01'

SCAN_DURATION_SEC = 60
PUSH_INTERVAL_SEC = 10

_lock = threading.Lock()
_scanning = False
_discovered: Dict[str, dict] = {}
_monitored: Dict[str, str] = {}  # normalized mac -> kind
_live_cache: Dict[str, dict] = {}
_monitor_stop = threading.Event()
_scan_stop = threading.Event()
_scan_thread: Optional[threading.Thread] = None
_monitor_thread: Optional[threading.Thread] = None


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


def _parse_beaconx(svc: bytes) -> dict:
    result = {'device_name': 'BeaconX Pro'}
    if len(svc) < 2:
        return result
    frame_type = svc[0]
    if frame_type == 0x60 and len(svc) >= 6:
        temp_raw = int.from_bytes(svc[2:4], 'little', signed=True)
        hum_raw = int.from_bytes(svc[4:6], 'little', signed=True)
        result['temperature_c'] = round(temp_raw / 100, 2)
        result['humidity_pct'] = round(hum_raw / 100, 1)
    elif frame_type == 0x70 and len(svc) >= 8:
        temp_raw = int.from_bytes(svc[2:4], 'little', signed=True)
        hum_raw = int.from_bytes(svc[4:6], 'little', signed=True)
        press_raw = int.from_bytes(svc[6:8], 'little', signed=False)
        result['temperature_c'] = round(temp_raw / 100, 2)
        result['humidity_pct'] = round(hum_raw / 100, 1)
        result['pressure_hpa'] = round(press_raw / 10, 1)
    return result


def _is_beaconx(adv: AdvertisementData) -> Optional[bytes]:
    for uuid_str, data in adv.service_data.items():
        if BEACONX_UUID_KEY in uuid_str.lower():
            return data
    return None


def _is_mst01(adv: AdvertisementData) -> Optional[bytes]:
    raw = adv.manufacturer_data.get(MINEW_COMPANY_ID)
    if raw and len(raw) >= 14 and raw[0] == FRAME_MARKER:
        if raw[1] == CA00_FRAME or (
            raw[1] == CA05_FRAME and MST01_NAME_BYTES in raw[9:14]
        ):
            return raw
    return None


def _advert_cb(device: BLEDevice, adv: AdvertisementData) -> None:
    mac = normalize_mac(device.address)
    if not mac:
        return

    kind = None
    parsed = None
    raw = _is_mst01(adv)
    if raw:
        kind = 'MST01'
        parsed = _parse_mst01(raw)
    else:
        svc = _is_beaconx(adv)
        if svc:
            kind = 'BeaconX'
            parsed = _parse_beaconx(svc)

    if not kind:
        return

    name = (parsed or {}).get('device_name', kind)
    entry = {
        'mac': format_mac_display(mac),
        'mac_normalized': mac,
        'kind': kind,
        'rssi': adv.rssi,
        'name': name,
    }
    if parsed:
        entry.update(parsed)

    with _lock:
        prev = _discovered.get(mac, {})
        prev.update(entry)
        _discovered[mac] = prev
        if mac in _monitored:
            cache = _live_cache.setdefault(mac, {'kind': kind})
            cache.update(entry)
            cache['rssi'] = adv.rssi
            if parsed:
                cache.update(parsed)


def _reading_from_cache(mac: str) -> Optional[dict]:
    with _lock:
        cache = _live_cache.get(mac)
        if not cache:
            return None
        data = dict(cache)

    dt_str = datetime.now().strftime('%d/%m/%Y %H:%M')
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


async def _run_scan_loop() -> None:
    global _scanning
    if not BLEAK_AVAILABLE:
        return
    scanner = BleakScanner(_advert_cb)
    await scanner.start()
    try:
        for _ in range(SCAN_DURATION_SEC):
            if _scan_stop.is_set():
                break
            await asyncio.sleep(1)
    finally:
        await scanner.stop()
        with _lock:
            _scanning = False


def _scan_worker() -> None:
    try:
        asyncio.run(_run_scan_loop())
    except Exception as ex:
        print(f'minew scan error: {ex}')
        with _lock:
            global _scanning
            _scanning = False


async def _run_monitor_loop() -> None:
    if not BLEAK_AVAILABLE:
        return
    scanner = BleakScanner(_advert_cb)
    await scanner.start()
    try:
        ticks = 0
        while not _monitor_stop.is_set():
            with _lock:
                if _scanning or not _monitored:
                    await asyncio.sleep(0.5)
                    continue
            ticks += 1
            if ticks >= PUSH_INTERVAL_SEC:
                _push_monitored_readings()
                ticks = 0
            await asyncio.sleep(1)
    finally:
        await scanner.stop()


def _monitor_worker() -> None:
    while not _monitor_stop.is_set():
        with _lock:
            active = bool(_monitored) and not _scanning
        if not active:
            time.sleep(1)
            continue
        try:
            asyncio.run(_run_monitor_loop())
        except Exception as ex:
            print(f'minew monitor error: {ex}')
            time.sleep(5)


def _ensure_monitor_thread() -> None:
    global _monitor_thread
    if _monitor_thread and _monitor_thread.is_alive():
        return
    _monitor_stop.clear()
    _monitor_thread = threading.Thread(target=_monitor_worker, daemon=True, name='minew-monitor')
    _monitor_thread.start()


def start_scan() -> dict:
    if not BLEAK_AVAILABLE:
        return {'ok': False, 'detail': 'bleak is not installed on this host'}
    global _scan_thread, _scanning
    stop_scan()
    with _lock:
        _discovered.clear()
        _scanning = True
    _scan_stop.clear()
    _scan_thread = threading.Thread(target=_scan_worker, daemon=True, name='minew-scan')
    _scan_thread.start()
    return {'ok': True, 'detail': 'scan started', 'duration_sec': SCAN_DURATION_SEC}


def stop_scan() -> dict:
    global _scanning
    _scan_stop.set()
    with _lock:
        _scanning = False
    return {'ok': True, 'detail': 'scan stopped'}


def get_scan_status() -> dict:
    with _lock:
        devices = sorted(_discovered.values(), key=lambda d: d.get('rssi', -999), reverse=True)
        return {
            'scanning': _scanning,
            'bleak_available': BLEAK_AVAILABLE,
            'devices': [
                {
                    'mac': d['mac'],
                    'kind': d['kind'],
                    'rssi': d.get('rssi'),
                    'name': d.get('name', d['kind']),
                }
                for d in devices
            ],
        }


def confirm_sensors(macs: Optional[List[str]] = None, add_all: bool = False) -> dict:
    from app.models import Sensor

    with _lock:
        if add_all:
            targets = list(_discovered.keys())
        elif macs:
            targets = [normalize_mac(m) for m in macs]
        else:
            targets = []
        discovered = dict(_discovered)

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
        _ensure_monitor_thread()
        _push_monitored_readings()

    return {'ok': True, 'added': added, 'count': len(added)}


def bleak_installed() -> bool:
    return BLEAK_AVAILABLE
