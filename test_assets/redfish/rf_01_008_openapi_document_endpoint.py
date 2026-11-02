import json
from urllib.parse import urljoin, urlsplit

TEST_CASE = {
    "modified_at": "2026-11-02T07:31:44.412549+00:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.7 Table 4 (/redfish/v1/openapi.yaml, Required=No); section 11.3.4 Table 33 (OpenAPI document).",
        "BMCAgent RF-01-008 acceptance policy: HTTP 404 with the explicit missing-URI message or HTTP 400 with matching Base.1.16.InvalidURI extended information is PASS with Note; invalid supplied documents and other errors retain their existing failure handling."
    ],
    "created_at": "2026-10-30T05:56:21.765986+00:00",
    "name": "RF-01-008 OpenAPI Document Endpoint",
    "description": "GET /redfish/v1/openapi.yaml and verify the minimum OpenAPI document structure.",
    "test_method": [
        {
            "step_1": (
                "Using Task BMC connection settings, GET /redfish/v1/openapi.yaml with "
                "Accept: application/yaml and a fixed 15-second request timeout. "
                "Record response URIs, status, headers and bodies. Follow supported "
                "same-origin redirects, detecting loops, up to five redirects."
            ),
            "criteria": (
                "HTTP 200 requires document validation. HTTP 404 is Pass with Note only for the exact JSON message: "
                "The URI /redfish/v1/openapi.yaml was not found. (DSP0266 1.25.0, "
                "section 6.7 Table 4, Required=No). HTTP 400 requires Base.1.16.InvalidURI and the same exact message in one extended-info entry. Content checks are skipped on accepted absence. Other HTTP errors, "
                "invalid Task settings, request failures or redirect boundary failures "
                "result in Fail with their specific reason. Redirect safeguards are "
                "provisional pending RF-02."
            ),
        },
        {
            "step_2": "Safely parse the final response body as a single YAML document.",
            "criteria": (
                "The body is valid YAML and its top-level value is an object (mapping). "
                "Invalid YAML, multiple documents or another top-level type result in Fail. "
                "A missing PyYAML dependency results in Error."
            ),
        },
        {
            "step_3": "Inspect the openapi, info and paths properties.",
            "criteria": (
                "openapi is a string, info is an object and paths is an object. "
                "Additional properties are allowed. All criteria met results in Pass; "
                "missing properties or incorrect types result in Fail. Full OpenAPI "
                "validation and API consistency belong to RF-03. Unexpected program "
                "problems result in Error."
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
                            "(should support). Accepted as PASS; document content was not validated.")
                    observations.update(initial_uri=urljoin(host, "/redfish/v1/openapi.yaml"),
                                        final_uri=url, redirect_count=hop, endpoint_provided=False,
                                        document_validated=False)
                    _log(context, "check", "Recommended OpenAPI endpoint", True,
                         expected="HTTP 200 preferred; absence is non-mandatory",
                         actual=actual, note=note)
                    return _finish(context, "Pass", "Optional OpenAPI endpoint absent; see Note",
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
