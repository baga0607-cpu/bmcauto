TEST_CASE = {
    "modified_at": "2026-11-26T05:42:12.574147+00:00",
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
            "step": "Read the `RedfishVersion` property if present. Record the `RedfishVersion` value, or record \"Not present\" if the property is absent."
        }
    ],
    "automation": "automatic",
    "parameters": {}
}

import json
import math
import re
from urllib.parse import urljoin


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


def run(ctx):
    with ctx.step(1) as step:
        response = step.redfish.get(ENDPOINT, redirects="same_origin", timeout=15)
        status = response.status_code
        if hasattr(step, "operation_result"):
            step.operation_result(actual={"final_uri": getattr(response, "uri", ENDPOINT), "status": status})
        step.checkpoint("http_status", judgement="PASS" if status == 200 else "FAIL",
                        expected=200, actual=status)
    if status != 200:
        return
    with ctx.step(2) as step:
        try:
            body = json.loads(response.text)
        except ValueError:
            reason = "Response body cannot be parsed as JSON."
            if hasattr(step, "operation_result"):
                step.operation_result(failure=reason)
            step.checkpoint("json_parseable", judgement="FAIL", actual="Parse failed", reason=reason)
            step.checkpoint("top_level_object", judgement="Not executed", reason=reason)
            return
        if hasattr(step, "operation_result"):
            step.operation_result(actual={"top_level_type": type(body).__name__})
        step.checkpoint("json_parseable", judgement="PASS", actual="Parsed")
        step.checkpoint("top_level_object", judgement="PASS" if isinstance(body, dict) else "FAIL",
                        expected="JSON object", actual=type(body).__name__)
    if not isinstance(body, dict):
        return
    observations = {}
    with ctx.step(3) as step:
        value = body.get("@odata.type")
        present = "@odata.type" in body
        _operation(step, actual={"present": present, "value": _safe(value)})
        type_expected = "@odata.type exists and is a string"
        if isinstance(value, str):
            step.checkpoint("odata_type_is_string", judgement="PASS", expected=type_expected, actual=value)
            valid = bool(re.fullmatch(r"#ServiceRoot(?:\.v[0-9]+_[0-9]+_[0-9]+)?\.ServiceRoot", value))
            step.checkpoint("service_root_type_format", judgement="PASS" if valid else "FAIL",
                              expected="#ServiceRoot.v<major>_<minor>_<errata>.ServiceRoot (digits) or #ServiceRoot.ServiceRoot",
                              actual=value, reason="" if valid else
                              "The @odata.type value does not match either accepted ServiceRoot type format.")
        else:
            reason = "@odata.type is not a string." if present else "@odata.type is missing."
            step.checkpoint("odata_type_is_string", judgement="FAIL", expected=type_expected,
                              actual=_safe(value) if present else "<missing>", reason=reason)
            step.checkpoint("service_root_type_format", judgement="Not executed", reason=reason)

    with ctx.step(4) as step:
        value = body.get("@odata.id")
        present = "@odata.id" in body
        _operation(step, actual={"present": present, "value": _safe(value)})
        id_expected = "@odata.id exists and is a string"
        if isinstance(value, str):
            step.checkpoint("odata_id_is_string", judgement="PASS", expected=id_expected, actual=value)
            valid = value == ENDPOINT
            step.checkpoint("service_root_uri_exact", judgement="PASS" if valid else "FAIL", expected=ENDPOINT,
                              actual=value, reason="" if valid else
                              "The @odata.id value must equal /redfish/v1/ exactly, including the trailing slash.")
        else:
            reason = "@odata.id is not a string." if present else "@odata.id is missing."
            step.checkpoint("odata_id_is_string", judgement="FAIL", expected=id_expected,
                              actual=_safe(value) if present else "<missing>", reason=reason)
            step.checkpoint("service_root_uri_exact", judgement="Not executed", reason=reason)

    with ctx.step(5) as step:
        present = "RedfishVersion" in body
        _operation(step, actual={"present": present})
        if present:
            observations["RedfishVersion"] = _safe(body["RedfishVersion"])
        step.record(observations.get("RedfishVersion", "Not present"))

ENDPOINT = "/redfish/v1/"

def _safe(value):
    """Keep observations JSON-compatible without changing their judgement."""
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    if isinstance(value, dict):
        return {key: _safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe(item) for item in value]
    return value


def _operation(step, **detail):
    if hasattr(step, "operation_result"):
        step.operation_result(**detail)


def execute(client, context=None, preset=None):
    from case_v1_context import execute_case
    return execute_case(TEST_CASE, run, context, preset, CaseFailure,
                        [(5, 'Record the `RedfishVersion` value, or record "Not present" if the property is absent.')])
