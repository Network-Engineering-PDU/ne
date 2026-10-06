from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from app.inputs_layout import build_layout


def sw(branch, sys_type, curr_type=0):
    return {"branch": branch, "sys_type": sys_type, "curr_type": curr_type}


class LayoutRulesTests(TestCase):
    def line_ids(self, layout):
        return [[p["line_id"] for p in b["phases"]] for b in layout["branches"]]

    def test_single_phase_main_shows_one_input(self):
        layout = build_layout(sw(0, 0))
        self.assertEqual([[1]], self.line_ids(layout))
        self.assertEqual([1], layout["active_line_ids"])
        self.assertEqual("L1", layout["branches"][0]["phases"][0]["label"])

    def test_bi_phase_main_shows_two_inputs(self):
        self.assertEqual([[1, 2]], self.line_ids(build_layout(sw(0, 1))))

    def test_three_phase_main_shows_three_inputs(self):
        layout = build_layout(sw(0, 2))
        self.assertEqual([[1, 2, 3]], self.line_ids(layout))
        self.assertEqual(["L1", "L2", "L3"], [p["label"] for p in layout["branches"][0]["phases"]])

    def test_three_phase_with_neutral_has_no_extra_input(self):
        # Neutral is not measured separately; same three phase inputs as without
        self.assertEqual([[1, 2, 3]], self.line_ids(build_layout(sw(0, 3))))

    def test_main_and_aux_numbers_inputs_branch_by_branch(self):
        layout = build_layout(sw(1, 2))
        self.assertEqual([[1, 2, 3], [4, 5, 6]], self.line_ids(layout))
        self.assertEqual(["Main branch", "Aux branch"], [b["name"] for b in layout["branches"]])
        self.assertEqual([1, 2, 3, 4, 5, 6], layout["active_line_ids"])

    def test_main_and_aux_single_phase_uses_two_inputs(self):
        self.assertEqual([[1], [2]], self.line_ids(build_layout(sw(1, 0))))

    def test_labels_describe_the_selected_configuration(self):
        layout = build_layout(sw(1, 3, 1))
        self.assertEqual("Three-phase with neutral", layout["type_label"])
        self.assertEqual("Current transformer", layout["current_type_label"])
        self.assertEqual("Main and aux branches", layout["branch_label"])

    def test_unknown_or_missing_switches_give_no_layout(self):
        self.assertIsNone(build_layout(None))
        self.assertIsNone(build_layout({"branch": 0}))
        self.assertIsNone(build_layout(sw(3, 0)))
        self.assertIsNone(build_layout(sw(0, 9)))


class InputsEndpointTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("inputs", password="x"))

    @patch("app.views.get_pdu_input_data", return_value=None)
    @patch("app.views.get_pdu_local_data", return_value={"branch": 0, "sys_type": 0, "curr_type": 0})
    def test_live_endpoint_returns_the_layout_for_the_switches(self, _local, _input):
        r = self.client.get(reverse("get_inputs_live_data"))
        self.assertEqual(200, r.status_code)
        layout = r.json()["layout"]
        self.assertEqual([1], layout["active_line_ids"])

    @patch("app.views.get_pdu_input_data", return_value=None)
    @patch("app.views.get_pdu_local_data", return_value=None)
    def test_live_endpoint_without_pdu_reports_no_layout(self, _local, _input):
        r = self.client.get(reverse("get_inputs_live_data"))
        self.assertIsNone(r.json()["layout"])

    @patch("app.views.get_pdu_local_data", return_value={"branch": 1, "sys_type": 1, "curr_type": 0})
    def test_page_renders_the_layout_as_json(self, _local):
        html = self.client.get(reverse("inputs")).content.decode()
        self.assertIn('id="initialLayout"', html)
        self.assertIn("Aux branch", html)
        self.assertNotIn('id="tabInputs"', html)
