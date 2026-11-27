TEST_CASE = {
    "modified_at": "2026-11-27T15:33:42.839835+08:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.7 Table 4",
        "DSP0266 v1.25.0 section 7.2.4",
        "DSP0266 v1.25.0 section 8.4.3 Table 15 (OData service document)."
    ],
    "created_at": "2026-10-19T09:53:55.572569+08:00",
    "name": "RF-01-003 OData Service Document Endpoint",
    "description": "GET /redfish/v1/odata and verify the metadata context and the minimum service document entry structure.",
    "test_method": [
        {
            "step_number": 1,
            "step": "Send GET /redfish/v1/odata and follow supported same-origin redirects.",
            "route": "bmc_redfish",
            "checkpoints": {
                "final_http_status": {
                    "expected": "Verify that the final HTTP status is 200."
                }
            }
        },
        {
            "step_number": 2,
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
            "step_number": 3,
            "step": "Read and resolve @odata.context against the response URI.",
            "checkpoints": {
                "metadata_context_uri_string": {
                    "expected": "Verify that @odata.context meets all conditions:\n- It is a string.\n- It is not empty.\n- It contains no whitespace or control characters."
                },
                "metadata_context_target": {
                    "expected": "Verify that @odata.context resolves to this service at /redfish/v1/$metadata."
                }
            }
        },
        {
            "step_number": 4,
            "step": "Read value and inspect each service document entry.",
            "checkpoints": {
                "value_is_an_array": {
                    "expected": "Verify that value is an array. An empty array is allowed."
                },
                "value_d_is_an_object": {
                    "expected": "Verify that each entry is an object."
                },
                "value_d_name_is_a_string": {
                    "expected": "Verify that each entry contains a string name."
                },
                "value_d_url_is_a_string": {
                    "expected": "Verify that each entry contains a string url."
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

_CHECKS = [('Final\\ HTTP\\ status', 'final_http_status'),
 ('Valid\\ JSON', 'valid_json'),
 ('Top\\-level\\ JSON\\ object', 'top_level_json_object'),
 ('Metadata\\ context\\ URI\\ string', 'metadata_context_uri_string'),
 ('Metadata\\ context\\ target', 'metadata_context_target'),
 ('value\\ is\\ an\\ array', 'value_is_an_array'),
 ('value\\[\\d+\\] is an object', 'value_d_is_an_object'),
 ('value\\[\\d+\\]\\.name is a string', 'value_d_name_is_a_string'),
 ('value\\[\\d+\\]\\.url is a string', 'value_d_url_is_a_string')]

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
    url = urljoin(host, '/redfish/v1/odata')
    reason = None
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
            flow.begin_step(2)
            try:
                body = json.loads(response.text)
            except ValueError:
                flow.check('Valid JSON', False)
                reason = 'Response body is not valid JSON'
                break
            flow.check('Valid JSON', True)
            flow.check('Top-level JSON object', isinstance(body, dict), expected='object', actual=type(body).__name__)
            if not isinstance(body, dict):
                reason = 'Response body is not a JSON object'
                break
            flow.begin_step(3)
            context_uri = body.get('@odata.context')
            if not isinstance(context_uri, str) or not context_uri or any((char.isspace() or ord(char) < 32 or ord(char) == 127 for char in context_uri)):
                flow.check('Metadata context URI string', False)
                reason = '@odata.context must be a nonempty URI string'
                break
            flow.check('Metadata context URI string', True, actual=context_uri)
            try:
                resolved = urljoin(url, context_uri)
                target_parts = urlsplit(resolved)
                valid_context = not target_parts.username and (not target_parts.password) and (_origin(resolved) == origin) and (target_parts.path == '/redfish/v1/$metadata')
            except ValueError:
                valid_context = False
            flow.check('Metadata context target', valid_context, expected='Task origin /redfish/v1/$metadata', actual=context_uri)
            if not valid_context:
                reason = '@odata.context does not resolve to this service /redfish/v1/$metadata'
                break
            observations['metadata_uri'] = resolved
            flow.begin_step(4)
            entries = body.get('value')
            flow.check('value is an array', isinstance(entries, list))
            if not isinstance(entries, list):
                reason = 'Service document value must be an array'
                break
            observations['entry_count'] = len(entries)
            for index, entry in enumerate(entries):
                flow.check(f'value[{index}] is an object', isinstance(entry, dict))
                if not isinstance(entry, dict):
                    reason = f'value[{index}] must be an object'
                    break
                flow.check(f'value[{index}].name is a string', isinstance(entry.get('name'), str))
                if not isinstance(entry.get('name'), str):
                    reason = f'value[{index}].name must be a string'
                    break
                flow.check(f'value[{index}].url is a string', isinstance(entry.get('url'), str))
                if not isinstance(entry.get('url'), str):
                    reason = f'value[{index}].url must be a string'
                    break
            break
    except requests.RequestException as error:
        reason = f'HTTP request could not complete ({type(error).__name__})'
    except Exception as error:
        return flow.finish('Error', f'Unexpected program error ({type(error).__name__})', observations)
    return flow.finish('Fail' if reason else 'Pass', reason or 'HTTP 200 with local metadata context and valid service document entries', observations)


def run(ctx):
    with ExitStack() as stack:
        return _evaluate(_Steps(ctx, stack))


def execute(client, context=None, preset=None):
    from case_v1_context import execute_case
    return execute_case(TEST_CASE, run, context, preset, CaseFailure)
