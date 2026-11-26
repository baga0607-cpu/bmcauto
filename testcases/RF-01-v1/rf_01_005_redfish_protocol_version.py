TEST_CASE = {
    "modified_at": "2026-11-26T05:42:12.574147+00:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.6 (RedfishVersion format)."
    ],
    "created_at": "2026-10-19T03:32:23.623177+00:00",
    "name": "RF-01-005 Redfish Protocol Version",
    "description": "Verify that ServiceRoot RedfishVersion exactly matches the tester-provided protocol version.",
    "test_method": [
        {
            "step_number": 1,
            "step": "Read the expected RedfishVersion from the preset, or ask the tester if it is blank.",
            "checkpoints": {
                "tester_supplied_expected_version": {
                    "expected": "Verify that a nonblank expected version string was supplied."
                }
            }
        },
        {
            "step_number": 2,
            "step": "Send GET /redfish/v1/ and follow supported same-origin redirects.",
            "route": "bmc_redfish",
            "checkpoints": {
                "final_http_status": {
                    "expected": "Verify that the final HTTP status is 200."
                }
            }
        },
        {
            "step_number": 3,
            "step": "Parse the response body as JSON.",
            "checkpoints": {
                "valid_json": {
                    "expected": "Verify that the response body can be parsed as JSON."
                },
                "top_level_json_object": {
                    "expected": "Verify that the top-level JSON value is an object."
                }
            }
        },
        {
            "step_number": 4,
            "step": "Read the RedfishVersion property.",
            "checkpoints": {
                "redfishversion_is_present": {
                    "expected": "Verify that RedfishVersion is present."
                },
                "redfishversion_format": {
                    "expected": "Verify that RedfishVersion uses the format major.minor.errata:\n- The value is a string.\n- It contains exactly three components separated by dots.\n- Each component contains one or more decimal digits."
                }
            }
        },
        {
            "step_number": 5,
            "step": "Compare RedfishVersion with the expected version without normalization.",
            "checkpoints": {
                "exact_redfishversion_match": {
                    "expected": "Verify that RedfishVersion exactly matches the tester-supplied version.\n\nProject acceptance policy:\n- Compare the strings without normalization.\n- The tester defines the expected version; DMTF does not prescribe that value."
                }
            }
        }
    ],
    "automation": "semi_automatic",
    "parameters": {
        "preset": {
            "type": "string",
            "default": "",
            "label": "Expected RedfishVersion (blank: ask during execution)"
        }
    },
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
import re
from urllib.parse import urljoin, urlsplit
from contextlib import ExitStack


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


_CHECKS = [('Tester\\ supplied\\ expected\\ version', 'tester_supplied_expected_version'),
 ('Final\\ HTTP\\ status', 'final_http_status'),
 ('Valid\\ JSON', 'valid_json'),
 ('Top\\-level\\ JSON\\ object', 'top_level_json_object'),
 ('RedfishVersion\\ is\\ present', 'redfishversion_is_present'),
 ('RedfishVersion\\ format', 'redfishversion_format'),
 ('Exact\\ RedfishVersion\\ match', 'exact_redfishversion_match')]

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
    settings = getattr(flow.ctx, 'parameters', {})
    if not isinstance(settings, dict):
        return flow.finish('Error', 'Plan case_settings must be a dictionary', observations)
    expected = settings.get('preset', '')
    source = 'preset'
    if expected is None or (isinstance(expected, str) and (not expected.strip())):
        source = 'interactive'
        try:
            expected = input('Expected RedfishVersion (major.minor.errata): ')
        except EOFError:
            expected = ''
    observations['expected_version_source'] = source
    supplied = isinstance(expected, str) and bool(expected.strip())
    flow.check('Tester supplied expected version', supplied, actual=expected)
    if not supplied:
        reason = 'Tester did not provide a version number' if expected is None or isinstance(expected, str) else 'Tester-provided version must be a string'
        return flow.finish('Fail', reason, observations)
    observations['expected_RedfishVersion'] = expected
    flow.begin_step(2)
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
    url = urljoin(host, '/redfish/v1/')
    reason = None
    flow.begin_step(2)
    try:
        session = flow.get
        seen = set()
        for hop in range(6):
            if url in seen:
                reason = 'Redirect loop detected'
                break
            seen.add(url)
            response = session(url, headers={'Accept': 'application/json'})

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
            flow.check('Final HTTP status', response.status_code == 200, expected=200, actual=response.status_code)
            if response.status_code != 200:
                reason = f'Expected HTTP status = 200; Received HTTP status = {response.status_code}'
                break
            flow.begin_step(3)
            try:
                body = json.loads(response.text)
            except ValueError:
                flow.check('Valid JSON', False)
                reason = 'Response body is not valid JSON'
                break
            flow.check('Valid JSON', True)
            flow.check('Top-level JSON object', isinstance(body, dict), expected='object', actual=type(body).__name__)
            flow.begin_step(4)
            if not isinstance(body, dict):
                reason = 'Response body is not a JSON object'
                break
            present = 'RedfishVersion' in body
            flow.check('RedfishVersion is present', present)
            if not present:
                reason = 'ServiceRoot did not provide RedfishVersion'
                break
            actual = body['RedfishVersion']
            observations['RedfishVersion'] = actual
            valid_version = isinstance(actual, str) and bool(re.fullmatch('[0-9]+\\.[0-9]+\\.[0-9]+', actual))
            flow.check('RedfishVersion format', valid_version, expected='major.minor.errata (decimal integers)', actual=actual)
            if not valid_version:
                reason = 'RedfishVersion format does not meet requirements'
                break
            flow.begin_step(5)
            flow.check('Exact RedfishVersion match', actual == expected, expected=expected, actual=actual)
            if actual != expected:
                reason = f'RedfishVersion does not match the expected version: expected={expected!r}, actual={actual!r}'
            break
    except requests.RequestException as error:
        reason = f'HTTP request could not complete ({type(error).__name__})'
    except Exception as error:
        return flow.finish('Error', f'Unexpected program error ({type(error).__name__})', observations)
    return flow.finish('Fail' if reason else 'Pass', reason or 'HTTP 200 with valid RedfishVersion exactly matching tester expectation', observations)


def run(ctx):
    with ExitStack() as stack:
        return _evaluate(_Steps(ctx, stack))


def execute(client, context=None, preset=None):
    from case_v1_context import execute_case
    return execute_case(TEST_CASE, run, context, preset, CaseFailure)
