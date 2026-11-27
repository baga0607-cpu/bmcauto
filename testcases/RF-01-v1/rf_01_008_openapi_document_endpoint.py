TEST_CASE = {
    "modified_at": "2026-11-27T15:33:42.839835+08:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.7, Table 4 (/redfish/v1/openapi.yaml)",
        "DSP0266 v1.25.0 section 11.3.4, Table 33 (openapi.yaml terms)."
    ],
    "created_at": "2026-10-30T13:56:21.765986+08:00",
    "name": "RF-01-008 OpenAPI Document Endpoint",
    "description": "Verify the minimum OpenAPI document structure when the endpoint is available; conditionally accept explicitly confirmed absence of this optional endpoint.",
    "test_method": [
        {
            "step_number": 1,
            "step": "Send GET /redfish/v1/openapi.yaml and follow supported same-origin redirects.",
            "route": "bmc_redfish",
            "checkpoints": {
                "endpoint_status": {
                    "expected": "Verify the response using these acceptance rules:\n\n- PASS: HTTP 200.\n- C-PASS - HTTP 404: The message exactly matches \"The URI /redfish/v1/openapi.yaml was not found.\"\n- C-PASS - HTTP 400: A single @Message.ExtendedInfo entry contains both:\n  - MessageId: Base.1.16.InvalidURI\n  - Message: \"The URI /redfish/v1/openapi.yaml was not found.\" (exact match)\n- FAIL: Any other response.\n\nC-PASS is a project acceptance policy. Include the actual response and acceptance reason in Note, and skip the remaining document checks."
                }
            }
        },
        {
            "step_number": 2,
            "step": "Parse the response body as a single YAML document.",
            "checkpoints": {
                "yaml_parseable": {
                    "expected": "Verify that the response body can be parsed as YAML."
                },
                "top_level_object": {
                    "expected": "Verify that the top-level YAML value is an object."
                }
            }
        },
        {
            "step_number": 3,
            "step": "Read the openapi, info and paths properties.",
            "checkpoints": {
                "openapi_is_present_and_is_a_string": {
                    "expected": "Verify that openapi is present and is a string."
                },
                "info_is_present_and_is_an_object": {
                    "expected": "Verify that info is present and is an object."
                },
                "paths_is_present_and_is_an_object": {
                    "expected": "Verify that paths is present and is an object."
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
from urllib.parse import urljoin, urlsplit
from contextlib import ExitStack


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


import re

_CHECKS = [('(?:OpenAPI missing-URI evidence|OpenAPI missing-URI message|Recommended OpenAPI endpoint|Final HTTP '
  'status)',
  'endpoint_status'),
 ('Valid YAML', 'yaml_parseable'),
 ('Top-level YAML object', 'top_level_object'),
 ('openapi property type', 'openapi_is_present_and_is_a_string'),
 ('info property type', 'info_is_present_and_is_an_object'),
 ('paths property type', 'paths_is_present_and_is_an_object')]

class _Steps:
    def __init__(self, ctx, stack):
        self.ctx = ctx
        self.stack = stack
        self.number = None
        self.step = None
        self.seen = set()
        self.visited = set()
        self.failed = False

    def begin_step(self, number):
        if self.number != number:
            self.stack.close()
            self.step = self.stack.enter_context(self.ctx.step(number))
            self.number = number
            self.visited.add(number)

    def checkpoint(self, key, judgement, **detail):
        self.seen.add(key)
        self.failed |= judgement == "FAIL"
        self.step.checkpoint(key, judgement=judgement, **detail)

    def get(self, uri, *, headers, auth=None):
        options = {"headers": headers, "timeout": 15}
        if auth:
            options["auth"] = auth
        return self.step.redfish.get(uri, **options)

    def finish(self, status, reason, observations):
        for item in TEST_CASE["test_method"]:
            number = item["step_number"]
            if number not in self.visited and hasattr(self.ctx, "skip_step"):
                judgement = "Skip" if status == "C-PASS" else "Not executed"
                self.ctx.skip_step(number, judgement, reason)
                continue
            for key in item.get("checkpoints", {}):
                if key in self.seen:
                    continue
                self.begin_step(number)
                applicable = status not in ("Pass", "C-PASS")
                self.checkpoint(key, "Not executed" if applicable else "Skip",
                                reason=reason if applicable or status == "C-PASS" else "No applicable item was observed.")
        if status == "Error":
            raise RuntimeError(reason)
        if status == "Fail" and not self.failed:
            raise CaseFailure(reason)
        if status == "Block":
            self.ctx.block(reason)
        return observations

    def check(self, label, passed, **detail):
        key = next(key for pattern, key in _CHECKS if re.fullmatch(pattern, label))
        number = next(item["step_number"] for item in TEST_CASE["test_method"] if key in item.get("checkpoints", {}))
        self.begin_step(number)
        status = detail.pop("judgement", None) or ("C-PASS" if passed and detail.get("note") else "PASS" if passed else "FAIL")
        detail = {name: value for name, value in detail.items() if value is not None}
        detail["actual"] = {"source": label, "value": detail.get("actual", passed)}
        if status == "FAIL" and not detail.get("reason"):
            detail["reason"] = f"{label} did not meet the declared expectation."
        if status == "FAIL" and label in ("Valid JSON", "Valid XML", "Valid YAML", "XML parser safety boundary"):
            if hasattr(self.step, "operation_result"):
                self.step.operation_result(failure=detail["reason"])
        self.checkpoint(key, status, **detail)


def _origin(url):
    value = urlsplit(url)
    return (value.scheme.lower(), value.hostname,
            value.port or (443 if value.scheme == "https" else 80))


def _evaluate(flow):

    observations = {}
    flow.begin_step(1)
    try:
        host = flow.ctx.route_origin('bmc_redfish')
        parsed = urlsplit(host) if isinstance(host, str) else None
        valid = parsed is not None and parsed.scheme in ('http', 'https') and bool(parsed.hostname)
        valid = valid and (not parsed.username) and (not parsed.password)
        origin = _origin(host) if valid else None
    except ValueError:
        valid = False
    if not valid:
        return flow.finish('Fail', 'Task BMC URL is missing or invalid', observations)
    try:
        import requests
    except ImportError:
        return flow.finish('Error', 'Required requests package is unavailable', observations)
    url = urljoin(host, '/redfish/v1/openapi.yaml')
    reason = None
    try:
        session = flow.get
        seen = set()
        for hop in range(6):
            if url in seen:
                reason = 'Redirect loop detected'
                break
            seen.add(url)
            response = session(url, headers={'Accept': 'application/yaml'})

            if response.status_code in (301, 302, 307, 308):
                location = response.headers.get('Location')
                if not location:
                    reason = 'Redirect response has no Location'
                    break
                try:
                    target = urljoin(url, location)
                    target_parts = urlsplit(target)
                    leaves_origin = target_parts.username or target_parts.password or _origin(target) != origin
                except ValueError:
                    reason = 'Redirect URL is invalid'
                    break
                if leaves_origin:
                    reason = 'Redirect leaves Task origin; credentials were not forwarded'
                    break
                if hop == 5:
                    reason = 'Redirect limit exceeded (5 redirects)'
                    break
                url = target
                continue
            if response.status_code in (400, 404):
                try:
                    payload = json.loads(response.text)
                except ValueError:
                    payload = None
                error = payload.get('error', payload) if isinstance(payload, dict) else None
                message = error.get('message') if isinstance(error, dict) else None
                expected_message = 'The URI /redfish/v1/openapi.yaml was not found.'
                actual = {'status': response.status_code}
                if response.status_code == 400:
                    details = error.get('@Message.ExtendedInfo') if isinstance(error, dict) else None
                    matched = isinstance(details, list) and any((isinstance(entry, dict) and entry.get('MessageId') == 'Base.1.16.InvalidURI' and (entry.get('Message') == expected_message) for entry in details))
                    if not matched:
                        reason = 'Expected HTTP status = 200; Received HTTP status = 400'
                        flow.check('OpenAPI missing-URI evidence', False, expected={'MessageId': 'Base.1.16.InvalidURI', 'Message': expected_message}, actual=details)
                        break
                    actual['MessageId'] = 'Base.1.16.InvalidURI'
                    message = expected_message
                elif message != expected_message:
                    reason = 'HTTP 404 response did not confirm the missing OpenAPI URI'
                    flow.check('OpenAPI missing-URI message', False, expected=expected_message, actual=message)
                    break
                actual['message'] = message
                identifier = ' (Base.1.16.InvalidURI)' if response.status_code == 400 else ''
                note = f'DUT returned HTTP {response.status_code}{identifier} with message: "{message}" DSP0266 1.25.0 section 6.7 Table 4 marks it Required=No (should support). Accepted as C-PASS; document content was not validated.'
                observations.update(initial_uri=urljoin(host, '/redfish/v1/openapi.yaml'), final_uri=url, redirect_count=hop, endpoint_provided=False, document_validated=False)
                flow.check('Recommended OpenAPI endpoint', True, expected='HTTP 200 preferred; absence is non-mandatory', actual=actual, note=note)
                return flow.finish('C-PASS', 'Optional OpenAPI endpoint absent; document checks skipped', observations)
            flow.check('Final HTTP status', response.status_code == 200, expected=200, actual=response.status_code)
            if response.status_code != 200:
                reason = f'Expected HTTP status = 200; Received HTTP status = {response.status_code}'
                break
            observations.update(initial_uri=urljoin(host, '/redfish/v1/openapi.yaml'), final_uri=url, redirect_count=hop)
            flow.begin_step(2)
            try:
                import yaml
            except ImportError:
                return flow.finish('Error', 'Required PyYAML package is unavailable', observations)
            try:
                body = yaml.safe_load(response.text)
            except yaml.YAMLError:
                flow.check('Valid YAML', False, expected='One safe YAML document', actual='YAML parsing failed')
                reason = 'Response body is not a valid safe YAML document'
                break
            flow.check('Valid YAML', True)
            flow.check('Top-level YAML object', isinstance(body, dict), expected='object', actual=type(body).__name__)
            if not isinstance(body, dict):
                reason = 'Response body is not a YAML object'
                break
            flow.begin_step(3)
            failures = []
            for name, expected_type, type_name in (('openapi', str, 'string'), ('info', dict, 'object'), ('paths', dict, 'object')):
                present = name in body
                value = body.get(name)
                valid = present and isinstance(value, expected_type)
                flow.check(name + ' property type', valid, expected=type_name, actual=type(value).__name__ if present else 'missing')
                if not valid:
                    failures.append(name + ' must be ' + type_name)
            observations.update(endpoint_provided=True, document_validated=not failures)
            if failures:
                reason = 'OpenAPI document content mismatch: ' + '; '.join(failures)
            break
    except requests.RequestException as error:
        reason = f'HTTP request could not complete ({type(error).__name__})'
    except Exception as error:
        return flow.finish('Error', f'Unexpected program error ({type(error).__name__})', observations)
    return flow.finish('Fail' if reason else 'Pass', reason or 'OpenAPI endpoint returned HTTP 200 with string openapi and object info and paths', observations)


def run(ctx):
    with ExitStack() as stack:
        return _evaluate(_Steps(ctx, stack))


def execute(client, context=None, preset=None):
    from case_v1_context import execute_case
    return execute_case(TEST_CASE, run, context, preset, CaseFailure)
