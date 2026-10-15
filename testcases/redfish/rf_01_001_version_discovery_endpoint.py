import json
from urllib.parse import urljoin, urlsplit

TEST_CASE = {
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


def _finish(context, status, reason, evidence):
    context["case_result"] = {
        "status": status, "reason": reason, "evidence": evidence,
    }
    context["_tc_status"] = "PASS" if status == "Pass" else "FAIL"
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
                print("HTTP evidence: " + json.dumps(item, ensure_ascii=False))
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
                if response.status_code != 200:
                    reason = f"Expected HTTP 200, received {response.status_code}"
                    break
                try:
                    body = json.loads(response.text)
                except ValueError:
                    reason = "Response body is not valid JSON"
                    break
                if not isinstance(body, dict):
                    reason = "Response body is not a JSON object"
                elif "v1" not in body:
                    reason = "Response has no v1 property"
                elif not isinstance(body["v1"], str) or body["v1"] != "/redfish/v1/":
                    reason = f"Expected v1='/redfish/v1/', received {body['v1']!r}"
                break
    except requests.RequestException as error:
        reason = f"HTTP request could not complete ({type(error).__name__})"
    except ValueError:
        reason = "Redirect URL is invalid"
    except Exception as error:
        return _finish(context, "Error", f"Unexpected program error ({type(error).__name__})", evidence)
    return _finish(context, "Fail" if reason else "Pass",
                   reason or "HTTP 200 with v1='/redfish/v1/'", evidence)
