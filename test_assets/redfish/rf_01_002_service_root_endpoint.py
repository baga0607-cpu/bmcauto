import json
import math
import re
from urllib.parse import urljoin

TEST_CASE = {
    "modified_at": "2026-11-26T05:00:54.277898+00:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.6",
        "DSP0266 v1.25.0 section 6.7 Table 4",
        "DSP0266 v1.25.0 section 7.2.3 (ServiceRoot)",
        "DSP0266 v1.25.0 section 9.6.2 (resource identity)",
        "DSP0266 v1.25.0 section 9.6.3 (resource type)"
    ],
    "created_at": "2026-10-19T01:23:29.401576+00:00",
    "name": "RF-01-002 Service Root Endpoint",
    "description": "Verify that /redfish/v1/ returns a ServiceRoot JSON object with the expected resource URI. Record RedfishVersion if present, without evaluating its value.",
    "command_routes": {
        "bmc_redfish": {
            "from": "bmcagent",
            "to": "bmc",
            "method": "redfish",
            "lan_port": "task.bmc.lan_ports.port1",
            "username": "task.bmc.username",
            "password": "task.bmc.password"
        }
    },
    "test_method": [
        {
            "step_number": 1,
            "type": "Command",
            "route": "bmc_redfish",
            "step": "GET /redfish/v1/ and follow at most five same-origin 301, 302, 307 or 308 redirects. Check the final response.",
            "checkpoints": {
                "http_status": {
                    "expected": "Verify that the final response status is HTTP 200."
                }
            }
        },
        {
            "step_number": 2,
            "type": "Action",
            "step": "Parse the final response body as JSON.",
            "checkpoints": {
                "json_parseable": {
                    "expected": "Verify that the response body can be parsed as JSON."
                },
                "top_level_object": {
                    "expected": "Verify that the top-level JSON value is an object."
                }
            }
        },
        {
            "step_number": 3,
            "type": "Action",
            "step": "Read the `@odata.type` property from the JSON object.",
            "checkpoints": {
                "odata_type_is_string": {
                    "expected": "Verify that the `@odata.type` property exists and its value is a string."
                },
                "service_root_type_format": {
                    "expected": "Verify that @odata.type matches either accepted form:\n- #ServiceRoot.v<major>_<minor>_<errata>.ServiceRoot\n- #ServiceRoot.ServiceRoot\n\nIn the versioned form, each version component must contain one or more digits."
                }
            }
        },
        {
            "step_number": 4,
            "type": "Action",
            "step": "Read the `@odata.id` property from the JSON object.",
            "checkpoints": {
                "odata_id_is_string": {
                    "expected": "Verify that the `@odata.id` property exists and its value is a string."
                },
                "service_root_uri_exact": {
                    "expected": "Verify that the value equals `/redfish/v1/` exactly, including the trailing slash."
                }
            }
        },
        {
            "step_number": 5,
            "type": "Action",
            "step": "Read the `RedfishVersion` property if present."
        },
        {
            "step_number": 5,
            "type": "Record",
            "step": "Record the `RedfishVersion` value, or record \"Not present\" if the property is absent."
        }
    ],
    "automation": "automatic",
    "parameters": {}
}

ENDPOINT = "/redfish/v1/"

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


def execute(client, context=None, preset=None):
    """Use Task connection settings and keep typed method evidence in the Log."""
    if not isinstance(context, dict):
        raise RuntimeError("BMCAgent did not supply a dictionary execution context")
    from case_log import ReportedCase
    report = ReportedCase(context, TEST_CASE, CaseFailure)
    observations = {}
    report.begin_step(1)
    try:
        try:
            from redfish_route import RedfishRoute
            step = next(item for item in TEST_CASE["test_method"] if item["step_number"] == 1 and "route" in item)
            route = RedfishRoute(context, TEST_CASE["command_routes"][step["route"]])
            with route.traversal(redirect_statuses=(301, 302, 307, 308), max_redirects=5,
                                 allow_target=lambda uri: True, inspect_hop=lambda hop: None) as get:
                response = get(urljoin(route.host, ENDPOINT))
        except ValueError as error:
            reason = f"Step 1: {error}"
            report.operation_result(failure=reason)
        else:
            report.operation_result(actual={"final_uri": response.uri, "status": response.status})
            if response.status == 200:
                report.checkpoint("http_status", "PASS", expected=200, actual=response.status)
                reason = _inspect_response(report, response, observations)
            else:
                reason = f"Expected HTTP 200 but received HTTP {response.status}."
                report.checkpoint("http_status", "FAIL", expected=200, actual=response.status, reason=reason)
    except Exception as error:
        message = f"Step {report.log.method_step_number}: Unexpected program error ({type(error).__name__})"
        return report.finish(observations, error=message)
    return report.finish(observations, blocked=reason)


def _inspect_response(report, response, observations):
    report.begin_step(2)
    try:
        body = json.loads(response.text)
    except ValueError:
        reason = "Step 2: Response body cannot be parsed as JSON"
        report.operation_result(failure=reason)
        report.checkpoint("json_parseable", "FAIL", expected="Response body can be parsed as JSON",
                          actual="Parse failed", reason=reason)
        report.checkpoint("top_level_object", "Not executed", reason=reason)
        return reason
    top_level = type(body).__name__
    report.operation_result(actual={"top_level_type": top_level})
    report.checkpoint("json_parseable", "PASS", expected="Response body can be parsed as JSON", actual="Parsed")
    if not isinstance(body, dict):
        reason = "Step 2: Top-level JSON value is not an object"
        report.checkpoint("top_level_object", "FAIL", expected="object", actual=top_level, reason=reason)
        return reason
    report.checkpoint("top_level_object", "PASS", expected="object", actual=top_level)
    _inspect(report, body, observations)
    return ""


def _inspect(report, body, observations):
    report.begin_step(3)
    value = body.get("@odata.type")
    present = "@odata.type" in body
    report.operation_result(actual={"present": present, "value": _safe(value)})
    type_expected = "@odata.type exists and is a string"
    if isinstance(value, str):
        report.checkpoint("odata_type_is_string", "PASS", expected=type_expected, actual=value)
        valid = bool(re.fullmatch(r"#ServiceRoot(?:\.v[0-9]+_[0-9]+_[0-9]+)?\.ServiceRoot", value))
        report.checkpoint("service_root_type_format", "PASS" if valid else "FAIL",
                          expected="#ServiceRoot.v<major>_<minor>_<errata>.ServiceRoot (digits) or #ServiceRoot.ServiceRoot",
                          actual=value, reason="" if valid else
                          "The @odata.type value does not match either accepted ServiceRoot type format.")
    else:
        reason = "@odata.type is not a string." if present else "@odata.type is missing."
        report.checkpoint("odata_type_is_string", "FAIL", expected=type_expected,
                          actual=_safe(value) if present else "<missing>", reason=reason)
        report.checkpoint("service_root_type_format", "Not executed", reason=reason)

    report.begin_step(4)
    value = body.get("@odata.id")
    present = "@odata.id" in body
    report.operation_result(actual={"present": present, "value": _safe(value)})
    id_expected = "@odata.id exists and is a string"
    if isinstance(value, str):
        report.checkpoint("odata_id_is_string", "PASS", expected=id_expected, actual=value)
        valid = value == ENDPOINT
        report.checkpoint("service_root_uri_exact", "PASS" if valid else "FAIL", expected=ENDPOINT,
                          actual=value, reason="" if valid else
                          "The @odata.id value must equal /redfish/v1/ exactly, including the trailing slash.")
    else:
        reason = "@odata.id is not a string." if present else "@odata.id is missing."
        report.checkpoint("odata_id_is_string", "FAIL", expected=id_expected,
                          actual=_safe(value) if present else "<missing>", reason=reason)
        report.checkpoint("service_root_uri_exact", "Not executed", reason=reason)

    report.begin_step(5)
    present = "RedfishVersion" in body
    report.operation_result(actual={"present": present})
    if present:
        observations["RedfishVersion"] = _safe(body["RedfishVersion"])
    report.record(observations.get("RedfishVersion", "Not present"))
