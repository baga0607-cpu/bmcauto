"""Offline execution of the thirteen v1 authoring deliverables through the production entry point."""
import io
import runpy
import socket
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import requests

from case_log import CaseLog
from single_case import metadata
from test_rf01_series_audit import ROOT_BODY, reply, schema_routes


REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT / "testcases" / "RF-01-v1"
if not ROOT.is_dir():
    # The desktop workspace keeps authored cases alongside the BMCAgent checkout.
    ROOT = REPO_ROOT.parent / "testcases" / "RF-01-v1"
CASE_FILENAMES = {
    1: "rf_01_001_version_discovery_endpoint.py",
    2: "rf_01_002_service_root_endpoint.py",
    3: "rf_01_003_odata_service_document_endpoint.py",
    4: "rf_01_004_metadata_document_endpoint.py",
    5: "rf_01_005_redfish_protocol_version.py",
    6: "rf_01_006_service_root_uri_alias.py",
    7: "rf_01_007_version_discovery_uri_alias.py",
    8: "rf_01_008_openapi_document_endpoint.py",
    9: "rf_01_009_resource_uri_uniqueness.py",
    10: "rf_01_010_uri_character_and_encoding_rules.py",
    11: "rf_01_011_uri_fragment_references.py",
    12: "rf_01_012_relative_uri_references.py",
    13: "rf_01_013_local_schema_file_endpoint.py",
}
ROOT_URI = "/redfish/v1/"


class AuthorCaseTest(unittest.TestCase):
    def run_case(self, number, routes, expected):
        path = ROOT / CASE_FILENAMES[number]
        definition = metadata(path.read_text(encoding="utf-8"))
        case = runpy.run_path(str(path))
        self.assertTrue(callable(case["run"]))
        logger = CaseLog(io.StringIO(), lambda e: None)
        context = {"log": logger, "redfish": {"host": "https://bmc.invalid"}}

        def get(session, url, **options):
            self.assertEqual(urlsplit(url).netloc, "bmc.invalid")
            self.assertFalse(options["allow_redirects"])
            return routes[urlsplit(url).path]

        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network disabled")), \
             patch.object(requests.Session, "get", get):
            try:
                case["execute"](None, context, preset="1.20.0")
            except case["CaseFailure"]:
                self.assertEqual(expected, "Fail")
        result = context["case_result"]
        self.assertEqual(result["status"], expected, result["reason"])
        self.assertEqual({key for item in definition["test_method"] for key in item.get("checkpoints", {})},
                         {r["checkpoint_id"] for r in result["method_results"] if r["type"] == "Checkpoint"})
        return result

    def test_all_cases(self):
        fragments = {ROOT_URI: reply(dict(ROOT_BODY, ProbeUri=ROOT_URI+"#/Target", Target=123),
                                     headers={"Link": "</schema.json>; rel=describedby"}),
                     "/schema.json": reply({"properties": {"ProbeUri": {"type": "string", "format": "uri-reference"}}})}
        inputs = {
            1: {"/redfish": reply({"v1": ROOT_URI})},
            2: {ROOT_URI: reply(dict(ROOT_BODY, RedfishVersion="1.20.0"))},
            3: {ROOT_URI+"odata": reply({"@odata.context": ROOT_URI+"$metadata", "value": []})},
            4: {ROOT_URI+"$metadata": reply('<edmx:Edmx xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx" Version="4.0"/>')},
            5: {ROOT_URI: reply({"RedfishVersion": "1.20.0"})},
            6: {ROOT_URI.rstrip("/"): reply(ROOT_BODY)},
            7: {"/redfish/": reply({"v1": ROOT_URI})},
            8: {ROOT_URI+"openapi.yaml": reply('openapi: "3.0.0"\ninfo: {}\npaths: {}')},
            9: {ROOT_URI: reply(ROOT_BODY)},
            10: {ROOT_URI: reply(ROOT_BODY)},
            11: fragments,
            12: {ROOT_URI: reply(ROOT_BODY)},
            13: schema_routes(),
        }
        for number, routes in inputs.items():
            with self.subTest(case=number):
                self.run_case(number, routes, "Pass")

    def test_conditional_acceptance(self):
        path = ROOT_URI + "openapi.yaml"
        for status, message, expected in [
            (404, {"error": {"message": f"The URI {path} was not found."}}, "C-PASS"),
            (404, {"error": {"message": "Other endpoint"}}, "Fail"),
            (200, "[broken", "Fail"),
        ]:
            result = self.run_case(8, {path: reply(message, status)}, expected)
            if expected == "C-PASS":
                self.assertTrue(result["note"])
        self.run_case(13, schema_routes(body={"$schema": "https://json-schema.org/draft/2020-12/schema",
                                             "$defs": {}}), "C-PASS")
        self.run_case(13, schema_routes(body="invalid schema"), "Fail")

    def test_blocked_archive(self):
        routes = schema_routes([{"ArchiveUri": "/bundle.tar", "ArchiveFile": "Test.json"}])
        routes["/bundle.tar"] = reply(b"unsupported archive")
        self.run_case(13, routes, "Block")
