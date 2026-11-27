TEST_CASE = {
    "modified_at": "2026-11-27T15:33:42.839835+08:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.6 (protocol/version discovery)",
        "DSP0266 v1.25.0 section 6.7 Table 4 (/redfish)."
    ],
    "created_at": "2026-10-14T15:32:57.063413+08:00",
    "name": "RF-01-001 Version Discovery Endpoint",
    "description": "Verify that /redfish returns a valid JSON object whose v1 property equals /redfish/v1/.",
    "test_method": [
        {
            "step_number": 1,
            "step": "Send a GET request to `/redfish`.",
            "route": "bmc_redfish",
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
            "step": "Read the `v1` property from the JSON object.",
            "checkpoints": {
                "v1_present": {
                    "expected": "Verify that the `v1` property exists."
                },
                "v1_string": {
                    "expected": "Verify that the `v1` value is a string."
                },
                "v1_uri": {
                    "expected": "Verify that the `v1` value equals `/redfish/v1/` exactly, including the trailing slash."
                }
            }
        }
    ],
    "automation": "automatic",
    "parameters": {},
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

import json
import math
import re
from urllib.parse import urljoin, urlsplit


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

    with ctx.step(3) as step:
        present = "v1" in body
        value = body.get("v1")
        step.checkpoint("v1_present", judgement="PASS" if present else "FAIL", actual=present)
        if present:
            step.checkpoint("v1_string", judgement="PASS" if isinstance(value, str) else "FAIL",
                            actual=type(value).__name__)
        else:
            step.checkpoint("v1_string", judgement="Not executed", reason="The v1 property is missing.")
        if isinstance(value, str):
            step.checkpoint("v1_uri", judgement="PASS" if value == "/redfish/v1/" else "FAIL",
                            expected="/redfish/v1/", actual=value)
        else:
            step.checkpoint("v1_uri", judgement="Not executed", reason="No v1 string is available.")


ENDPOINT = "/redfish"


def execute(client, context=None, preset=None):
    from case_v1_context import execute_case
    return execute_case(TEST_CASE, run, context, preset, CaseFailure)
