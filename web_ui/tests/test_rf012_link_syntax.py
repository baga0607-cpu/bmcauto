"""Offline RF-01-012 checks; no production DB or network access."""
import ast
import contextlib
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

import requests

SOURCE = Path(__file__).resolve().parents[2] / "test_assets/redfish/rf_01_012_relative_uri_references.py"
spec = importlib.util.spec_from_file_location("rf012", SOURCE)
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


class RelativeReferenceTest(unittest.TestCase):
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
                self_outer.assertEqual(self.auth, ("user", "synthetic"))
                self_outer.assertTrue(url.startswith("https://bmc.invalid/"))
                self_outer.assertEqual(kwargs, {"headers": {"Accept": "application/json"},
                                               "verify": True, "timeout": 15, "allow_redirects": False})
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
            rows = [record for record in logger.records if record["kind"] == "step"]
            self.assertTrue(rows)
            self.assertEqual(len(rows), len(context["case_result"]["method_results"]))
            self.assertEqual(sum(r["kind"] == "finish" for r in logger.records), 1)
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
        stat = SOURCE.stat()
        expected = datetime.fromtimestamp(getattr(stat, "st_birthtime", stat.st_ctime), timezone.utc)
        self.assertEqual(meta["created_at"], "2026-10-30T07:19:35.437164+00:00")



    def test_reference_classification(self):
        for raw in ("/", "/Systems/1", "//bmc.invalid/redfish/v1/", "//[::1]/x",
                    "/x?value=1#p"):
            self.assertEqual(case._classify(raw), ("relative", []))
        for raw in ("https://bmc.invalid/x", "HTTP://bmc.invalid/x", "urn:example:item",
                    "mailto:operator@example.invalid"):
            self.assertEqual(case._classify(raw), ("absolute", []))
        for raw in ("Systems/1", "../Systems/1", "./x", "?page=2", "#/Value", "", "//",
                    "///x", "////bmc.invalid/x", "//:443/x", "//host:bad/x", "\n/x", None):
            with self.subTest(raw=raw):
                self.assertTrue(case._classify(raw)[1])

    def test_raw_body_violations_are_not_requested(self):
        for raw in ("Systems/1", "../Systems/1", "?page=2", "#/Value", ""):
            result, calls, _, _ = self.run_case({ROOT: root(Child=link(raw))}, "Fail")
            self.assertEqual(len(calls), 1)
            item=result["observations"]["violations"][0]
            self.assertEqual(item["uri"], raw)
            self.assertEqual(item["field"], "$/Child/@odata.id")

    def test_oem_pages_cycles_and_references(self):
        result, calls, _, _ = self.run_case({
            ROOT: root(Things=link("/things"), Oem={"Vendor": link("/a")}),
            "/things": resource("/things", "ThingCollection", Members=[link("/a")],
                                **{"Members@odata.nextLink": "/things?page=2"}),
            "/things?page=2": resource("/things", "ThingCollection", Members=[link("/b")]),
            "/a": resource("/a", Parent=link(ROOT)),
            "/b": resource("/b"),
        })
        self.assertEqual(len(calls), 5)
        self.assertTrue(result["observations"]["traversal_complete"])
        self.run_case({
            ROOT: root(Things=link("/things")),
            "/things": resource("/things", "ThingCollection",
                                **{"Members@odata.nextLink": "/things"})}, "Fail")

    def test_link_parser_commas_quotes_and_anchors(self):
        header = '</x?a=1,2>; rel="next"; title="a, b; c", <https://other.invalid/y>; anchor="/base"'
        self.assertEqual(case._link_references(header), [
            ("Link[0]/target", "/x?a=1,2"), ("Link[1]/target", "https://other.invalid/y"),
            ("Link[1]/anchor", "/base")])
        self.assertEqual(case._link_references('</x>; title="escaped \\"quote, here"; anchor="/a"')[-1],
                         ("Link[0]/anchor", "/a"))
        for header in ("", "bad", "</x", '</x>; title="unterminated',
                       "</x>,", "</x>; anchor", '</x>; anchor="/a"; anchor="/b"',
                       "<</x>>"):
            with self.subTest(header=header), self.assertRaises(case.CaseFailure):
                case._link_references(header)

    def test_unquoted_parameter_compatibility(self):
        for suffix in ('path=/SessionService', 'path="/SessionService"',
                       'path=/Links/Sessions; rel=item', 'type=application/json'):
            self.assertEqual(case._link_references('</redfish/v1/SessionService>; ' + suffix),
                             [("Link[0]/target", "/redfish/v1/SessionService")])
        self.assertEqual(case._link_references('</x>; anchor=/base')[-1],
                         ("Link[0]/anchor", "/base"))

    def test_compatible_header_completes_scope_without_hiding_violations(self):
        header = ('<http://redfish.dmtf.org/schemas/v1/ServiceRoot.v1_9_0.json>; rel=describedby, '
                  '</redfish/v1/SessionService>; path=/SessionService, '
                  '</redfish/v1/SessionService/Sessions>; path=/Links/Sessions')
        mapping = {ROOT: response(root(Child=link('/child')), headers={'Link': header}),
                   '/child': resource('/child')}
        result, calls, _, _ = self.run_case(mapping, 'Fail')
        self.assertEqual(len(result['observations']['header_syntax_errors']), 2)
        checks = result['method_results']
        self.assertTrue(any(r['step_number'] == 2 and r['status'] == 'FAIL' for r in checks))
        self.assertTrue(any(r['step_number'] == 3 and r['status'] == 'PASS' for r in checks))
        self.assertTrue(result['observations']['traversal_complete'])
        self.assertFalse(result['observations']['header_errors'])
        self.assertIn('https://bmc.invalid/child', calls)
        mapping[ROOT].headers['Link'] = header + ', <bad/path>; path=/Bad'
        result, _, _, _ = self.run_case(mapping, 'Fail')
        self.assertTrue(result['observations']['violations'])
        mapping[ROOT].headers['Link'] = '</x>; path=/x; anchor=relative'
        result, _, _, _ = self.run_case(mapping, 'Fail')
        self.assertTrue(result['observations']['violations'])

    def test_header_syntax_quoted_and_token_values_pass(self):
        header = '</x>; path="/x"; anchor="/base"; rel=item; custom=token'
        result, _, _, _ = self.run_case({ROOT: response(root(), headers={'Link': header})})
        self.assertEqual(result['observations']['header_syntax_errors'], [])

    def test_unquoted_anchor_is_inspected_despite_syntax_failure(self):
        result, _, _, _ = self.run_case({ROOT: response(root(), headers={
            'Link': '</x>; anchor=/base; type=application/json'})}, 'Fail')
        self.assertEqual(len(result['observations']['header_syntax_errors']), 2)
        self.assertTrue(any(x['uri'] == '/base' for x in result['observations']['uris']))
        self.assertEqual(result['observations']['unread'], [])

    def test_ambiguous_unquoted_parameters_still_fail(self):
        for header in ('</x>; path=', '</x>; path=/a /b', '</x>; path=/a"b"',
                       '</x>; path=/a<bad>', '</x>; path=/a; anchor=/a; anchor=/b',
                       '</x>; path=/a; title="unfinished'):
            with self.subTest(header=header), self.assertRaises(case.CaseFailure):
                case._link_references(header)

    def test_header_counts_and_absent_headers(self):
        result, calls, _, _ = self.run_case({ROOT: response(root(), headers={
            "Location": "/returned", "Content-Location": "//bmc.invalid/current",
            "Link": '</schema>; rel=describedby, <https://schemas.invalid/x>; rel=alternate; anchor="/base"'})})
        self.assertEqual(len(calls), 1)
        counts=result["observations"]["counts"]
        self.assertEqual(counts["body"]["relative"], 1)
        self.assertEqual(counts["headers"]["relative"], 4)
        self.assertEqual(counts["headers"]["absolute"], 1)
        self.assertEqual(result["observations"]["absent_headers"], [])
        result, _, _, _ = self.run_case({ROOT: root()})
        self.assertEqual(result["observations"]["absent_headers"],
                         ["content-location", "link", "location"])

    def test_invalid_header_references_and_parse_failures(self):
        for headers in ({"Location": "../x"}, {"Content-Location": "x"},
                        {"Link": '<Systems/1>; rel=item'},
                        {"Link": '</x>; anchor="#fragment"'}):
            result, _, _, _ = self.run_case({ROOT: response(root(), headers=headers)}, "Fail")
            self.assertTrue(result["observations"]["violations"])
        result, _, _, _ = self.run_case({ROOT: response(root(), headers={"Link": 'bad'})}, "Fail")
        self.assertEqual(len(result["observations"]["header_errors"]), 1)
        self.assertFalse(result["observations"]["traversal_complete"])

    def test_headers_on_redirect_and_failure_responses(self):
        result, calls, _, _ = self.run_case({
            ROOT: response(status=302, headers={"Location": "/actual", "Link": "<bad/path>; rel=item"}),
            "/actual": root(),
        }, "Fail")
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["observations"]["violations"][0]["uri"], "bad/path")
        result, _, _, _ = self.run_case({
            ROOT: response(status=500, headers={"Location": "relative"})
        }, "Fail")
        self.assertTrue(result["observations"]["violations"])

    def test_actions_uri_properties_external_and_prose(self):
        result, calls, _, _ = self.run_case({ROOT: root(
            External=link("//external.invalid/x"),
            Actions={"#Reset": {"target": "/Actions/Reset"}},
            BackupUri="https://other.invalid/file",
            Description="Text ../x and #fragment are not links")})
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["observations"]["counts"]["body"]["absolute"], 1)
        for body in (root(Actions={"#Reset": {"target": "Actions/Reset"}}),
                     root(BackupUri="../file")):
            self.run_case({ROOT: body}, "Fail")

    def test_absolute_only_scope_is_not_applicable(self):
        result, _, _, _ = self.run_case({
            ROOT: resource("https://bmc.invalid" + ROOT, "ServiceRoot")}, "Fail")
        self.assertEqual(result["observations"]["relative_reference_count"], 0)
        self.assertFalse(result["observations"]["violations"])
        self.assertIn("No applicable", result["reason"])

    def test_network_path_local_traversal(self):
        _, calls, _, _ = self.run_case({
            ROOT: root(Child=link("//bmc.invalid/child")),
            "/child": resource("/child")})
        self.assertEqual(len(calls), 2)

    def test_redirects_and_unread_scope(self):
        for status in (301,302,307,308):
            self.run_case({ROOT: response(status=status, headers={"Location": "/actual"}),
                           "/actual": root()})
        for target in ("relative", ROOT, "https://other.invalid/x", "http://bmc.invalid/x",
                       "/Actions/Reset"):
            _, calls, _, _ = self.run_case({ROOT: response(status=302, headers={"Location": target})}, "Fail")
            self.assertEqual(len(calls), 1)
        for bad in (response(status=404), response("not JSON"), response([]), requests.Timeout("synthetic")):
            _, calls, _, _ = self.run_case({
                ROOT: root(Links=[link("/bad"),link("/good")]),
                "/bad": bad, "/good": resource("/good")}, "Fail")
            self.assertIn("https://bmc.invalid/good", calls)

    def test_log_steps_and_error_classification(self):
        scenarios = [
            ({ROOT: root()}, "Pass", ["PASS","PASS","PASS"]),
            ({ROOT: root(Actions={"#Reset": {"target": "bad"}})}, "Fail", ["PASS","PASS","FAIL"]),
            ({ROOT: response(status=500)}, "Fail", ["PASS","FAIL",None]),
            ({ROOT: RuntimeError("defect")}, "Error", ["PASS","ERROR",None]),
        ]
        for mapping, outcome, statuses in scenarios:
            _, _, logger, _ = self.run_case(mapping, outcome)
            rows=[r for r in logger.records if r["kind"]=="step"]
            self.assertTrue(rows)
            if outcome == "Pass":
                self.assertTrue(all(r["result"]["status"] in ("PASS", "COMPLETED", "Skip") for r in rows))
            else:
                self.assertTrue(any(r["result"]["status"] in ("FAIL", "FAILED", "ERROR") for r in rows))
        with patch.dict("sys.modules", {"requests":None}):
            self.run_case({}, "Error")
        self.run_case({}, "Fail", settings={})
        _, _, _, output=self.run_case({ROOT:root()}, platform_log=False)
        self.assertIn("method_results", output)

    def test_sensitive_headers_redacted(self):
        result, _, _, output=self.run_case({ROOT:response(root(),headers={
            "Set-Cookie":"secret-cookie","Authorization":"secret-auth","X-Auth-Token":"secret-token"})})
        self.assertEqual(result["evidence"][0]["headers"],{})
        self.assertNotIn("secret-",output)


if __name__=="__main__":
    unittest.main(verbosity=2)
