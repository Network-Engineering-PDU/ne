import struct

from django.test import SimpleTestCase

from app import hci_adv
from app import minew_scanner as m

# Advertisement captured on the PDU with btmon: the BeaconX Pro's temperature frame
# (service data 0xfeab, 16 bytes) inside a 26-byte advertisement.
TH_PAYLOAD = bytes.fromhex('70000a00fc024d0b4703dcb3477efa23')
TLM_PAYLOAD = bytes.fromhex('20000b4716c000003ce900013e94')


def ad(ad_type, payload):
    return bytes([len(payload) + 1, ad_type]) + payload


def le_report_event(addr_hex, data, rssi):
    """Builds an HCI event packet with one LE Advertising Report, as the controller sends it."""
    address = bytes.fromhex(addr_hex.replace(':', ''))[::-1]  # on-air order is little-endian
    report = bytes([0x00, 0x01]) + address + bytes([len(data)]) + data + struct.pack('b', rssi)
    params = bytes([0x02, 0x01]) + report  # subevent, number of reports
    return bytes([0x04, 0x3E, len(params)]) + params


class HciAdvertisingTests(SimpleTestCase):
    def test_temperature_frame_is_read_from_the_advert(self):
        data = ad(0x01, b'\x06') + ad(0x16, b'\xab\xfe' + TH_PAYLOAD) + bytes([0x02, 0x0A, 0x00])
        self.assertEqual(26, len(data))
        reports = list(hci_adv.parse_le_reports(le_report_event('DC:B3:47:7E:FA:23', data, -46)))
        self.assertEqual(1, len(reports))
        r = reports[0]
        self.assertEqual('DC:B3:47:7E:FA:23', r['Address'])
        self.assertEqual(-46, r['RSSI'])
        self.assertEqual(TH_PAYLOAD, r['ServiceData']['0000feab-0000-1000-8000-00805f9b34fb'])

    def test_temperature_and_battery_adverts_both_reach_the_scanner(self):
        mac = 'DC:B3:47:7E:FA:23'
        m._monitored[m.normalize_mac(mac)] = 'MOKO'
        m._monitored_loaded = True
        try:
            th = ad(0x16, b'\xab\xfe' + TH_PAYLOAD)
            tlm = ad(0x16, b'\xaa\xfe' + TLM_PAYLOAD)
            for report in hci_adv.parse_le_reports(le_report_event(mac, th, -46)):
                m._process_bluez_device('', report)
            for report in hci_adv.parse_le_reports(le_report_event(mac, tlm, -46)):
                m._process_bluez_device('', report)
            cache = m._live_cache[m.normalize_mac(mac)]
            self.assertIn('temperature_c', cache)
            self.assertEqual(2887, cache['battery_mv'])  # from the battery frame
            # Captured frame: the phone app showed 25.2 C and 58.5 %RH at the same time
            self.assertEqual(25.2, cache['temperature_c'])
            self.assertEqual(58.9, cache['humidity_pct'])
        finally:
            m._monitored.pop(m.normalize_mac(mac), None)
            m._live_cache.pop(m.normalize_mac(mac), None)

    def test_truncated_event_is_ignored(self):
        self.assertEqual([], list(hci_adv.parse_le_reports(bytes([0x04, 0x3E, 0x05, 0x02, 0x01]))))
        self.assertEqual([], list(hci_adv.parse_le_reports(b'')))
