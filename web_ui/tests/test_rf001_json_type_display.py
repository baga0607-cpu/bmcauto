"""Offline JSON type display checks through RF-01-001 execution."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
import requests

source = Path(__file__).resolve().parents[2] / "test_assets/redfish/rf_01_001_version_discovery_endpoint.py"
spec = importlib.util.spec_from_file_location("rf001", source)
case = importlib.util.module_from_spec(spec)
spec.loader.exec_module(case)

class JsonTypeDisplayTest(unittest.TestCase):
    def run_body(self, raw, expected_status):
        context = {"redfish": {"host": "https://bmc.invalid"}}
        response = type("Response", (), {"status_code": 200, "headers": {}, "text": raw})()
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")), patch.object(requests.Session, "get", return_value=response), contextlib.redirect_stdout(io.StringIO()):
            if expected_status == "Pass":
                case.execute(None, context)
            else:
                with self.assertRaises(case.CaseFailure):
                    case.execute(None, context)
        self.assertEqual(context["case_result"]["status"], expected_status)
        return context["_method_results"]

    def test_json_types_and_unchanged_verdicts(self):
        for body, label in [({"v1": "/redfish/v1/"}, "Object (dict)"),
                            ([], "Array (list)"), ("text", "String (str)"),
                            (1, "Number (int)"), (1.5, "Number (float)"),
                            (True, "Boolean (bool)"), (False, "Boolean (bool)"),
                            (None, "Null (NoneType)")]:
            with self.subTest(label=label, body=body):
                passed = isinstance(body, dict)
                rows = self.run_body(json.dumps(body), "Pass" if passed else "Fail")
                self.assertEqual(rows[4]["expected"], "JSON Object")
                self.assertEqual(rows[4]["actual"], "JSON " + label)
                self.assertEqual(rows[4]["status"], "PASS" if passed else "FAIL")
                if not passed:
                    self.assertEqual(rows[5]["status"], "Skip")

    def test_object_type_pass_does_not_mask_property_failure(self):
        rows = self.run_body('{"v1":"/wrong"}', "Fail")
        self.assertEqual(rows[4]["status"], "PASS")
        self.assertEqual(rows[4]["actual"], "JSON Object (dict)")

    def test_invalid_json_keeps_parse_failure(self):
        rows = self.run_body('{broken', "Fail")
        self.assertEqual(rows[3]["status"], "FAIL")
        self.assertEqual(rows[4]["status"], "Skip")

if __name__ == "__main__":
    unittest.main(verbosity=2)
