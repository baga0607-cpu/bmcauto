"""Offline RF-01-011 checks; no production DB or network access."""
import ast
import contextlib
from datetime import datetime, timezone
import importlib.util
import io
import json
import re
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

import requests

SOURCE = Path(__file__).resolve().parents[2] / "test_assets/redfish/rf_01_011_uri_fragment_references.py"
spec = importlib.util.spec_from_file_location("rf011", SOURCE)
case = importlib.util.module_from_spec(spec)
spec.loader.exec_module(case)
sys.path.insert(0, str(SOURCE.parents[2] / "web_ui"))
from case_log import CaseLog

ROOT = "/redfish/v1/"


def resource(uri, kind="Thing", **properties):
    return {"@odata.id": uri, "@odata.type": "#" + kind + "." + kind, **properties}


def root(**properties):
    return resource(ROOT, "ServiceRoot", **properties)


def link(uri):
    return {"@odata.id": uri}


def response(body=None, status=200, headers=None):
    return type("Response", (), {"status_code": status, "headers": headers or {},
                                "text": body if isinstance(body, str) else json.dumps(body)})()


class FragmentTest(unittest.TestCase):
    def run_case(self, mapping, expected="Pass", settings=None, platform_log=True):
        output = io.StringIO()
        logger = CaseLog(output, lambda event: None)
        context = {"redfish": settings if settings is not None else {
            "host": "https://bmc.invalid/base", "username": "user",
            "password": "synthetic", "verify_ssl": True}}
        if platform_log:
            context["log"] = logger
        calls = []

        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def get(self, url, **kwargs):
                self_outer.assertFalse(self.trust_env)
                external = url.startswith("https://redfish.dmtf.org/schemas/")
                self_outer.assertEqual(self.auth, None if external else ("user", "synthetic"))
                self_outer.assertTrue(external or url.startswith("https://bmc.invalid/"))
                self_outer.assertEqual(kwargs["headers"]["Accept"], "application/json")
                self_outer.assertEqual({k: v for k, v in kwargs.items() if k != "headers"},
                                       {"verify": True, "timeout": 15, "allow_redirects": False})
                if url.endswith("/ServiceRoot.json"):
                    self_outer.assertEqual(kwargs["headers"]["Cache-Control"], "no-cache")
                self_outer.assertNotIn(url, calls, "Each URL may be requested only once")
                calls.append(url)
                key = url.removeprefix("https://bmc.invalid")
                value = mapping[key]
                if isinstance(value, Exception):
                    raise value
                return value if hasattr(value, "status_code") else response(value)

        self_outer = self
        with patch.object(socket.socket, "connect", side_effect=AssertionError("No network")),              patch.object(requests, "Session", Session), contextlib.redirect_stdout(io.StringIO()) as console:
            if expected == "Pass":
                case.execute(None, context)
            else:
                with self.assertRaises(case.CaseFailure if expected == "Fail" else RuntimeError):
                    case.execute(None, context)
        self.assertEqual(context["case_result"]["status"], expected)
        self.assertEqual(context["_tc_status"], "PASS" if expected == "Pass" else "FAIL")
        self.assertTrue(context["case_result"]["reason"])
        if platform_log:
            self.assertEqual(sum(r["kind"] == "finish" for r in logger.records), 1)
            self.assertTrue(context["case_result"]["method_results"])
        return context["case_result"], calls, logger, output.getvalue() + console.getvalue()

    def test_metadata_birthtime_and_english(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertTrue(source.isascii())
        tree = ast.parse(source)
        meta = ast.literal_eval(next(n.value for n in tree.body if isinstance(n, ast.Assign)
                                     and any(isinstance(t, ast.Name) and t.id == "TEST_CASE" for t in n.targets)))
        self.assertEqual(meta, case.TEST_CASE)
        self.assertEqual(meta["parameters"], {})
        self.assertEqual(meta["automation"], "automatic")
        # Git checkouts have new filesystem timestamps; retain the original creation metadata.
        expected = datetime(2026, 10, 30, 6, 23, 36, 474763, tzinfo=timezone.utc)
        self.assertEqual(datetime.fromisoformat(meta["created_at"]), expected)



    def fixture(self, uri=ROOT + "#/Target", target=None, schema=None):
        if target is None:
            target = {"@odata.id": ROOT + "#/Target", "Name": "Target"}
        if schema is None:
            schema = {"type": "object", "properties": {
                "@odata.id": {"type": "string"},
                "Ref": {"$ref": "#/definitions/Link"},
                "Target": {"$ref": "#/definitions/Link"},
                "ValueUri": {"type": "string", "format": "uri-reference"}},
                "definitions": {"Link": {"type": "object", "properties": {
                    "@odata.id": {"type": "string"}}}}}
        return {ROOT: response(root(Ref=link(uri), Target=target),
                               headers={"Link": '</schema.json>; rel="describedby"'}),
                "/schema.json": schema}

    def test_pointer_examples(self):
        document = {"": 0, "a/b": {"~name": [False, None]}, "~1": "ordered",
                    "a%2Fb": 7, "cafe" + chr(233): 9}
        for pointer, expected in (("/", 0), ("/a~1b/~0name/0", False),
                                  ("/a~1b/~0name/1", None), ("/~01", "ordered"),
                                  ("/a%252Fb", 7), ("/cafe%C3%A9", 9)):
            self.assertEqual(case._resolve_pointer(document, pointer), expected)
        self.assertIs(case._resolve_pointer(document, ""), document)

    def test_bad_pointer_syntax_and_targets(self):
        for pointer in ("anchor", "/~", "/~2", "/missing", "/a/01", "/a/-", "/a/-1",
                        "/a/1", "/a/0/x", "/a/%GG", "/a/%", "/a/%FF", "/a#b", "/a/ 0"):
            with self.subTest(pointer=pointer), self.assertRaises(case.CaseFailure):
                case._resolve_pointer({"a": [3]}, pointer)

    def test_reference_and_property_targets(self):
        result, calls, _, _ = self.run_case(self.fixture())
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["observations"]["fragment_count"], 2)
        self.assertTrue(all(r["property_kind"] == "resource" for r in result["observations"]["results"]))
        mapping = self.fixture()
        mapping[ROOT] = response(root(ValueUri=ROOT + "#/Value", Value=False),
                                 headers={"Link": "</schema.json>; rel=describedby"})
        result, _, _, _ = self.run_case(mapping)
        self.assertEqual(result["observations"]["results"][0]["property_kind"], "property")

    def test_resource_target_requires_matching_identity(self):
        for value in (17, {}, {"@odata.id": ROOT}, {"@odata.id": ROOT + "#/Other"}):
            mapping = self.fixture(target=value)
            result, _, _, _ = self.run_case(mapping, "Fail")
            self.assertTrue(any(not r["passed"] for r in result["observations"]["results"]))
        mapping = self.fixture(uri=ROOT + "#/Missing")
        self.run_case(mapping, "Fail")

    def test_no_fragments_external_actions_and_prose(self):
        result, calls, _, _ = self.run_case({ROOT: root(
            Description="Use #/Name as an example", WebsiteUri="https://external.invalid/#anchor",
            Actions={"#Reset": {"target": ROOT + "#/Danger"}})}, "Fail")
        self.assertEqual(result["observations"]["fragment_count"], 0)
        self.assertIn("No applicable", result["reason"])
        self.assertEqual(len(calls), 1)

    def test_target_fetch_strips_fragment_and_caches(self):
        mapping = self.fixture(uri="/child#/Target")
        mapping["/child"] = response(resource("/child", Target={"@odata.id": "/child#/Target"}),
                                     headers={"Link": "</schema.json>; rel=describedby"})
        result, calls, _, _ = self.run_case(mapping)
        self.assertTrue(all("#" not in uri for uri in calls))
        self.assertEqual(calls.count("https://bmc.invalid/child"), 1)

    def test_schema_missing_unknown_external_and_cycle(self):
        mapping = self.fixture()
        mapping[ROOT].headers.clear()
        self.run_case(mapping, "Fail")
        mapping = self.fixture()
        mapping[ROOT].headers["Link"] = "<https://external.invalid/schema>; rel=describedby"
        _, calls, _, _ = self.run_case(mapping, "Fail")
        self.assertEqual(len(calls), 1)
        for schema in (
                {"type": "object", "properties": {}},
                {"$ref": "#"},
                {"allOf": []},
                {"anyOf": [{"type": "object"}, {"type": "object"}]},
                {"$ref": "https://external.invalid/schema"},
        ):
            self.run_case(self.fixture(schema=schema), "Fail")

    def test_schema_nullable_and_external_document_ref(self):
        schema = {"type": "object", "properties": {
            "Ref": {"anyOf": [{"type": "null"}, {"$ref": "/link.json"}]},
            "Target": {"$ref": "/link.json"}}}
        mapping = self.fixture(schema=schema)
        mapping["/link.json"] = {"type": "object", "properties": {"@odata.id": {"type": "string"}}}
        _, calls, _, _ = self.run_case(mapping)
        self.assertEqual(calls.count("https://bmc.invalid/link.json"), 1)

    def test_schema_document_canonical_id(self):
        for keyword in ("$id", "id"):
            mapping = self.fixture()
            mapping["/schema.json"][keyword] = "https://schemas.invalid/Example.json"
            _, calls, _, _ = self.run_case(mapping)
            self.assertTrue(all("schemas.invalid" not in uri for uri in calls))
        mapping = self.fixture()
        mapping["/schema.json"]["$id"] = "https://schemas.invalid/Example.json"
        mapping["/schema.json"]["properties"]["Ref"] = {"$ref": "Other.json"}
        self.run_case(mapping, "Fail")

    def test_schema_link_ambiguity(self):
        self.assertEqual(case._schema_link('</a>; rel="other", </b>; rel="describedby"'), "/b")
        for header in ("", "</a>; rel=other",
                       "</a>; rel=describedby, </b>; rel=describedby"):
            with self.assertRaises(case.CaseFailure):
                case._schema_link(header)

    def test_pagination_and_unread_scope(self):
        mapping = self.fixture()
        body = json.loads(mapping[ROOT].text)
        body["Things"] = link("/things")
        mapping[ROOT].text = json.dumps(body)
        mapping["/things"] = resource("/things", "ThingCollection",
                                      **{"Members@odata.nextLink": "/things?page=2"})
        mapping["/things?page=2"] = resource("/things", "ThingCollection", Members=[])
        self.run_case(mapping)
        mapping["/things?page=2"] = response(status=404)
        self.run_case(mapping, "Fail")
        mapping["/things?page=2"] = resource("/things", "ThingCollection",
                                             **{"Members@odata.nextLink": "/things"})
        self.run_case(mapping, "Fail")

    def test_redirect_and_http_errors(self):
        mapping = self.fixture()
        mapping["/schema.json"] = response(status=302, headers={"Location": "/actual-schema"})
        mapping["/actual-schema"] = {"type": "object", "properties": {
            "Ref": {"type": "object", "properties": {"@odata.id": {"type": "string"}}},
            "Target": {"type": "object", "properties": {"@odata.id": {"type": "string"}}}}}
        self.run_case(mapping)
        for value in (response(status=404), response("invalid"), response([]), requests.Timeout("synthetic")):
            self.run_case({ROOT: value}, "Fail")
        for location in (ROOT, "https://external.invalid/x", "/Actions/Reset"):
            self.run_case({ROOT: response(status=302, headers={"Location": location})}, "Fail")

    def test_duplicate_json_and_nullable_uri(self):
        self.run_case({ROOT: response('{"a": 1, "a": 2}')}, "Fail")
        mapping = self.fixture()
        mapping["/schema.json"]["properties"]["ValueUri"]["type"] = ["string", "null"]
        mapping[ROOT] = response(root(ValueUri=ROOT + "#/Value", Value=None),
                                 headers={"Link": "</schema.json>; rel=describedby"})
        self.run_case(mapping)

    def version_fixture(self):
        mapping = self.fixture()
        body = json.loads(mapping[ROOT].text)
        body["@odata.type"] = "#ServiceRoot.v1_0_0.ServiceRoot"
        base = "https://redfish.dmtf.org/schemas/v1/"
        mapping[ROOT] = response(body, headers={"Link": "<http://redfish.dmtf.org/schemas/v1/ServiceRoot.json>; rel=describedby"})
        definition = mapping.pop("/schema.json")
        mapping[base + "ServiceRoot.json"] = {"$ref": "#/definitions/ServiceRoot", "definitions": {
            "ServiceRoot": {"anyOf": [{"$ref": "ServiceRoot.v9_0_0.json#/definitions/ServiceRoot"},
                                       {"$ref": "ServiceRoot.v1_0_0.json#/definitions/ServiceRoot"}]}}}
        mapping[base + "ServiceRoot.v1_0_0.json"] = {"definitions": {"ServiceRoot": definition, **definition.pop("definitions")}}
        return mapping, base

    def test_dmtf_declared_version_and_per_run_cache(self):
        mapping, base = self.version_fixture()
        for _ in range(2):
            result, calls, _, _ = self.run_case(mapping)
            self.assertEqual(calls.count(base + "ServiceRoot.json"), 1)
            self.assertIn(base + "ServiceRoot.v1_0_0.json", calls)
            self.assertNotIn(base + "ServiceRoot.v9_0_0.json", calls)
            self.assertTrue(any(r["cache_hit"] for r in result["observations"]["schema_requests"]))

    def test_dmtf_version_mismatch_and_missing_version(self):
        mapping, base = self.version_fixture()
        mapping[ROOT].headers["Link"] = "<" + base + "ServiceRoot.v9_0_0.json>; rel=describedby"
        result, calls, _, _ = self.run_case(mapping, "Fail")
        self.assertEqual(len(calls), 1)
        self.assertIn("does not match", result["observations"]["results"][0]["reason"])
        mapping, base = self.version_fixture()
        mapping[base + "ServiceRoot.json"]["definitions"]["ServiceRoot"]["anyOf"].pop()
        result, calls, _, _ = self.run_case(mapping, "Fail")
        self.assertIn("no branch", result["observations"]["results"][0]["reason"])
        self.assertEqual(len(calls), 2)

    def test_direct_schema_ref_version_mismatch(self):
        mapping, base = self.version_fixture()
        mapping[base + "ServiceRoot.json"] = {"$ref": "ServiceRoot.v9_0_0.json#/definitions/ServiceRoot"}
        result, calls, _, _ = self.run_case(mapping, "Fail")
        self.assertEqual(len(calls), 2)
        self.assertIn("does not match", result["observations"]["results"][0]["reason"])

    def test_dmtf_dependency_failure_evidence(self):
        for failure in (requests.ConnectionError("offline"), response(status=404), response("not json")):
            mapping, base = self.version_fixture()
            mapping[base + "ServiceRoot.v1_0_0.json"] = failure
            result, _, _, _ = self.run_case(mapping, "Fail")
            item = result["observations"]["results"][0]
            self.assertTrue(item["pointer_resolved"])
            self.assertEqual(item["failure_stage"], "schema")
            self.assertIn(base + "ServiceRoot.v1_0_0.json", item["reason"])

    def test_dmtf_trust_and_redirect_boundaries(self):
        for uri in ("https://redfish.dmtf.org.evil.test/schemas/a.json",
                    "https://redfish.dmtf.org:444/schemas/a.json",
                    "https://redfish.dmtf.org/other/a.json",
                    "https://redfish.dmtf.org/schemas/%2e%2e/a.json"):
            with self.assertRaises(case.CaseFailure):
                case._trusted_schema_url(uri)
        mapping, base = self.version_fixture()
        mapping[base + "ServiceRoot.json"] = response(status=302, headers={"Location": "https://evil.test/schema.json"})
        result, calls, _, _ = self.run_case(mapping, "Fail")
        self.assertEqual(len(calls), 2)
        self.assertIn("not trusted", result["observations"]["results"][0]["reason"])
        mapping, base = self.version_fixture()
        mapping[base + "ServiceRoot.json"] = response(status=302, headers={"Location": base + "alias.json"})
        mapping[base + "alias.json"] = {"$ref": "ServiceRoot.v1_0_0.json#/definitions/ServiceRoot"}
        self.run_case(mapping)

    def test_step_results_and_dependency_error(self):
        for mapping, expected, statuses in (
                (self.fixture(), "Pass", ["PASS", "PASS", "PASS"]),
                ({ROOT: root()}, "Fail", ["PASS", "PASS", "FAIL"]),
                ({ROOT: RuntimeError("defect")}, "Error", ["PASS", "ERROR", None])):
            _, _, logger, _ = self.run_case(mapping, expected)
            rows = [r for r in logger.records if r["kind"] == "step"]
            self.assertTrue(rows)
            if expected == "Pass":
                self.assertTrue(all(r["result"]["status"] in ("PASS", "COMPLETED") for r in rows))
        with patch.dict("sys.modules", {"requests": None}):
            self.run_case({}, "Error")
        self.run_case({}, "Fail", settings={})
        _, _, _, output = self.run_case(self.fixture(), platform_log=False)
        self.assertIn("method_results", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
