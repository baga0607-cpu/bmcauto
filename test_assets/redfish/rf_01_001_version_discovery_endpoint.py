import json
from urllib.parse import urljoin, urlsplit

TEST_CASE = {
    "created_at": '2026-10-14T07:32:57.063413+00:00',
    "name": "RF-01-001 Version Discovery Endpoint",
    "description": "GET /redfish and verify the v1 mapping to /redfish/v1/.",
    "test_method": [
        {
            "step_1": (
                "Using Task BMC connection settings, send GET /redfish with "
                "Accept: application/json and a fixed 15-second request timeout. "
                "Record each response status, headers and body. Follow supported "
                "same-origin redirects, detecting loops, up to five redirects."
            ),
            "criteria": (
                "The final HTTP status is 200. Invalid Task settings, request "
                "failure, missing redirect Location, loops, exceeding five "
                "redirects or leaving the Task origin result in Fail with a reason. "
                "Redirect safeguards are provisional pending RF-02; a boundary "
                "failure alone does not establish a DMTF violation."
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
            "step_3": "Inspect the v1 property in the JSON object.",
            "criteria": (
                "v1 exists, is a string and equals /redfish/v1/ exactly. "
                "Additional properties are allowed. Missing or incorrect v1 "
                "results in Fail with a reason. All steps meeting their criteria "
                "results in Pass. An unexpected program execution problem or "
                "missing required dependency at any step results in Error."
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
        write(step, criteria, result)
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
        state = context.get("_report_steps")
        if state and state["number"] is not None:
            state["checks"].append({"label": args[0], "passed": bool(args[1]),
                                    "expected": kwargs.get("expected"), "actual": kwargs.get("actual")})
    logger = context.get("log")
    if logger is not None:
        return getattr(logger, method)(*args, **kwargs)
    # Standalone/offline execution remains possible without a platform import.
    print("\n--- " + method.upper() + " ---")
    print(json.dumps({"details": args, **kwargs}, ensure_ascii=False, indent=2))


def _finish(context, status, reason, evidence):
    _report_finish(context, status, reason)
    context["case_result"] = {
        "status": status, "reason": reason, "evidence": evidence,
    }
    context["_tc_status"] = "PASS" if status == "Pass" else "FAIL"
    if context.get("log") is not None:
        _log(context, "finish", status, reason)
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
    if context is None:
        raise RuntimeError("BMCAgent did not supply the execution context")
    _log(context, "section", "Task connection settings", report_step=1)
    evidence = []
    conf = context.get("redfish", {})
    host = conf.get("host", "")
    try:
        parsed = urlsplit(host)
        valid = parsed.scheme in ("http", "https") and bool(parsed.hostname)
        valid = valid and not parsed.username and not parsed.password
        origin = _origin(host) if valid else None
    except (ValueError, TypeError):
        valid = False
    timeout = 15
    if not valid:
        return _finish(context, "Fail", "Task BMC URL is missing or invalid", evidence)
    try:
        import requests
    except ImportError:
        return _finish(context, "Error", "Required requests package is unavailable", evidence)

    url = urljoin(host, "/redfish")
    reason = None
    _log(context, "section", "HTTP request and redirect evidence", report_step=1)
    try:
        with requests.Session() as session:
            # Do not obtain proxy settings or unrelated credentials from the host.
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
                    verify=conf.get("verify_ssl", False), timeout=timeout,
                    allow_redirects=False,
                )
                # Cookies may contain authentication material; do not log them.
                item = {"uri": url, "status": response.status_code,
                        "headers": {k: v for k, v in response.headers.items()
                                    if k.lower() not in ("set-cookie", "authorization", "x-auth-token")},
                        "body": response.text}
                evidence.append(item)
                _log(context, "http", "GET", url, response.status_code,
                     item["headers"], response.text, request_headers={"Accept": "application/json"})
                if response.status_code in (301, 302, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        reason = "Redirect response has no Location"
                        break
                    target = urljoin(url, location)
                    target_parts = urlsplit(target)
                    if target_parts.username or target_parts.password or _origin(target) != origin:
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
                    reason = f"Expected HTTP 200, received {response.status_code}"
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
                elif "v1" not in body:
                    _log(context, "check", "v1 mapping", False, expected="/redfish/v1/", actual="<missing>")
                    reason = "Response has no v1 property"
                elif not isinstance(body["v1"], str) or body["v1"] != "/redfish/v1/":
                    _log(context, "check", "v1 mapping", False, expected="/redfish/v1/", actual=body["v1"])
                    reason = f"Expected v1='/redfish/v1/', received {body['v1']!r}"
                else:
                    _log(context, "check", "v1 mapping", True, expected="/redfish/v1/", actual=body["v1"])
                _report_begin(context, 3)
                break
    except requests.RequestException as error:
        reason = f"HTTP request could not complete ({type(error).__name__})"
    except ValueError:
        reason = "Redirect URL is invalid"
    except Exception as error:
        return _finish(context, "Error", f"Unexpected program error ({type(error).__name__})", evidence)
    return _finish(context, "Fail" if reason else "Pass",
                   reason or "HTTP 200 with v1='/redfish/v1/'", evidence)
