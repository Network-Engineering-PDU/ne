from unittest.mock import patch

from django.test import SimpleTestCase

from app import minew_scanner as m


def row(temp=2150, hum=40, pres=101300, bat=2500, rssi=-60):
    return {'mac_address': 'AA', 'datetime': '01/01/2026 00:00:00', 'temperature': temp,
            'humidity': hum, 'pressure': pres, 'battery': bat, 'rssi': rssi}


class SaveRulesTests(SimpleTestCase):
    def setUp(self):
        m._last_saved.clear()

    def test_first_reading_is_saved(self):
        self.assertTrue(m._should_save('AA', row(), now=0))

    def test_unchanged_values_are_not_saved_again(self):
        m._last_saved['AA'] = (0, m._value_signature(row()))
        self.assertFalse(m._should_save('AA', row(), now=30))

    def test_changed_value_is_saved_after_the_minimum_gap(self):
        m._last_saved['AA'] = (0, m._value_signature(row()))
        self.assertFalse(m._should_save('AA', row(temp=2160), now=5))   # too soon
        self.assertTrue(m._should_save('AA', row(temp=2160), now=m.SAVE_MIN_GAP_SEC))

    def test_heartbeat_saves_steady_values(self):
        m._last_saved['AA'] = (0, m._value_signature(row()))
        self.assertFalse(m._should_save('AA', row(), now=m.SAVE_HEARTBEAT_SEC - 1))
        self.assertTrue(m._should_save('AA', row(), now=m.SAVE_HEARTBEAT_SEC))

    def test_rssi_change_alone_does_not_count_as_a_new_reading(self):
        m._last_saved['AA'] = (0, m._value_signature(row()))
        self.assertFalse(m._should_save('AA', row(rssi=-75), now=30))

    def test_push_saves_only_new_values(self):
        with patch.object(m, '_reading_from_cache', side_effect=[row(), row()]), \
             patch.object(m, '_monitored', {'AA': 'MST01'}), \
             patch.object(m, 'save_sensor_readings') as save, \
             patch.object(m.time, 'monotonic', return_value=100.0):
            m._push_monitored_readings()
            self.assertEqual(1, save.call_count)
        with patch.object(m, '_reading_from_cache', return_value=row()), \
             patch.object(m, '_monitored', {'AA': 'MST01'}), \
             patch.object(m, 'save_sensor_readings') as save, \
             patch.object(m.time, 'monotonic', return_value=130.0):
            m._push_monitored_readings()
            save.assert_not_called()
