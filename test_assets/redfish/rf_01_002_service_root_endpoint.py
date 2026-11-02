import json
import re
from urllib.parse import urljoin, urlsplit

TEST_CASE = {
    "modified_at": "2026-11-02T06:11:19.396101+00:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 sections 6.6, 6.7 Table 4 and 7.2.3 (ServiceRoot); sections 9.6.2 and 9.6.3 (resource identity/type)."
    ],
    "created_at": '2026-10-19T01:23:29.401576+00:00',
    "name": "RF-01-002 Service Root Endpoint",
    "description": (
        "GET /redfish/v1/ and verify the ServiceRoot type and resource URI. "
        "Record RedfishVersion without checking its expected value."
    ),
    "test_method": [
        {
            "step_1": (
                "Using Task BMC connection settings, send GET /redfish/v1/ with "
                "Accept: application/json and a fixed 15-second request timeout. "
                "Record each response URI, status, headers and body. Follow supported "
                "same-origin redirects, detecting loops, up to five redirects."
            ),
            "criteria": (
                "The final HTTP status is 200. Invalid Task settings, request "
                "failure, missing redirect Location, loops, exceeding five redirects "
                "or leaving the Task origin result in Fail with a reason. Redirect "
                "safeguards are provisional pending RF-02; a boundary failure alone "
                "does not establish a DMTF violation."
            ),
        },
        {
            "step_2": "Parse the final response body as JSON.",
            "criteria": (
                "The body is valid JSON and its top-level value is an object. "
                "Invalid JSON or another top-level type results in Fail with a reason."
            ),
        },
        {
            "step_3": "Inspect @odata.type and @odata.id; record RedfishVersion if present.",
            "criteria": (
                "@odata.type is a ServiceRoot type identifier: "
                "#ServiceRoot.v<major>_<minor>_<errata>.ServiceRoot or "
                "#ServiceRoot.ServiceRoot. No particular Schema version is required. "
                "@odata.id equals /redfish/v1/ exactly. Additional properties are "
                "allowed. RedfishVersion is evidence only; its presence, format and "
                "expected value are evaluated by RF-01-005. All criteria met results "
                "in Pass; a content mismatch results in Fail with a reason. An "
                "unexpected program problem or missing dependency results in Error."
            ),
        },
    ],
    "automation": "automatic",
    "parameters": {},
}


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


def _report_emit(context, number, result):
    """Record the authored method and criteria without changing case judgement."""
    method = TEST_CASE["test_method"][number - 1]
    step = method.get("step_" + str(number), method.get("step"))
    criteria = method.get("criteria")
    logger = context.get("log")
    write = getattr(logger, "step", None) if logger is not None else None
    if callable(write):
        note = result.get('note') if isinstance(result, dict) else None
        write(step, criteria, result, **({'note': note} if note else {}))
    else:
        print("\n--- REPORT STEP ---")
        print(json.dumps({"step": step, "criteria": criteria, "result": result}, ensure_ascii=False, indent=2))


def _report_flush(context, status=None, reason=None):
    state = context.get("_report_steps")
    if not state or state["number"] is None:
        return
    number, checks = state["number"], state["checks"]
    if status is not None:
        outcome = status.upper()
    elif checks:
        outcome = "PASS" if all(check["passed"] for check in checks) else "FAIL"
    else:
        outcome = None
    result = {"status": outcome, "checks": checks} if outcome is not None else None
    if reason and result is not None:
        result["reason"] = reason
    notes = [check['note'] for check in checks if check.get('note')]
    if notes and result is not None:
        result['note'] = '\n'.join(dict.fromkeys(notes))
    _report_emit(context, number, result)
    state["seen"].append(number)
    state["number"], state["checks"] = None, []


def _report_begin(context, number):
    state = context.setdefault("_report_steps", {"number": None, "checks": [], "seen": []})
    if state["number"] != number:
        _report_flush(context)
        state["number"] = number


def _report_finish(context, status, reason):
    _report_flush(context, status, reason)
    state = context.get("_report_steps", {"seen": []})
    for number in range(1, len(TEST_CASE["test_method"]) + 1):
        if number not in state["seen"]:
            _report_emit(context, number, None)
    context.pop("_report_steps", None)


def _log(context, method, *args, **kwargs):
    # Report evidence is separate from assertions and the final case outcome.
    if method == "section":
        number = kwargs.pop("report_step", None)
        if number is not None:
            _report_begin(context, number)
    elif method == "check":
        if kwargs.get("note"):
            context.setdefault("_result_notes", []).append(kwargs["note"])
        state = context.get("_report_steps")
        if state and state["number"] is not None:
            state["checks"].append({"label": args[0], "passed": bool(args[1]),
                                    "expected": kwargs.get("expected"), "actual": kwargs.get("actual"), "note": kwargs.get("note")})
    logger = context.get("log")
    if logger is not None:
        return getattr(logger, method)(*args, **kwargs)
    # Standalone/offline execution remains possible without a platform import.
    print("\n--- " + method.upper() + " ---")
    print(json.dumps({"details": args, **kwargs}, ensure_ascii=False, indent=2))


def _finish(context, status, reason, evidence, observations):
    _report_finish(context, status, reason)
    note = "\n".join(dict.fromkeys(context.get("_result_notes", [])))
    context["case_result"] = {
        "status": status, "reason": reason, "note": note, "evidence": evidence,
        "observations": observations,
    }
    # Compatibility with the current runner; it still stores Error as Failed.
    context["_tc_status"] = "PASS" if status == "Pass" else "FAIL"
    if context.get("log") is not None:
        _log(context, "finish", status, reason, **({"note": note} if note else {}))
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

    url = urljoin(host, "/redfish/v1/")
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
                _log(context, "section", "JSON document validation", report_step=2)
                try:
                    body = json.loads(response.text)
                except ValueError:
                    _log(context, "check", "Valid JSON", False)
                    reason = "Response body is not valid JSON"
                    break
                _log(context, "check", "Valid JSON", True)
                _log(context, "check", "Top-level JSON object", isinstance(body, dict),
                     expected="object", actual=type(body).__name__)
                _log(context, "section", "Document content validation")
                if not isinstance(body, dict):
                    reason = "Response body is not a JSON object"
                    break
                _report_begin(context, 3)
                if "RedfishVersion" in body:
                    observations["RedfishVersion"] = body["RedfishVersion"]
                resource_type = body.get("@odata.type")
                type_ok = isinstance(resource_type, str) and bool(re.fullmatch(
                    r"#ServiceRoot(?:\.v[0-9]+_[0-9]+_[0-9]+)?\.ServiceRoot", resource_type))
                id_ok = body.get("@odata.id") == "/redfish/v1/"
                _log(context, "check", "ServiceRoot type", type_ok,
                     expected="ServiceRoot (any Schema version)", actual=resource_type)
                _log(context, "check", "ServiceRoot URI", id_ok,
                     expected="/redfish/v1/", actual=body.get("@odata.id"))
                if not type_ok:
                    reason = f"Expected @odata.type = a type identifying ServiceRoot; Received @odata.type = {resource_type!r}"
                elif not id_ok:
                    reason = f"Expected @odata.id = '/redfish/v1/'; Received @odata.id = {body.get('@odata.id')!r}"
                break
    except requests.RequestException as error:
        reason = f"HTTP request could not complete ({type(error).__name__})"
    except Exception as error:
        return _finish(context, "Error", f"Unexpected program error ({type(error).__name__})",
                       evidence, observations)
    return _finish(context, "Fail" if reason else "Pass",
                   reason or "HTTP 200 with ServiceRoot type and @odata.id='/redfish/v1/'",
                   evidence, observations)
