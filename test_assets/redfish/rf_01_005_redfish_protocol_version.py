import json
import re
from urllib.parse import urljoin, urlsplit

TEST_CASE = {
    "modified_at": "2026-11-26T05:00:54.277898+00:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.6 (RedfishVersion format)."
    ],
    "created_at": "2026-10-19T03:32:23.623177+00:00",
    "name": "RF-01-005 Redfish Protocol Version",
    "description": "Verify that ServiceRoot RedfishVersion exactly matches the tester-provided protocol version.",
    "test_method": [
        {
            "step_number": 1,
            "type": "Action",
            "step": "Read the expected RedfishVersion from the preset, or ask the tester if it is blank.",
            "checkpoints": {
                "tester_supplied_expected_version": {
                    "expected": "Verify that a nonblank expected version string was supplied."
                }
            }
        },
        {
            "step_number": 2,
            "type": "Command",
            "step": "Send GET /redfish/v1/ and follow supported same-origin redirects.",
            "route": "bmc_redfish",
            "checkpoints": {
                "final_http_status": {
                    "expected": "Verify that the final HTTP status is 200."
                }
            }
        },
        {
            "step_number": 3,
            "type": "Action",
            "step": "Parse the response body as JSON.",
            "checkpoints": {
                "valid_json": {
                    "expected": "Verify that the response body can be parsed as JSON."
                },
                "top_level_json_object": {
                    "expected": "Verify that the top-level JSON value is an object."
                }
            }
        },
        {
            "step_number": 4,
            "type": "Action",
            "step": "Read the RedfishVersion property.",
            "checkpoints": {
                "redfishversion_is_present": {
                    "expected": "Verify that RedfishVersion is present."
                },
                "redfishversion_format": {
                    "expected": "Verify that RedfishVersion uses the format major.minor.errata:\n- The value is a string.\n- It contains exactly three components separated by dots.\n- Each component contains one or more decimal digits."
                }
            }
        },
        {
            "step_number": 5,
            "type": "Action",
            "step": "Compare RedfishVersion with the expected version without normalization.",
            "checkpoints": {
                "exact_redfishversion_match": {
                    "expected": "Verify that RedfishVersion exactly matches the tester-supplied version.\n\nProject acceptance policy:\n- Compare the strings without normalization.\n- The tester defines the expected version; DMTF does not prescribe that value."
                }
            }
        }
    ],
    "automation": "semi_automatic",
    "parameters": {
        "preset": {
            "type": "string",
            "default": "",
            "label": "Expected RedfishVersion (blank: ask during execution)"
        }
    },
    "command_routes": {
        "bmc_redfish": {
            "from": "bmcagent",
            "to": "bmc",
            "method": "redfish",
            "lan_port": "task.bmc.lan_ports.port1",
            "username": "task.bmc.username",
            "password": "task.bmc.password"
        }
    }
}


from result_policy import declared_method_items

_METHOD_ITEMS = dict(declared_method_items(TEST_CASE["test_method"]))


def _route_host(context):
    from redfish_route import RedfishRoute
    declaration = TEST_CASE["command_routes"]["bmc_redfish"]
    try:
        return RedfishRoute(dict(context, log=context.get("log")), declaration).host
    except (KeyError, TypeError, AttributeError, IndexError) as error:
        raise ValueError("Invalid Task BMC LAN port settings") from error


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


_METHOD_CHECKS = [('Tester\\ supplied\\ expected\\ version', 'tester_supplied_expected_version'),
 ('Final\\ HTTP\\ status', 'final_http_status'),
 ('Valid\\ JSON', 'valid_json'),
 ('Top\\-level\\ JSON\\ object', 'top_level_json_object'),
 ('RedfishVersion\\ is\\ present', 'redfishversion_is_present'),
 ('RedfishVersion\\ format', 'redfishversion_format'),
 ('Exact\\ RedfishVersion\\ match', 'exact_redfishversion_match')]


def _method_emit(context, index, status, **detail):
    item = _METHOD_ITEMS[index]
    identity = {"checkpoint_id": index} if item["type"] == "Checkpoint" else {"method_index": index}
    result = dict(**identity, step_number=item["step_number"], type=item["type"],
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
    index = next(i for i, item in _METHOD_ITEMS.items()
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
    item = next(item for item in _METHOD_ITEMS.values()
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
        phase = _METHOD_ITEMS[index]["step_number"]
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
        elif status == "FAIL":
            result["reason"] = f"{label}: expected {result['expected']!r}, observed {result['actual']['value']!r}."
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
    for index, item in _METHOD_ITEMS.items():
        if item["type"] == "Record" and item.get("observation") in observations:
            _method_emit(context, index, "COMPLETED", actual=observations[item["observation"]])
    observed = {result.get("checkpoint_id", result.get("method_index")) for result in results}
    for index, item in _METHOD_ITEMS.items():
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
    logger = context.get("log")
    if callable(getattr(logger, "declare_methods", None)):
        logger.declare_methods(TEST_CASE["test_method"])
    evidence = []
    observations = {}
    _log(context, "section", "Expected protocol version input", report_step=1)
    settings = context.get("case_settings", {})
    if not isinstance(settings, dict):
        return _finish(context, "Error", "Plan case_settings must be a dictionary", evidence, observations)
    expected = preset if preset is not None else settings.get("preset", "")
    source = "preset"
    if expected is None or (isinstance(expected, str) and not expected.strip()):
        source = "interactive"
        # Keep platform interruption exceptions intact; the runner owns Stop handling.
        try:
            expected = input("Expected RedfishVersion (major.minor.errata): ")
        except EOFError:
            expected = ""
    observations["expected_version_source"] = source
    supplied = isinstance(expected, str) and bool(expected.strip())
    _log(context, "check", "Tester supplied expected version", supplied, actual=expected)
    if not supplied:
        reason = "Tester did not provide a version number" if expected is None or isinstance(expected, str) else "Tester-provided version must be a string"
        return _finish(context, "Fail", reason, evidence, observations)
    observations["expected_RedfishVersion"] = expected
    _log(context, "section", "Task connection settings", report_step=2)
    conf = context.get("redfish", {})
    if not isinstance(conf, dict):
        return _finish(context, "Fail", "Task BMC settings are invalid", evidence, observations)
    try:
        host = _route_host(context)
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

    url = urljoin(host, "/redfish/v1/")
    reason = None
    _log(context, "section", "HTTP request and redirect evidence", report_step=2)
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
                    url, headers={"Accept": "application/json"},
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
                     item["headers"], response.text, request_headers={"Accept": "application/json"})
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
                _log(context, "section", "JSON document validation", report_step=3)
                try:
                    body = json.loads(response.text)
                except ValueError:
                    _log(context, "check", "Valid JSON", False)
                    reason = "Response body is not valid JSON"
                    break
                _log(context, "check", "Valid JSON", True)
                _log(context, "check", "Top-level JSON object", isinstance(body, dict),
                     expected="object", actual=type(body).__name__)
                _log(context, "section", "Document content validation", report_step=4)
                if not isinstance(body, dict):
                    reason = "Response body is not a JSON object"
                    break
                present = "RedfishVersion" in body
                _log(context, "check", "RedfishVersion is present", present)
                if not present:
                    reason = "ServiceRoot did not provide RedfishVersion"
                    break
                actual = body["RedfishVersion"]
                observations["RedfishVersion"] = actual
                valid_version = isinstance(actual, str) and bool(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", actual))
                _log(context, "check", "RedfishVersion format", valid_version,
                     expected="major.minor.errata (decimal integers)", actual=actual)
                if not valid_version:
                    reason = "RedfishVersion format does not meet requirements"
                    break
                _log(context, "section", "Expected and actual protocol version comparison", report_step=5)
                _log(context, "check", "Exact RedfishVersion match", actual == expected,
                     expected=expected, actual=actual)
                if actual != expected:
                    reason = f"RedfishVersion does not match the expected version: expected={expected!r}, actual={actual!r}"

                break
    except requests.RequestException as error:
        reason = f"HTTP request could not complete ({type(error).__name__})"
    except Exception as error:
        return _finish(context, "Error", f"Unexpected program error ({type(error).__name__})",
                       evidence, observations)
    return _finish(context, "Fail" if reason else "Pass",
                   reason or "HTTP 200 with valid RedfishVersion exactly matching tester expectation",
                   evidence, observations)
