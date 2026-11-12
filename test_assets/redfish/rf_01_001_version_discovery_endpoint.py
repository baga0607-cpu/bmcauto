import json
import math
import re
from urllib.parse import urljoin, urlsplit

TEST_CASE = {
    "modified_at": "2026-11-12T08:48:00+00:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.6 (protocol/version discovery); section 6.7 Table 4 (/redfish)."
    ],
    "created_at": "2026-10-14T07:32:57.063413+00:00",
    "name": "RF-01-001 Version Discovery Endpoint",
    "description": "Verify that /redfish returns a valid JSON object whose v1 property equals /redfish/v1/.",
    "test_method": [
        {
            "step_number": 1,
            "type": "Command",
            "step": "Send a GET request to `/redfish`."
        },
        {
            "step_number": 1,
            "type": "Checkpoint",
            "step": "Verify that the final response status is HTTP 200."
        },
        {
            "step_number": 2,
            "type": "Action",
            "step": "Parse the final response body as JSON."
        },
        {
            "step_number": 2,
            "type": "Checkpoint",
            "step": "Verify that the response body can be parsed as JSON."
        },
        {
            "step_number": 2,
            "type": "Checkpoint",
            "step": "Verify that the top-level JSON value is an object."
        },
        {
            "step_number": 3,
            "type": "Action",
            "step": "Read the `v1` property from the JSON object."
        },
        {
            "step_number": 3,
            "type": "Checkpoint",
            "step": "Verify that the `v1` property exists."
        },
        {
            "step_number": 3,
            "type": "Checkpoint",
            "step": "Verify that the `v1` value is a string."
        },
        {
            "step_number": 3,
            "type": "Checkpoint",
            "step": "Verify that the `v1` value equals `/redfish/v1/` exactly, including the trailing slash."
        }
    ],
    "automation": "automatic",
    "parameters": {}
}

ENDPOINT = "/redfish"

class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


def _safe(value):
    """Keep observations JSON-compatible without changing their judgement."""
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    if isinstance(value, dict):
        return {key: _safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe(item) for item in value]
    return value


def _emit(context, method_index, status, actual=None, expected=None, reason=None):
    item = TEST_CASE["test_method"][method_index]
    result = {"method_index": method_index, "type": item["type"],
              "step_number": item["step_number"], "status": status, "actual": _safe(actual)}
    if expected is not None:
        result["expected"] = expected
    if reason:
        result["reason"] = reason
    context["_method_results"][method_index] = result
    logger = context.get("log")
    if callable(getattr(logger, "method_item", None)):
        logger.method_item(item, result)
    elif callable(getattr(logger, "step", None)):
        logger.step(item["step"], None, result)
    else:
        print(json.dumps({"method": item, "result": result}, ensure_ascii=False, allow_nan=False))


def _begin(context, method_index):
    context["_active_step"] = method_index
    logger = context.get("log")
    item = TEST_CASE["test_method"][method_index]
    if logger is not None:
        logger.section(f'Step {item["step_number"]} | {item["type"]} | {item["step"]}')


def _location(context):
    index = context.get("_active_step")
    return f'Step {TEST_CASE["test_method"][index]["step_number"]}' if index is not None else "Execution"


def _done(context, method_index, actual=None):
    _emit(context, method_index, "COMPLETED", actual)
    context["_active_step"] = None


def _check(context, method_index, passed, expected, actual):
    _emit(context, method_index, "PASS" if passed else "FAIL", actual, expected)
    if not passed:
        item = TEST_CASE["test_method"][method_index]
        context["_failures"].append(
            f'Step {item["step_number"]} — {item["step"]} Expected {expected!r}; received {_safe(actual)!r}')


def _skip(context, method_index, reason):
    _emit(context, method_index, "Skip", reason=reason)


def _finish(context, status, reason, evidence, observations):
    active = context.get("_active_step")
    if active is not None and active not in context["_method_results"]:
        _emit(context, active, "ERROR" if status == "Error" else "FAILED", reason=reason)
    for index, item in enumerate(TEST_CASE["test_method"]):
        if index not in context["_method_results"]:
            pending = {"Command": "Skip", "Action": "Skip", "Checkpoint": "Skip", "Record": "Skip"}
            _emit(context, index, pending[item["type"]], reason=reason)
    context["case_result"] = {
        "status": status, "reason": reason, "evidence": evidence,
        "observations": _safe(observations),
        "method_results": list(context["_method_results"].values()),
    }
    context["_tc_status"] = "PASS" if status == "Pass" else "FAIL"
    logger = context.get("log")
    if logger is not None:
        logger.finish(status, reason)
    else:
        print(json.dumps(context["case_result"], ensure_ascii=False, allow_nan=False))
    if status == "Fail":
        raise CaseFailure(reason)
    if status == "Error":
        raise RuntimeError(reason)


def _origin(url):
    value = urlsplit(url)
    return (value.scheme.lower(), value.hostname,
            value.port or (443 if value.scheme == "https" else 80))


def execute(client, context=None, preset=None):
    """Use Task connection settings and keep typed method evidence in the Log."""
    if not isinstance(context, dict):
        raise RuntimeError("BMCAgent did not supply a dictionary execution context")
    context["_method_results"], context["_failures"] = {}, []
    evidence, observations = [], {}
    _begin(context, 0)
    conf = context.get("redfish", {})
    try:
        host = conf.get("host", "") if isinstance(conf, dict) else ""
        parsed = urlsplit(host) if isinstance(host, str) else None
        valid = parsed is not None and parsed.scheme in ("http", "https") and bool(parsed.hostname)
        valid = valid and not parsed.username and not parsed.password
        origin = _origin(host) if valid else None
    except (ValueError, TypeError):
        valid = False
    if not valid:
        return _finish(context, "Fail", "Step 1: Task BMC URL is missing or invalid", evidence, observations)
    try:
        import requests
    except ImportError:
        return _finish(context, "Error", "Step 1: Required requests package is unavailable", evidence, observations)

    url = urljoin(host, ENDPOINT)
    reason = None
    try:
        with requests.Session() as session:
            session.trust_env = False
            session.auth = (conf.get("username", ""), conf.get("password", ""))
            seen = set()
            for hop in range(6):
                if url in seen:
                    reason = "Step 1: Redirect loop detected"
                    break
                seen.add(url)
                response = session.get(
                    url, headers={"Accept": "application/json"},
                    verify=conf.get("verify_ssl", False), timeout=15, allow_redirects=False)
                item = {"source_step": 1, "uri": url, "status": response.status_code,
                        "headers": {k: v for k, v in response.headers.items()
                                    if k.lower() not in ("set-cookie", "authorization", "x-auth-token")},
                        "body": response.text}
                evidence.append(item)
                logger = context.get("log")
                if logger is not None:
                    logger.http("GET", url, response.status_code, item["headers"], response.text,
                                request_headers={"Accept": "application/json"})
                else:
                    print(json.dumps({"source_step": 1, "http": item}, ensure_ascii=False))
                if response.status_code in (301, 302, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        reason = "Step 1: Redirect response has no Location"
                        break
                    try:
                        target = urljoin(url, location)
                        parts = urlsplit(target)
                        leaves_origin = parts.username or parts.password or _origin(target) != origin
                    except ValueError:
                        reason = "Step 1: Redirect URL is invalid"
                        break
                    if leaves_origin:
                        reason = "Step 1: Redirect leaves Task origin; credentials were not forwarded"
                        break
                    if hop == 5:
                        reason = "Step 1: Redirect limit exceeded (5 redirects)"
                        break
                    url = target
                    continue
                _done(context, 0, {"final_uri": url, "status": response.status_code})
                _check(context, 1, response.status_code == 200, 200, response.status_code)
                if response.status_code != 200:
                    reason = context["_failures"][-1]
                    break
                _begin(context, 2)
                try:
                    body = json.loads(response.text)
                except ValueError:
                    reason = "Step 2: Response body cannot be parsed as JSON"
                    _emit(context, 2, "FAILED", reason=reason)
                    context["_active_step"] = None
                    _check(context, 3, False, "Response body can be parsed as JSON", "Parse failed")
                    break
                _done(context, 2, {"top_level_type": type(body).__name__})
                _check(context, 3, True, "Response body can be parsed as JSON", "Parsed")
                _check(context, 4, isinstance(body, dict), "object", type(body).__name__)
                if not isinstance(body, dict):
                    reason = "Step 2: Top-level JSON value is not an object"
                    break
                _inspect(context, body, observations)
                if context["_failures"]:
                    reason = "; ".join(context["_failures"])
                break
    except requests.RequestException as error:
        reason = f"{_location(context)}: HTTP request could not complete ({type(error).__name__})"
    except Exception as error:
        return _finish(context, "Error",
                       f"{_location(context)}: Unexpected program error ({type(error).__name__})",
                       evidence, observations)
    return _finish(context, "Fail" if reason else "Pass",
                   reason or "All Checkpoints passed", evidence, observations)

def _inspect(context, body, observations):
    _begin(context, 5)
    present = "v1" in body
    value = body.get("v1")
    _done(context, 5, {"present": present, "value": _safe(value)})
    _check(context, 6, present, "v1 property exists", "Present" if present else "Missing")
    if not present:
        _skip(context, 7, "Step 3 failed: v1 is missing")
        _skip(context, 8, "Step 3 failed: v1 is missing")
        return
    _check(context, 7, isinstance(value, str), "string", type(value).__name__)
    if not isinstance(value, str):
        _skip(context, 8, "Step 3 failed: v1 is not a string")
        return
    _check(context, 8, value == "/redfish/v1/", "/redfish/v1/", value)
