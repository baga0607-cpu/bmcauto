import json
from urllib.parse import urljoin, urlsplit

TEST_CASE = {
    "modified_at": '2026-11-12T09:02:07.701445+00:00',
    "test_type": "compliance",
    "spec_ref": ['DSP0266 v1.25.0 section 6.7, Table 4 (/redfish/v1/openapi.yaml); section 11.3.4, Table 33 '
 '(openapi.yaml terms).'],
    "created_at": "2026-10-30T05:56:21.765986+00:00",
    "name": "RF-01-008 OpenAPI Document Endpoint",
    "description": "Verify the minimum OpenAPI document structure when the endpoint is available; conditionally accept explicitly confirmed absence of this optional endpoint.",
    "test_method": [
    {
        "step_number": 1,
        "type": "Command",
        "step": "Send GET /redfish/v1/openapi.yaml and follow supported same-origin redirects."
    },
    {
        "step_number": 1,
        "type": "Checkpoint",
        "step": 'Verify HTTP 200. Project acceptance policy: use C-PASS only for HTTP 404 with message "The URI /redfish/v1/openapi.yaml was not found.", or HTTP 400 with both MessageId Base.1.16.InvalidURI and that exact Message in the same @Message.ExtendedInfo entry. Record the actual response and acceptance reason in Note; skip document checks when absence is accepted.'
    },
    {
        "step_number": 2,
        "type": "Action",
        "step": "Parse the response body as a single YAML document."
    },
    {
        "step_number": 2,
        "type": "Checkpoint",
        "step": "Verify that the response body can be parsed as YAML."
    },
    {
        "step_number": 2,
        "type": "Checkpoint",
        "step": "Verify that the top-level YAML value is an object."
    },
    {
        "step_number": 3,
        "type": "Action",
        "step": "Read the openapi, info and paths properties."
    },
    {
        "step_number": 3,
        "type": "Checkpoint",
        "step": "Verify that openapi is present and is a string."
    },
    {
        "step_number": 3,
        "type": "Checkpoint",
        "step": "Verify that info is present and is an object."
    },
    {
        "step_number": 3,
        "type": "Checkpoint",
        "step": "Verify that paths is present and is an object."
    }
],
    "automation": "automatic",
    "parameters": {},
}


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


def _emit(context, index, status, **values):
    item = TEST_CASE["test_method"][index]
    result = dict(method_index=index, type=item["type"],
                  step_number=item["step_number"], status=status, **values)
    context.setdefault("_method_results", {})[index] = result
    logger = context.get("log")
    if logger is not None:
        logger.method_item(item, result)
    else:
        print(json.dumps({"description": item["step"], **result}, ensure_ascii=False))


def _log(context, method, *args, **kwargs):
    if method == "section":
        number = kwargs.pop("report_step")
        context["_active_step"] = number
        item = TEST_CASE["test_method"][{1: 0, 2: 2, 3: 5}[number]]
        args = (f'Step {number} | {item["type"]} | {item["step"]}',)
    elif method == "http":
        context["_http_actual"] = {"uri": args[1], "status": args[2]}
    elif method == "check":
        number = context["_active_step"]
        action = {1: 0, 2: 2, 3: 5}[number]
        if action not in context.get("_method_results", {}):
            actual = (context.get("_http_actual") if number == 1 else
                      "YAML parsing attempted" if number == 2 else "Properties read")
            _emit(context, action, "FAILED" if number == 2 and not args[1] else "COMPLETED", actual=actual)
        index = {"Valid YAML": 3, "Top-level YAML object": 4,
                 "openapi property type": 6, "info property type": 7,
                 "paths property type": 8}.get(args[0], 1)
        note = kwargs.get("note")
        status = "C-PASS" if args[1] and note else "PASS" if args[1] else "FAIL"
        detail = {key: value for key, value in kwargs.items() if value is not None}
        if note:
            context["_result_note"] = note
        _emit(context, index, status, **detail)
        return
    logger = context.get("log")
    if logger is not None:
        return getattr(logger, method)(*args, **kwargs)
    print(json.dumps({"event": method, "details": args, **kwargs}, ensure_ascii=False))


def _finish(context, status, reason, evidence, observations):
    results = context.setdefault("_method_results", {})
    action = {1: 0, 2: 2, 3: 5}.get(context.get("_active_step"))
    if action is not None and action not in results:
        _emit(context, action, "ERROR" if status == "Error" else "FAILED", reason=reason)
    for index in range(len(TEST_CASE["test_method"])):
        if index not in results:
            _emit(context, index, "Skip", reason=(
                "Optional endpoint is absent; no document is available for validation."
                if status == "C-PASS" else "Prerequisite did not complete: " + reason))
    note = context.get("_result_note", "")
    context["case_result"] = dict(status=status, reason=reason, note=note,
                                  evidence=evidence, observations=observations)
    context["_tc_status"] = {"Pass": "PASS", "C-PASS": "C-PASS"}.get(status, "FAIL")
    if context.get("log") is not None:
        context["log"].finish(status, reason, note=note or None)
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

    url = urljoin(host, "/redfish/v1/openapi.yaml")
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
                    url, headers={"Accept": "application/yaml"},
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
                     item["headers"], response.text, request_headers={"Accept": "application/yaml"})
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
                if response.status_code in (400, 404):
                    try:
                        payload = json.loads(response.text)
                    except ValueError:
                        payload = None
                    error = payload.get("error", payload) if isinstance(payload, dict) else None
                    message = error.get("message") if isinstance(error, dict) else None
                    expected_message = "The URI /redfish/v1/openapi.yaml was not found."
                    actual = {"status": response.status_code}
                    if response.status_code == 400:
                        details = error.get("@Message.ExtendedInfo") if isinstance(error, dict) else None
                        matched = isinstance(details, list) and any(
                            isinstance(entry, dict)
                            and entry.get("MessageId") == "Base.1.16.InvalidURI"
                            and entry.get("Message") == expected_message
                            for entry in details
                        )
                        if not matched:
                            reason = "Expected HTTP status = 200; Received HTTP status = 400"
                            _log(context, "check", "OpenAPI missing-URI evidence", False,
                                 expected={"MessageId": "Base.1.16.InvalidURI", "Message": expected_message},
                                 actual=details)
                            break
                        actual["MessageId"] = "Base.1.16.InvalidURI"
                        message = expected_message
                    elif message != expected_message:
                        reason = "HTTP 404 response did not confirm the missing OpenAPI URI"
                        _log(context, "check", "OpenAPI missing-URI message", False,
                             expected=expected_message, actual=message)
                        break
                    actual["message"] = message
                    identifier = " (Base.1.16.InvalidURI)" if response.status_code == 400 else ""
                    note = (f'DUT returned HTTP {response.status_code}{identifier} with message: "{message}" '
                            "DSP0266 1.25.0 section 6.7 Table 4 marks it Required=No "
                            "(should support). Accepted as C-PASS; document content was not validated.")
                    observations.update(initial_uri=urljoin(host, "/redfish/v1/openapi.yaml"),
                                        final_uri=url, redirect_count=hop, endpoint_provided=False,
                                        document_validated=False)
                    _log(context, "check", "Recommended OpenAPI endpoint", True,
                         expected="HTTP 200 preferred; absence is non-mandatory",
                         actual=actual, note=note)
                    return _finish(context, "C-PASS", "Optional OpenAPI endpoint absent; document checks skipped",
                                   evidence, observations)
                _log(context, "check", "Final HTTP status", response.status_code == 200,
                     expected=200, actual=response.status_code)
                if response.status_code != 200:
                    reason = f"Expected HTTP status = 200; Received HTTP status = {response.status_code}"
                    break
                observations.update(initial_uri=urljoin(host, "/redfish/v1/openapi.yaml"),
                                    final_uri=url, redirect_count=hop)
                _log(context, "section", "YAML document validation", report_step=2)
                try:
                    import yaml
                except ImportError:
                    return _finish(context, "Error", "Required PyYAML package is unavailable",
                                   evidence, observations)
                try:
                    body = yaml.safe_load(response.text)
                except yaml.YAMLError:
                    _log(context, "check", "Valid YAML", False,
                         expected="One safe YAML document", actual="YAML parsing failed")
                    reason = "Response body is not a valid safe YAML document"
                    break
                _log(context, "check", "Valid YAML", True)
                _log(context, "check", "Top-level YAML object", isinstance(body, dict),
                     expected="object", actual=type(body).__name__)
                if not isinstance(body, dict):
                    reason = "Response body is not a YAML object"
                    break
                _log(context, "section", "Document content validation", report_step=3)
                failures = []
                for name, expected_type, type_name in (
                        ("openapi", str, "string"), ("info", dict, "object"),
                        ("paths", dict, "object")):
                    present = name in body
                    value = body.get(name)
                    valid = present and isinstance(value, expected_type)
                    # YAML values can include dates or recursive aliases; log type evidence.
                    _log(context, "check", name + " property type", valid,
                         expected=type_name,
                         actual=type(value).__name__ if present else "missing")
                    if not valid:
                        failures.append(name + " must be " + type_name)
                observations.update(endpoint_provided=True, document_validated=not failures)
                if failures:
                    reason = "OpenAPI document content mismatch: " + "; ".join(failures)
                break
    except requests.RequestException as error:
        reason = f"HTTP request could not complete ({type(error).__name__})"
    except Exception as error:
        return _finish(context, "Error", f"Unexpected program error ({type(error).__name__})",
                       evidence, observations)
    return _finish(context, "Fail" if reason else "Pass",
                   reason or "OpenAPI endpoint returned HTTP 200 with string openapi and object info and paths",
                   evidence, observations)
