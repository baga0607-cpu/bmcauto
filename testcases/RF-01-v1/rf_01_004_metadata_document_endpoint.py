TEST_CASE = {
    "modified_at": "2026-11-27T15:33:42.839835+08:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.7 Table 4",
        "DSP0266 v1.25.0 section 7.2.4 (OData metadata)",
        "DSP0266 v1.25.0 section 8.4.2 (OData metadata)",
        "DSP0266 v1.25.0 section 11.1.4 (CSDL format)."
    ],
    "created_at": "2026-10-19T11:27:51.085627+08:00",
    "name": "RF-01-004 Metadata Document Endpoint",
    "description": "GET /redfish/v1/$metadata and verify the minimum XML Edmx document identity.",
    "test_method": [
        {
            "step_number": 1,
            "step": "Send GET /redfish/v1/$metadata and follow supported same-origin redirects.",
            "route": "bmc_redfish",
            "checkpoints": {
                "final_http_status": {
                    "expected": "Verify that the final HTTP status is 200."
                }
            }
        },
        {
            "step_number": 2,
            "step": "Parse the response bytes as XML using the declared encoding.",
            "checkpoints": {
                "xml_parser_safety_boundary": {
                    "expected": "Verify that the XML document contains no DTD declaration.\n\nThis is a parser safeguard: DTD processing is disabled."
                },
                "valid_xml": {
                    "expected": "Verify that the response body can be parsed as XML."
                }
            }
        },
        {
            "step_number": 3,
            "step": "Read the root element name, namespace and Version attribute.",
            "checkpoints": {
                "root_local_name": {
                    "expected": "Verify that the root local name is Edmx."
                },
                "root_namespace": {
                    "expected": "Verify that the root namespace is http://docs.oasis-open.org/odata/ns/edmx."
                },
                "edmx_version_attribute": {
                    "expected": "Verify that the root element has a Version attribute with:\n- No namespace prefix.\n- The exact value \"4.0\"."
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
import xml.etree.ElementTree as ET
from contextlib import ExitStack


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


import re

_CHECKS = [('Final\\ HTTP\\ status', 'final_http_status'),
 ('XML\\ parser\\ safety\\ boundary', 'xml_parser_safety_boundary'),
 ('Valid\\ XML', 'valid_xml'),
 ('Root\\ local\\ name', 'root_local_name'),
 ('Root\\ namespace', 'root_namespace'),
 ('Edmx\\ Version\\ attribute', 'edmx_version_attribute')]

class UnsupportedDTD(ValueError):
    """Parser boundary; do not resolve or expand DTD entities."""

class MetadataTreeBuilder(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise UnsupportedDTD("DTD processing is disabled")


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
    url = urljoin(host, '/redfish/v1/$metadata')
    reason = None
    try:
        session = flow.get
        seen = set()
        for hop in range(6):
            if url in seen:
                reason = 'Redirect loop detected'
                break
            seen.add(url)
            response = session(url, headers={'Accept': 'application/xml'})

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
                body = ET.fromstring(response.content, parser=ET.XMLParser(target=MetadataTreeBuilder()))
            except UnsupportedDTD:
                flow.check('XML parser safety boundary', False, expected='No DTD processing', actual='DTD declaration')
                reason = 'XML DTD processing is disabled; document not validated (parser safeguard)'
                break
            except (ET.ParseError, LookupError, ValueError) as error:
                flow.check('Valid XML', False, actual=str(error))
                reason = f'Response body could not be parsed as XML ({type(error).__name__})'
                break
            flow.check('XML parser safety boundary', True, expected='No DTD processing', actual='No DTD processed')
            flow.check('Valid XML', True)
            flow.begin_step(3)
            namespace, local_name = ('', body.tag)
            if body.tag.startswith('{'):
                namespace, local_name = body.tag[1:].split('}', 1)
            version = body.get('Version')
            observations.update(root_local_name=local_name, root_namespace=namespace, edmx_version=version)
            checks = [('Root local name', local_name, 'Edmx'), ('Root namespace', namespace, 'http://docs.oasis-open.org/odata/ns/edmx'), ('Edmx Version attribute', version, '4.0')]
            failures = []
            for label, actual, expected in checks:
                passed = actual == expected
                flow.check(label, passed, expected=expected, actual=actual)
                if not passed:
                    failures.append(f'Expected {label} = {expected!r}; Received {label} = {actual!r}')
            reason = '; '.join(failures) or None
            break
    except requests.RequestException as error:
        reason = f'HTTP request could not complete ({type(error).__name__})'
    except Exception as error:
        return flow.finish('Error', f'Unexpected program error ({type(error).__name__})', observations)
    return flow.finish('Fail' if reason else 'Pass', reason or 'HTTP 200 with XML Edmx root, OData namespace and Version 4.0', observations)


def run(ctx):
    with ExitStack() as stack:
        return _evaluate(_Steps(ctx, stack))


def execute(client, context=None, preset=None):
    from case_v1_context import execute_case
    return execute_case(TEST_CASE, run, context, preset, CaseFailure)
