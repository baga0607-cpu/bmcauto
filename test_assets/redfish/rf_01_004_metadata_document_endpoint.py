import json
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET

TEST_CASE = {'modified_at': "2026-11-12T09:19:32.977199+00:00",
 'test_type': 'compliance',
 'spec_ref': ['DSP0266 v1.25.0 section 6.7 Table 4; sections 7.2.4 and 8.4.2 (OData metadata); section '
              '11.1.4 (CSDL format).'],
 'created_at': '2026-10-19T03:27:51.085627+00:00',
 'name': 'RF-01-004 Metadata Document Endpoint',
 'description': 'GET /redfish/v1/$metadata and verify the minimum XML Edmx document identity.',
 'test_method': [{'step_number': 1,
                  'type': 'Command',
                  'step': 'Send GET /redfish/v1/$metadata and follow supported same-origin redirects.'},
                 {'step_number': 1,
                  'type': 'Checkpoint',
                  'step': 'Verify that the final HTTP status is 200.'},
                 {'step_number': 2,
                  'type': 'Action',
                  'step': 'Parse the response bytes as XML using the declared encoding.'},
                 {'step_number': 2,
                  'type': 'Checkpoint',
                  'step': "Verify that the XML document contains no DTD declaration.\n\nThis is a parser safeguard: DTD processing is disabled."},
                 {'step_number': 2,
                  'type': 'Checkpoint',
                  'step': 'Verify that the response body can be parsed as XML.'},
                 {'step_number': 3,
                  'type': 'Action',
                  'step': 'Read the root element name, namespace and Version attribute.'},
                 {'step_number': 3, 'type': 'Checkpoint', 'step': 'Verify that the root local name is Edmx.'},
                 {'step_number': 3,
                  'type': 'Checkpoint',
                  'step': 'Verify that the root namespace is http://docs.oasis-open.org/odata/ns/edmx.'},
                 {'step_number': 3,
                  'type': 'Checkpoint',
                  'step': "Verify that the root element has a Version attribute with:\n- No namespace prefix.\n- The exact value \"4.0\"."}],
 'automation': 'automatic',
 'parameters': {}}


class UnsupportedDTD(ValueError):
    """Parser boundary; do not resolve or expand DTD entities."""


class MetadataTreeBuilder(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise UnsupportedDTD("DTD processing is disabled")


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


_METHOD_CHECKS = [('Final\\ HTTP\\ status', 1),
 ('XML\\ parser\\ safety\\ boundary', 3),
 ('Valid\\ XML', 4),
 ('Root\\ local\\ name', 6),
 ('Root\\ namespace', 7),
 ('Edmx\\ Version\\ attribute', 8)]


def _method_emit(context, index, status, **detail):
    item = TEST_CASE["test_method"][index]
    result = dict(method_index=index, step_number=item["step_number"], type=item["type"],
                  status=status, **detail)
    result = json.loads(json.dumps(result, ensure_ascii=False), parse_constant=lambda value: value)
    context.setdefault("_method_results", []).append(result)
    logger = context.get("log")
    if callable(getattr(logger, "method_item", None)):
        logger.method_item(item, result)
    elif callable(getattr(logger, "step", None)):
        logger.step(item["step"], None, result)
    else:
        print(json.dumps({"method": item, "result": result}, ensure_ascii=False))


def _report_flush(context, status=None, reason=None):
    phase = context.get("_method_phase")
    if phase is None:
        return
    pending = context.get("_method_pending", [])
    requests = context.get("_method_http", [])
    index = next(i for i, item in enumerate(TEST_CASE["test_method"])
                 if item["step_number"] == phase and item["type"] in ("Command", "Action"))
    failed_parse = any(label in ("Valid JSON", "Valid XML", "XML parser safety boundary")
                       and result["status"] == "FAIL" for _, label, result in pending)
    skipped = context.pop("_method_action_skip", None)
    outcome = ("Skip" if skipped else "ERROR" if status == "Error" else "FAILED" if failed_parse
               or status == "Fail" and not pending else "COMPLETED")
    detail = {"actual": {"responses": requests} if requests else "Operation completed"}
    if outcome in ("FAILED", "ERROR", "Skip"):
        detail = {"reason": skipped or reason or "Response parsing did not complete"}
    _method_emit(context, index, outcome, **detail)
    for index, label, result in pending:
        _method_emit(context, index, **result)
    context["_method_phase"] = None
    context["_method_pending"], context["_method_http"] = [], []


def _report_begin(context, number):
    if context.get("_method_phase") == number:
        return
    _report_flush(context)
    context["_method_phase"] = number
    context.setdefault("_method_visited", set()).add(number)
    context["_method_pending"], context["_method_http"] = [], []
    item = next(item for item in TEST_CASE["test_method"]
                if item["step_number"] == number and item["type"] in ("Command", "Action"))
    if context.get("log") is not None:
        context["log"].section(f'Step {number} | {item["type"]} | {item["step"]}')


def _log(context, method, *args, **kwargs):
    if method == "section":
        number = kwargs.pop("report_step", None)
        if number is not None:
            _report_begin(context, number)
        return
    if method == "check":
        import re
        label, passed = args
        index = next((index for pattern, index in _METHOD_CHECKS if re.fullmatch(pattern, label)), None)
        if index is None:
            raise RuntimeError("No declared Checkpoint for " + label)
        phase = TEST_CASE["test_method"][index]["step_number"]
        if context.get("_method_phase") != phase:
            _report_begin(context, phase)
        note = kwargs.get("note")
        status = kwargs.pop("judgement", None) or ("C-PASS" if passed and note else "PASS" if passed else "FAIL")
        result = {"status": status, "expected": kwargs.get("expected", True),
                  "actual": {"source": label, "value": kwargs.get("actual", bool(passed))}}
        if note and status == "C-PASS":
            result["note"] = note
        if kwargs.get("reason"):
            result["reason"] = kwargs["reason"]
        context.setdefault("_method_pending", []).append((index, label, result))
        return
    if method == "http":
        context.setdefault("_method_http", []).append({"method": args[0], "uri": args[1], "status": args[2]})
    logger = context.get("log")
    if logger is not None:
        return getattr(logger, method)(*args, **kwargs)
    print(json.dumps({"event": method, "details": args, **kwargs}, ensure_ascii=False))


def _finish(context, status, reason, evidence, observations):
    _report_flush(context, status, reason)
    results = context.setdefault("_method_results", [])
    for index, item in enumerate(TEST_CASE["test_method"]):
        if item["type"] == "Record" and item.get("observation") in observations:
            _method_emit(context, index, "COMPLETED", actual=observations[item["observation"]])
    observed = {result["method_index"] for result in results}
    for index, item in enumerate(TEST_CASE["test_method"]):
        if index not in observed:
            skip_reason = ("No applicable item was encountered for this check."
                           if item["step_number"] in context.get("_method_visited", set()) and status == "Pass"
                           else "Prerequisite was unavailable or execution ended: " + reason)
            _method_emit(context, index, "Skip", reason=skip_reason)
    notes = list(dict.fromkeys(result["note"] for result in results if result["status"] == "C-PASS"))
    if status == "Pass" and any(result["status"] in ("FAIL", "FAILED", "ERROR") for result in results):
        status, reason = "Fail", "A required method item failed; see its recorded result"
    elif status == "Pass" and notes:
        status = "C-PASS"
    note = "\n".join(notes) if status == "C-PASS" else ""
    context["case_result"] = dict(status=status, reason=reason, note=note, evidence=evidence,
                                  observations=observations, method_results=results)
    context["_tc_status"] = {"Pass": "PASS", "C-PASS": "C-PASS", "Block": "BLOCK"}.get(status, "FAIL")
    if context.get("log") is not None:
        context["log"].finish(status, reason, **({"note": note} if note else {}))
    else:
        print(json.dumps(context["case_result"], ensure_ascii=False))
    if status == "Fail":
        raise CaseFailure(reason)
    if status == "Error":
        raise RuntimeError(reason)


def _origin(url):
    value = urlsplit(url)
    return (value.scheme.lower(), value.hostname,
            value.port or (443 if value.scheme == "https" else 80))


def execute(client, context=None, preset=None):
    """Use Task connection settings, not global YAML or client private APIs."""
    if not isinstance(context, dict):
        raise RuntimeError("BMCAgent did not supply a dictionary execution context")
    _log(context, "section", "Task connection settings", report_step=1)
    evidence = []
    observations = {}
    conf = context.get("redfish", {})
    if not isinstance(conf, dict):
        return _finish(context, "Fail", "Task BMC settings are invalid", evidence, observations)
    host = conf.get("host", "")
    try:
        parsed = urlsplit(host) if isinstance(host, str) else None
        valid = parsed is not None and parsed.scheme in ("http", "https") and bool(parsed.hostname)
        valid = valid and not parsed.username and not parsed.password
        origin = _origin(host) if valid else None
    except ValueError:
        valid = False
    if not valid:
        return _finish(context, "Fail", "Task BMC URL is missing or invalid", evidence, observations)
    try:
        import requests
    except ImportError:
        return _finish(context, "Error", "Required requests package is unavailable", evidence, observations)

    url = urljoin(host, "/redfish/v1/$metadata")
    reason = None
    _log(context, "section", "HTTP request and redirect evidence", report_step=1)
    try:
        with requests.Session() as session:
            session.trust_env = False
            session.auth = (conf.get("username", ""), conf.get("password", ""))
            seen = set()
            for hop in range(6):
                if url in seen:
                    reason = "Redirect loop detected"
                    break
                seen.add(url)
                response = session.get(
                    url, headers={"Accept": "application/xml"},
                    verify=conf.get("verify_ssl", False), timeout=15,
                    allow_redirects=False,
                )
                item = {
                    "uri": url, "status": response.status_code,
                    "headers": {k: v for k, v in response.headers.items()
                                if k.lower() not in ("set-cookie", "authorization", "x-auth-token")},
                    "body": response.text,
                }
                evidence.append(item)
                _log(context, "http", "GET", url, response.status_code,
                     item["headers"], response.text, request_headers={"Accept": "application/xml"})
                if response.status_code in (301, 302, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        reason = "Redirect response has no Location"
                        break
                    try:
                        target = urljoin(url, location)
                        target_parts = urlsplit(target)
                        leaves_origin = (target_parts.username or target_parts.password
                                         or _origin(target) != origin)
                    except ValueError:
                        reason = "Redirect URL is invalid"
                        break
                    if leaves_origin:
                        reason = "Redirect leaves Task origin; credentials were not forwarded"
                        break
                    if hop == 5:
                        reason = "Redirect limit exceeded (5 redirects)"
                        break
                    url = target
                    continue
                _log(context, "check", "Final HTTP status", response.status_code == 200,
                     expected=200, actual=response.status_code)
                if response.status_code != 200:
                    reason = f"Expected HTTP status = 200; Received HTTP status = {response.status_code}"
                    break
                _log(context, "section", "XML document parsing", report_step=2)
                try:
                    body = ET.fromstring(response.content,
                                         parser=ET.XMLParser(target=MetadataTreeBuilder()))
                except UnsupportedDTD:
                    _log(context, "check", "XML parser safety boundary", False,
                         expected="No DTD processing", actual="DTD declaration")
                    reason = "XML DTD processing is disabled; document not validated (parser safeguard)"
                    break
                except (ET.ParseError, LookupError, ValueError) as error:
                    _log(context, "check", "Valid XML", False, actual=str(error))
                    reason = f"Response body could not be parsed as XML ({type(error).__name__})"
                    break
                _log(context, "check", "XML parser safety boundary", True, expected="No DTD processing", actual="No DTD processed")
                _log(context, "check", "Valid XML", True)
                _log(context, "section", "Metadata document identity validation", report_step=3)
                namespace, local_name = "", body.tag
                if body.tag.startswith("{"):
                    namespace, local_name = body.tag[1:].split("}", 1)
                version = body.get("Version")
                observations.update(root_local_name=local_name, root_namespace=namespace,
                                    edmx_version=version)
                checks = [
                    ("Root local name", local_name, "Edmx"),
                    ("Root namespace", namespace, "http://docs.oasis-open.org/odata/ns/edmx"),
                    ("Edmx Version attribute", version, "4.0"),
                ]
                failures = []
                for label, actual, expected in checks:
                    passed = actual == expected
                    _log(context, "check", label, passed, expected=expected, actual=actual)
                    if not passed:
                        failures.append(f"Expected {label} = {expected!r}; Received {label} = {actual!r}")
                reason = "; ".join(failures) or None
                break

    except requests.RequestException as error:
        reason = f"HTTP request could not complete ({type(error).__name__})"
    except Exception as error:
        return _finish(context, "Error", f"Unexpected program error ({type(error).__name__})",
                       evidence, observations)
    return _finish(context, "Fail" if reason else "Pass",
                   reason or "HTTP 200 with XML Edmx root, OData namespace and Version 4.0",
                   evidence, observations)
