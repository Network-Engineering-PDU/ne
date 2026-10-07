from django.test import SimpleTestCase

from app import minew_scanner as m

# Real advertisements from the BeaconX Pro (DC:B3:47:7E:FA:23), captured from the PDU
TH_FRAME = bytes.fromhex("70 00 0a 01 0e 02 22 0b 3c 03 dc b3 47 7e fa 23".replace(" ", ""))
TLM_FRAME = bytes.fromhex("20 00 0b 3c 19 00 00 00 03 49 00 00 1e 74".replace(" ", ""))
DEVICE_INFO_FRAME = bytes.fromhex("40bf0a0b3500" "03dcb3477efa23" "0020")


class MokoParserTests(SimpleTestCase):
    def test_th_frame_gives_temperature_and_humidity(self):
        parsed = m._parse_moko(TH_FRAME)
        self.assertEqual(26.6, parsed["temperature_c"])
        self.assertEqual(52.6, parsed["humidity_pct"])
        self.assertNotIn("battery_mv", parsed)

    def test_tlm_frame_gives_battery_and_chip_temperature(self):
        parsed = m._parse_moko(TLM_FRAME)
        self.assertEqual(2876, parsed["battery_mv"])   # app showed 2874 mV
        self.assertEqual(25.0, parsed["chip_temperature_c"])  # app showed 25.0 °C
        self.assertNotIn("temperature_c", parsed)
        self.assertNotIn("humidity_pct", parsed)

    def test_device_info_frame_has_no_measurements(self):
        parsed = m._parse_moko(DEVICE_INFO_FRAME)
        self.assertEqual({"device_name": "BeaconX Pro"}, parsed)

    def test_unknown_or_empty_frames_are_ignored(self):
        self.assertEqual({"device_name": "BeaconX Pro"}, m._parse_moko(b""))
        self.assertEqual({"device_name": "BeaconX Pro"}, m._parse_moko(bytes.fromhex("60000000")))

    def test_negative_temperature(self):
        # 0xFFF6 = -10 in 0.1 degree units -> -1.0 C; 0x0222 = 546 -> 54.6 %
        frame = bytes.fromhex("7000" "f6ff" "2202")
        parsed = m._parse_moko(frame)
        self.assertEqual(-1.0, parsed["temperature_c"])
        self.assertEqual(54.6, parsed["humidity_pct"])


class MokoScannerIntegrationTests(SimpleTestCase):
    def setUp(self):
        m._live_cache.clear()
        m._monitored.clear()
        m._monitored["DCB3477EFA23"] = "MOKO"

    def props(self, frame):
        return {
            "Address": "DC:B3:47:7E:FA:23",
            "RSSI": -60,
            "ServiceData": {"0000feab-0000-1000-8000-00805f9b34fb": frame},
        }

    def test_th_and_tlm_frames_fill_the_live_cache(self):
        m._process_bluez_device("/org/bluez/hci0/dev_DC_B3_47_7E_FA_23", self.props(TH_FRAME))
        m._process_bluez_device("/org/bluez/hci0/dev_DC_B3_47_7E_FA_23", self.props(TLM_FRAME))
        cache = m._live_cache["DCB3477EFA23"]
        self.assertEqual("MOKO", cache["kind"])
        self.assertEqual(26.6, cache["temperature_c"])
        self.assertEqual(52.6, cache["humidity_pct"])
        self.assertEqual(2876, cache["battery_mv"])

    def test_saved_row_uses_the_same_units_as_minew(self):
        m._process_bluez_device("/org/bluez/hci0/dev_DC_B3_47_7E_FA_23", self.props(TH_FRAME))
        row = m._reading_from_cache("DCB3477EFA23")
        self.assertEqual(2660, row["temperature"])   # stored as hundredths of a degree
        self.assertEqual(53, row["humidity"])         # whole percent, as for MINEW


class MokoBatteryFrameTests(SimpleTestCase):
    """The battery (TLM) frame comes under the Eddystone UUID, not feab."""

    def test_battery_is_read_from_the_feaa_frame(self):
        from app import minew_scanner as m
        th = bytes.fromhex('70000a01060230 0b4503dcb3477efa23'.replace(' ', ''))
        tlm = bytes.fromhex('2000 0b4517800000 2d99 0000f204'.replace(' ', ''))
        props = {'ServiceData': {
            '0000feab-0000-1000-8000-00805f9b34fb': th,
            '0000feaa-0000-1000-8000-00805f9b34fb': tlm}}
        self.assertEqual(tlm, m._moko_tlm_props(props))
        parsed = m._parse_moko(th)
        parsed.update(m._parse_moko(m._moko_tlm_props(props)))
        self.assertEqual(2885, parsed['battery_mv'])
        self.assertEqual(26.6, parsed['temperature_c'])


class MokoTlmOnlyTests(SimpleTestCase):
    """BlueZ may show only the battery frame for a BeaconX; it must still be found."""

    def test_tlm_only_advert_is_recognised_as_moko(self):
        from app import minew_scanner as m
        tlm = bytes.fromhex('2000 0b4517800000 2e c3 00 00 f7 d6'.replace(' ', ''))
        props = {'Address': 'DC:B3:47:7E:FA:23', 'RSSI': -46, 'ServiceData': {
            '0000feaa-0000-1000-8000-00805f9b34fb': tlm}}
        m._process_bluez_device('/org/bluez/hci0/dev_DC_B3_47_7E_FA_23', props)
        found = [d for d in m._discovered.values() if d['mac'] == 'DC:B3:47:7E:FA:23']
        self.assertEqual([], found)  # only collected during a scan
        m._scanning = True
        try:
            m._process_bluez_device('/org/bluez/hci0/dev_DC_B3_47_7E_FA_23', props)
            found = [d for d in m._discovered.values() if d['mac'] == 'DC:B3:47:7E:FA:23']
            self.assertEqual('MOKO', found[0]['kind'])
            self.assertEqual(2885, found[0]['battery_mv'])
        finally:
            m._scanning = False
            m._discovered.clear()

    def test_other_eddystone_frames_are_not_moko(self):
        from app import minew_scanner as m
        uid = bytes.fromhex('00e3 12345678901234567890 0000 00000000'.replace(' ', ''))
        self.assertIsNone(m._moko_tlm_props({'ServiceData': {
            '0000feaa-0000-1000-8000-00805f9b34fb': uid}}))
