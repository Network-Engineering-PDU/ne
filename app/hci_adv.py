"""Reads every Bluetooth LE advertising report straight from the controller.

BlueZ keeps only the service data of the latest advertisement for each device.
The MOKO temperature frame is replaced by the battery frame within a second, so
polling BlueZ misses most temperature frames. This module listens on a raw HCI
socket and sees every advertisement. It only receives: it sends no commands,
so BlueZ stays in control of scanning.
"""
import ctypes
import os
import select
import socket
import struct
from typing import Callable, Dict, Iterator

AF_BLUETOOTH = 31
BTPROTO_HCI = 1
SOL_HCI = 0
HCI_FILTER = 2
HCI_EVENT_PKT = 0x04
EVT_LE_META = 0x3E
EVT_LE_ADVERTISING_REPORT = 0x02
AD_SERVICE_DATA_16 = 0x16
AD_MANUFACTURER = 0xFF
# Same key format BlueZ uses, so the existing parser finds 'feab' / 'feaa' as before
UUID16_TAIL = '-0000-1000-8000-00805f9b34fb'


# The PDU's Python has no Bluetooth socket support, so the socket calls go through libc
_libc = ctypes.CDLL(None, use_errno=True)


class _SockaddrHci(ctypes.Structure):
    _fields_ = [('hci_family', ctypes.c_ushort),
                ('hci_dev', ctypes.c_ushort),
                ('hci_channel', ctypes.c_ushort)]


def open_listener(dev_id: int = 0) -> int:
    """Returns a file descriptor for the raw HCI socket. Close it with close_listener."""
    fd = _libc.socket(AF_BLUETOOTH, socket.SOCK_RAW, BTPROTO_HCI)
    if fd < 0:
        raise OSError(ctypes.get_errno(), 'socket(AF_BLUETOOTH) failed')
    # Only HCI event packets, and only LE Meta events
    flt = struct.pack('<IIIH', 1 << HCI_EVENT_PKT, 0, 1 << (EVT_LE_META - 32), 0)
    flt_buf = ctypes.create_string_buffer(flt, len(flt))
    addr = _SockaddrHci(AF_BLUETOOTH, dev_id, 0)
    if (_libc.setsockopt(fd, SOL_HCI, HCI_FILTER, flt_buf, len(flt)) != 0 or
            _libc.bind(fd, ctypes.byref(addr), ctypes.sizeof(addr)) != 0):
        err = ctypes.get_errno()
        os.close(fd)
        raise OSError(err, 'HCI socket setup failed')
    return fd


def close_listener(fd: int) -> None:
    os.close(fd)


def parse_ad_structures(data: bytes) -> tuple:
    service: Dict[str, bytes] = {}
    manufacturer: Dict[int, bytes] = {}
    i = 0
    while i < len(data):
        length = data[i]
        if length == 0 or i + 1 + length > len(data):
            break
        ad_type = data[i + 1]
        payload = data[i + 2:i + 1 + length]
        if ad_type == AD_SERVICE_DATA_16 and len(payload) >= 2:
            uuid = int.from_bytes(payload[0:2], 'little')
            service[f'0000{uuid:04x}{UUID16_TAIL}'] = payload[2:]
        elif ad_type == AD_MANUFACTURER and len(payload) >= 2:
            manufacturer[int.from_bytes(payload[0:2], 'little')] = payload[2:]
        i += 1 + length
    return service, manufacturer


def parse_le_reports(buf: bytes) -> Iterator[dict]:
    """Yields one props-style dict per advertising report in an HCI event packet."""
    if buf and buf[0] == HCI_EVENT_PKT:
        buf = buf[1:]
    if len(buf) < 4 or buf[0] != EVT_LE_META or buf[2] != EVT_LE_ADVERTISING_REPORT:
        return
    count = buf[3]
    pos = 4
    for _ in range(count):
        if pos + 10 > len(buf):
            return
        data_len = buf[pos + 8]
        if pos + 10 + data_len > len(buf):
            return
        address = buf[pos + 2:pos + 8]
        data = buf[pos + 9:pos + 9 + data_len]
        rssi = struct.unpack('b', buf[pos + 9 + data_len:pos + 10 + data_len])[0]
        pos += 10 + data_len
        service, manufacturer = parse_ad_structures(data)
        yield {
            'Address': ':'.join(f'{b:02X}' for b in reversed(address)),
            'RSSI': rssi,
            'ServiceData': service,
            'ManufacturerData': manufacturer,
        }


def listen(fd: int, on_report: Callable[[dict], None], stop_event) -> None:
    while not stop_event.is_set():
        ready, _, _ = select.select([fd], [], [], 1.0)
        if not ready:
            continue
        buf = os.read(fd, 512)
        for report in parse_le_reports(buf):
            on_report(report)
