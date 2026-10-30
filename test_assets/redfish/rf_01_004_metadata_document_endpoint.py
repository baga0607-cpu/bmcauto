import json
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET

TEST_CASE = {
    "created_at": '2026-10-19T03:27:51.085627+00:00',
    "name": "RF-01-004 Metadata Document Endpoint",
    "description": (
        "GET /redfish/v1/$metadata and verify the minimum XML Edmx document identity."
    ),
    "test_method": [
        {
            "step_1": (
                "Using Task BMC connection settings, send GET /redfish/v1/$metadata "
                "with Accept: application/xml and a fixed 15-second request timeout. "
                "Record each response URI, status, headers and body. Follow supported "
                "same-origin redirects, detecting loops, up to five redirects."
            ),
            "criteria": (
                "The final HTTP status is 200. Invalid Task settings, request failure "
                "or rejected redirects result in Fail with a reason. Redirect safeguards "
                "are provisional pending RF-02; a boundary failure alone does not "
                "establish a DMTF violation."
            ),
        },
        {
            "step_2": "Parse the final response bytes as XML using its declared encoding.",
            "criteria": (
                "The body is valid XML. Malformed XML results in Fail. Documents with "
                "a DTD are not processed by this parser safeguard and result in Fail "
                "with an explicit reason, not a claim of a DMTF violation."
            ),
        },
        {
            "step_3": "Inspect the root element local name, namespace and Version attribute.",
            "criteria": (
                "The root local name is Edmx, its namespace is "
                "http://docs.oasis-open.org/odata/ns/edmx, and its unqualified Version "
                "attribute is exactly 4.0. XML prefixes are not fixed. Additional "
                "attributes and children are allowed. All criteria met results in Pass; "
                "a mismatch results in Fail with a reason. Schema references, "
                "EntityContainer and definition completeness belong to RF-03. "
                "Unexpected program problems or missing dependencies result in Error."
            ),
        },
    ],
    "automation": "automatic",
    "parameters": {},
}


class UnsupportedDTD(ValueError):
    """Parser boundary; do not resolve or expand DTD entities."""


class MetadataTreeBuilder(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise UnsupportedDTD("DTD processing is disabled")


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


def _finish(context, status, reason, evidence, observations):
    _report_finish(context, status, reason)
    context["case_result"] = {
        "status": status, "reason": reason, "evidence": evidence,
        "observations": observations,
    }
    # Compatibility with the current runner; it still stores Error as Failed.
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
                    reason = f"Expected HTTP 200, received {response.status_code}"
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
                        failures.append(f"{label}: expected {expected!r}, received {actual!r}")
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
