"""Offline contracts for RF-01-001/002 Step/Checkpoint/Record evidence."""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web_ui"))
from case_log import CaseLog
from report_case import method_rows

NAMES = ["rf_01_001_version_discovery_endpoint.py", "rf_01_002_service_root_endpoint.py"]
CASES = []
for index, name in enumerate(NAMES):
    spec = importlib.util.spec_from_file_location("scr_case_" + str(index), ROOT / "test_assets/redfish" / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    CASES.append(module)
GOOD = [{"v1": "/redfish/v1/"},
        {"@odata.type": "#ServiceRoot.v1_19_0.ServiceRoot", "@odata.id": "/redfish/v1/"}]


def response(body, status=200, headers=None):
    return type("Response", (), {"status_code": status, "headers": headers or {},
                                "text": body if isinstance(body, str) else json.dumps(body)})()


class MethodItemsTest(unittest.TestCase):
    def run_case(self, index, replies, expected="Pass", settings=None, old_log=False):
        module = CASES[index]
        output = io.StringIO()
        logger = CaseLog(output, lambda event: None)
        if old_log:
            logger.method_item = None
        context = {"log": logger, "redfish": settings if settings is not None else {
            "host": "https://bmc.invalid/base", "username": "synthetic", "password": "test",
            "verify_ssl": True}}
        calls = []

        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def get(self, url, **kwargs):
                calls.append((url, kwargs, self.trust_env, self.auth))
                reply = replies[len(calls) - 1]
                if isinstance(reply, Exception):
                    raise reply
                return reply

        with patch.object(socket.socket, "connect", side_effect=AssertionError("No network")), \
             patch.object(requests, "Session", Session):
            if expected == "Pass":
                module.execute(None, context)
            else:
                with self.assertRaises(module.CaseFailure if expected == "Fail" else RuntimeError):
                    module.execute(None, context)
        self.assertEqual(context["case_result"]["status"], expected)
        rows = [r for r in logger.records if r["kind"] == "step"]
        declared = module.TEST_CASE["test_method"]
        self.assertEqual([r["result"]["method_index"] for r in rows], list(range(len(declared))))
        self.assertEqual(len([r for r in logger.records if r["kind"] == "finish"]), 1)
        self.assertEqual(len(method_rows({"log_records": logger.records}, {})), len(declared))
        for row, definition in zip(rows, declared):
            self.assertEqual(row["result"]["step_number"], definition["step_number"])
            self.assertEqual(row["result"]["type"], definition["type"])
            self.assertIsNone(row["criteria"])
            if definition["type"] == "Record":
                self.assertNotIn(row["result"]["status"], ("PASS", "FAIL"))
                self.assertNotIn("expected", row["result"])
        json.dumps(logger.records, allow_nan=False)
        for url, kwargs, trust_env, auth in calls:
            self.assertTrue(url.startswith("https://bmc.invalid/"))
            self.assertEqual(kwargs, {"headers": {"Accept": "application/json"},
                                     "verify": True, "timeout": 15, "allow_redirects": False})
            self.assertFalse(trust_env)
            self.assertEqual(auth, ("synthetic", "test"))
        aliases = [["S1","C1","S2","C2a","C2b","S3","C3a","C3b","C3c"],["S1","C1","S2","C2a","C2b","S3","C3a","C3b","S4","C4a","C4b","S5","R5"]]
        return dict(zip(aliases[index], [r["result"] for r in rows])), context, output.getvalue(), calls

    def test_literal_metadata_and_report_fallback(self):
        for module in CASES:
            tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
            meta = ast.literal_eval(next(n.value for n in tree.body if isinstance(n, ast.Assign)
                                         and any(isinstance(t, ast.Name) and t.id == "TEST_CASE" for t in n.targets)))
            self.assertEqual(meta, json.loads(json.dumps(meta)))
            self.assertEqual(meta["parameters"], {})
            self.assertEqual(meta["automation"], "automatic")
            self.assertEqual(len(method_rows({}, meta)), len(meta["test_method"]))
            for item in meta["test_method"]:
                self.assertNotIn("criteria", item)
                self.assertNotIn("id", item)
                self.assertNotIn("step_id", item)
                self.assertIn(item["type"], ("Command", "Action", "Checkpoint", "Record"))
                self.assertIsInstance(item["step_number"], int)
            self.assertIn("can be parsed as JSON", meta["test_method"][3]["step"])

    def test_pass_and_no_001_record(self):
        for i in range(2):
            rows, _, log, _ = self.run_case(i, [response(GOOD[i])])
            self.assertEqual(rows["S1"]["status"], "COMPLETED")
            self.assertEqual(rows["C2a"]["status"], "PASS")
            self.assertIn("Step 2 | Checkpoint", log)
            self.assertNotIn("C2a", log)
            self.assertIn("Judgement: PASS", log)
            self.assertNotIn("Criteria:", log)
        self.assertFalse(any(r["type"] == "Record" for r in CASES[0].TEST_CASE["test_method"]))

    def test_missing_v1_does_not_fail_dependent_checkpoints(self):
        rows, _, _, _ = self.run_case(0, [response({})], "Fail")
        self.assertEqual(rows["C3a"]["status"], "FAIL")
        for key in ("C3b", "C3c"):
            self.assertEqual(rows[key]["status"], "NOT_EVALUATED")
            self.assertIn("v1 is missing", rows[key]["reason"])

    def test_v1_type_and_value_have_separate_attribution(self):
        for value, failed in [(123, "C3b"), ("/redfish/v1", "C3c")]:
            rows, _, _, _ = self.run_case(0, [response({"v1": value})], "Fail")
            self.assertEqual(rows[failed]["status"], "FAIL")
            self.assertEqual(rows["C2b"]["status"], "PASS")
            if failed == "C3b":
                self.assertEqual(rows["C3c"]["status"], "NOT_EVALUATED")

    def test_parse_failure_and_top_level_type(self):
        for i in range(2):
            rows, _, _, _ = self.run_case(i, [response("invalid JSON")], "Fail")
            self.assertEqual(rows["S2"]["status"], "FAILED")
            self.assertEqual(rows["C2a"]["status"], "FAIL")
            self.assertEqual(rows["C2b"]["status"], "NOT_EVALUATED")
            for body in ([], None, "42", '"hello"'):
                rows, _, _, _ = self.run_case(i, [response(body)], "Fail")
                self.assertEqual(rows["C2a"]["status"], "PASS")
                self.assertEqual(rows["C2b"]["status"], "FAIL")
                self.assertEqual(rows["S3"]["status"], "NOT_RUN")

    def test_independent_002_checks_and_record_survive_failure(self):
        body = {"@odata.type": "#Wrong.Type", "@odata.id": "/wrong", "RedfishVersion": 123}
        rows, ctx, _, _ = self.run_case(1, [response(body)], "Fail")
        self.assertEqual(rows["C3b"]["status"], "FAIL")
        self.assertEqual(rows["C4b"]["status"], "FAIL")
        self.assertEqual(rows["R5"]["status"], "RECORDED")
        self.assertEqual(rows["R5"]["actual"], 123)
        self.assertIn("Step 3", ctx["case_result"]["reason"])
        self.assertIn("Step 4", ctx["case_result"]["reason"])
        rows, _, _, _ = self.run_case(1, [response({})], "Fail")
        for key in ("C3a", "C4a"):
            self.assertEqual(rows[key]["status"], "FAIL")
        for key in ("C3b", "C4b"):
            self.assertEqual(rows[key]["status"], "NOT_EVALUATED")
        self.assertEqual(rows["R5"]["actual"], "Not present")

    def test_record_never_judges_value_or_presence(self):
        for value in (None, False, 0, "", "1.2.3", {"unusual": True}, float("nan"), float("inf")):
            rows, _, _, _ = self.run_case(1, [response(dict(GOOD[1], RedfishVersion=value))])
            self.assertEqual(rows["R5"]["status"], "RECORDED")
        rows, _, _, _ = self.run_case(1, [response(GOOD[1])])
        self.assertEqual(rows["R5"]["actual"], "Not present")

    def test_accepted_service_root_types(self):
        for kind in ("#ServiceRoot.ServiceRoot", "#ServiceRoot.v99_23_17.ServiceRoot"):
            self.run_case(1, [response(dict(GOOD[1], **{"@odata.type": kind}))])

    def test_http_failure_skips_downstream(self):
        for i in range(2):
            rows, _, _, _ = self.run_case(i, [response(GOOD[i], 404)], "Fail")
            self.assertEqual(rows["S1"]["status"], "COMPLETED")
            self.assertEqual(rows["C1"]["status"], "FAIL")
            self.assertEqual(rows["S2"]["status"], "NOT_RUN")

    def test_redirect_guards_and_request_contract(self):
        for i in range(2):
            redirects = [response("", 307, {"Location": f"/hop{n}"}) for n in range(6)]
            self.run_case(i, redirects[:5] + [response(GOOD[i])])
            self.run_case(i, redirects, "Fail")
            for location in ("https://other.invalid/x", "http://bmc.invalid/x",
                             "https://user:pw@bmc.invalid/x", "https://bmc.invalid:bad/x",
                             CASES[i].ENDPOINT):
                rows, _, _, calls = self.run_case(i, [response("", 302, {"Location": location})], "Fail")
                self.assertEqual(len(calls), 1)
                self.assertEqual(rows["S1"]["status"], "FAILED")
                self.assertEqual(rows["C1"]["status"], "NOT_EVALUATED")
            self.run_case(i, [response("", 301)], "Fail")

    def test_failure_error_dependency_and_sensitive_headers(self):
        for i in range(2):
            self.run_case(i, [requests.Timeout("offline")], "Fail")
            rows, _, _, _ = self.run_case(i, [RuntimeError("offline defect")], "Error")
            self.assertEqual(rows["S1"]["status"], "ERROR")
            for settings in ({}, {"host": None}, {"host": "https://bmc.invalid:bad"}):
                self.run_case(i, [], "Fail", settings)
            with patch.dict(sys.modules, {"requests": None}):
                self.run_case(i, [], "Error")
            _, context, log, _ = self.run_case(i, [response(GOOD[i], headers={
                "Authorization": "private-auth", "Set-Cookie": "private-cookie",
                "X-Auth-Token": "private-token", "Content-Type": "application/json"})])
            self.assertNotIn("private-", log)
            self.assertEqual(context["case_result"]["evidence"][0]["source_step"], 1)

    def test_legacy_log_adapter(self):
        for i in range(2):
            self.run_case(i, [response(GOOD[i])], old_log=True)

    def test_invalid_log_associations_and_record_verdict_rejected(self):
        logger = CaseLog(io.StringIO(), lambda event: None)
        item = {"type": "Record", "step_number": 5, "step": "Version"}
        result = {"method_index": 12, "type": "Record", "step_number": 5, "status": "PASS"}
        with self.assertRaises(ValueError):
            logger.method_item(item, result)
        result["status"] = "RECORDED"
        result["step_number"] = 4
        with self.assertRaises(ValueError):
            logger.method_item(item, result)
        result["step_number"] = item["step_number"] = 0
        with self.assertRaises(ValueError):
            logger.method_item(item, result)
