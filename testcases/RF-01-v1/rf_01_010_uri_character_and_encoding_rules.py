TEST_CASE = {
    "modified_at": "2026-11-26T05:42:12.574147+00:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.1 (URI characters and percent encoding).",
        "RFC 3986 section 2.1 (encoding, IPv6 authority and fragments)",
        "RFC 3986 section 3.2.2 (encoding, IPv6 authority and fragments)",
        "RFC 3986 section 3.5 (encoding, IPv6 authority and fragments)",
        "RFC 6901 section 3 (JSON Pointer escapes).",
        "RFC 6901 section 6 (JSON Pointer escapes)."
    ],
    "created_at": "2026-10-30T06:16:31.055575+00:00",
    "name": "RF-01-010 URI Character and Encoding Rules",
    "description": "Inspect original resource URI references discovered from ServiceRoot for unsafe characters, fragment delimiters and percent-encoding outside query components.",
    "test_method": [
        {
            "step_number": 1,
            "step": "Prepare a read-only traversal of the service.",
            "checkpoints": {
                "task_origin_available": {
                    "expected": "Verify that a valid HTTP(S) service origin is available."
                }
            }
        },
        {
            "step_number": 2,
            "step": "GET discoverable local resources and collection pages from /redfish/v1/. Do not invoke Actions or fetch external services.",
            "route": "bmc_redfish",
            "checkpoints": {
                "traversal_complete": {
                    "expected": "Verify that traversal completed without:\n- Resources that could not be read.\n- Invalid links.\n- Pagination errors."
                }
            }
        },
        {
            "step_number": 3,
            "step": "Inspect original URI components before normalization.",
            "checkpoints": {
                "original_uri_character_and_encoding_rules": {
                    "expected": "Verify each original URI reference against these rules:\n- The value is a nonempty string.\n- No raw whitespace, control characters or non-ASCII characters.\n- No unsafe characters: <, >, \", {, }, |, \\, ^, ~, [, ], or backtick, except as allowed below.\n- Percent encoding is allowed only in the query component. Each % must be followed by two hexadecimal digits.\n- Square brackets are allowed around a valid IPv6 address in the authority.\n- ~0 and ~1 are allowed in the fragment for JSON Pointer escaping.\n- No additional raw # inside the fragment."
                },
                "scope_sufficient_for_pass": {
                    "expected": "Verify that the complete discovered scope was assessed."
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

import ipaddress
import json
import re
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit
from contextlib import ExitStack


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


_CHECKS = [('Task\\ origin\\ available', 'task_origin_available'),
 ('Traversal\\ evidence\\ available', 'traversal_complete'),
 ('Traversal\\ complete', 'traversal_complete'),
 ('Original\\ URI\\ character\\ and\\ encoding\\ rules', 'original_uri_character_and_encoding_rules'),
 ('Scope\\ sufficient\\ for\\ Pass', 'scope_sufficient_for_pass')]

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
        self.checkpoint(key, status, **detail)


def _origin(url):
    value = urlsplit(url)
    return (value.scheme.lower(), value.hostname,
            value.port or (443 if value.scheme == "https" else 80))


def _url(reference, base):
    if not isinstance(reference, str) or not reference or any(c.isspace() for c in reference):
        raise ValueError("Empty, non-string or whitespace-containing URI")
    target = urljoin(base, reference)
    parts = urlsplit(target)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("Invalid HTTP resource URI")
    origin = _origin(target)
    # Normalize only authority spelling/default ports; preserve path case and query.
    hostname = parts.hostname
    authority = "[" + hostname + "]" if ":" in hostname else hostname
    if origin[2] != (443 if parts.scheme == "https" else 80):
        authority += ":" + str(origin[2])
    return urlunsplit((parts.scheme, authority, parts.path or "/", parts.query, ""))


def _uri_issues(raw):
    """Inspect the original string before urlsplit can strip control characters."""
    if not isinstance(raw, str) or not raw:
        return [{"rule": "URI string", "detail": "Expected a non-empty string"}]
    issues = []
    before_fragment, delimiter, fragment = raw.partition("#")
    before_query, query_delimiter, query = before_fragment.partition("?")
    components = [("resource", before_query, 0)]
    if query_delimiter:
        components.append(("query", query, len(before_query) + 1))
    if delimiter:
        components.append(("fragment", fragment, len(before_fragment) + 1))
        if "#" in fragment:
            issues.append({"rule": "Fragment delimiter", "detail": "Additional raw # inside fragment"})
    # RFC3986 IP-literal brackets are syntax, not resource path characters.
    bracket_positions = set()
    match = re.match('^(?:[A-Za-z][A-Za-z0-9+.-]*:)?//(\\[[^]]+\\])', before_query)
    if match:
        literal = match.group(1)
        try:
            ipaddress.IPv6Address(literal[1:-1])
            if "%" not in literal:
                bracket_positions = {match.start(1), match.end(1) - 1}
        except ValueError:
            pass
    unsafe = set('<>"{}|\\^~[]`')
    for component, value, offset in components:
        for index, char in enumerate(value):
            absolute_index = offset + index
            if ord(char) <= 32 or ord(char) >= 127:
                issues.append({"rule": "Unsafe character", "component": component,
                               "offset": absolute_index, "detail": "Raw whitespace, control or non-ASCII character"})
            elif char in unsafe:
                if absolute_index in bracket_positions:
                    continue
                if component == "fragment" and char == "~" and value[index + 1:index + 2] in ("0", "1"):
                    continue
                issues.append({"rule": "Unsafe character", "component": component,
                               "offset": absolute_index, "detail": "RFC1738 unsafe character " + repr(char)})
            elif char == "%":
                valid = re.fullmatch(r"[0-9A-Fa-f]{2}", value[index + 1:index + 3]) is not None
                if not valid:
                    issues.append({"rule": "Percent escape", "component": component,
                                   "offset": absolute_index, "detail": "Malformed percent escape"})
                elif component != "query":
                    issues.append({"rule": "Percent encoding outside query", "component": component,
                                   "offset": absolute_index, "detail": value[index:index + 3]})
    return issues


def _links(body):
    """Recognize explicit protocol URI fields; do not scan arbitrary prose."""
    stack = [(body, "$", False)]
    while stack:
        value, field, in_actions = stack.pop()
        if isinstance(value, dict):
            for key, child in value.items():
                location = field + "/" + key.replace("~", "~0").replace("/", "~1")
                actions = in_actions or key == "Actions"
                if key == "@odata.id":
                    yield ("action" if in_actions else "resource"), child, location
                elif key == "@odata.nextLink" or key.endswith("@odata.nextLink"):
                    yield ("action" if in_actions else "page"), child, location
                elif in_actions and key == "target":
                    yield "action", child, location
                elif key == "@Redfish.ActionInfo":
                    yield "action", child, location
                elif key == "@odata.context":
                    yield "context", child, location
                elif isinstance(child, (dict, list)):
                    stack.append((child, location, actions))
        elif isinstance(value, list):
            stack.extend((child, field + "/" + str(index), in_actions)
                         for index, child in enumerate(value))


def _reject_json_constant(value):
    raise ValueError("Non-finite JSON constant: " + value)


def _fetch(session, url, origin, cache, inspect_uri):
    chain = []
    current = url
    try:
        for hop in range(6):
            if current in chain:
                raise CaseFailure('Redirect loop detected')
            if current in cache:
                result = cache[current]
                if isinstance(result, Exception):
                    raise result
                for alias in chain:
                    cache[alias] = result
                return result
            chain.append(current)
            response = session(current, headers={'Accept': 'application/json'})
            headers = {k: v for k, v in response.headers.items() if k.lower() not in ('set-cookie', 'authorization', 'x-auth-token')}

            location_issues = []
            if response.headers.get('Location') is not None:
                location_issues = inspect_uri(response.headers.get('Location'), current, 'headers/Location', 'header')
            if response.status_code in (301, 302, 307, 308):
                location = response.headers.get('Location')
                if not location:
                    raise CaseFailure('Redirect response has no Location')
                if location_issues:
                    raise CaseFailure('Advertised redirect URI violates character or encoding rules')
                try:
                    target = _url(location, current)
                except ValueError:
                    raise CaseFailure('Redirect URL is invalid') from None
                if _origin(target) != origin:
                    raise CaseFailure('Redirect leaves Task origin; credentials were not forwarded')
                if '/Actions/' in urlsplit(target).path or urlsplit(target).path.endswith('/Actions'):
                    raise CaseFailure('Redirect to an Action endpoint was not followed')
                if hop == 5:
                    raise CaseFailure('Redirect limit exceeded (5 redirects)')
                current = target
                continue
            if response.status_code != 200:
                raise CaseFailure(f'Expected HTTP status = 200; Received HTTP status = {response.status_code}')
            try:
                body = json.loads(response.text, parse_constant=_reject_json_constant)
            except ValueError:
                raise CaseFailure('Response body is not valid JSON') from None
            if not isinstance(body, dict):
                raise CaseFailure('Response body is not a JSON object')
            result = (current, body)
            for alias in chain:
                cache[alias] = result
            return result
        raise CaseFailure('Redirect could not complete')
    except Exception as error:
        for attempted in chain:
            cache[attempted] = error
        raise


def _has_page_cycle(edges):
    """Topological reduction avoids recursion on large pagination graphs."""
    incoming = {}
    outgoing = {}
    for source, target in edges:
        incoming.setdefault(source, 0)
        incoming[target] = incoming.get(target, 0) + 1
        outgoing.setdefault(source, []).append(target)
    ready = deque(node for node, count in incoming.items() if count == 0)
    removed = 0
    while ready:
        node = ready.popleft()
        removed += 1
        for target in outgoing.get(node, []):
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)
    return removed != len(incoming)


def _evaluate(flow):

    observations = {'resources': [], 'uris': [], 'violations': [], 'excluded': [], 'unread': [], 'scope': 'Structured resource/page links, Action references, OData context and Location'}
    flow.begin_step(1)
    try:
        host = _url(flow.ctx.route_origin('bmc_redfish'), '')
        origin = _origin(host)
    except (ValueError, TypeError):
        return flow.finish('Fail', 'Task BMC URL is missing or invalid', observations)
    try:
        import requests
    except ImportError:
        return flow.finish('Error', 'Required requests package is unavailable', observations)
    flow.check('Task origin available', True, expected='HTTP(S) origin', actual=urlunsplit((urlsplit(host).scheme, urlsplit(host).netloc, '', '', '')))
    root = _url('/redfish/v1/', host)
    queue, scheduled, cache = (deque([root]), {root}, {})
    resources, aliases, page_edges = (set(), {}, set())
    errors = observations['unread']

    def unread(uri, reason, source=None):
        errors.append({'uri': uri, 'source': source, 'reason': reason})
        flow.check('Traversal evidence available', False, expected='Readable in-scope resource or page', actual=errors[-1])

    def inspect_uri(raw, source, field, kind):
        issues = _uri_issues(raw)
        item = {'source': source, 'field': field, 'uri': raw, 'kind': kind, 'issues': issues}
        observations['uris'].append(item)
        if issues:
            observations['violations'].append(item)
        return issues
    flow.begin_step(2)
    try:
        session = flow.get
        while queue:
            requested = queue.popleft()
            try:
                final, body = _fetch(session, requested, origin, cache, inspect_uri)
            except (CaseFailure, requests.RequestException) as error:
                reason = str(error) if isinstance(error, CaseFailure) else 'HTTP request could not complete (' + type(error).__name__ + ')'
                cache[requested] = CaseFailure(reason)
                unread(requested, reason)
                continue
            aliases[requested] = final
            if final in resources:
                continue
            resources.add(final)
            observations['resources'].append({'request_uri': requested, 'final_uri': final})
            if '@odata.id' not in body:
                unread(final, 'Missing top-level @odata.id; resource URI evidence is incomplete')
            if requested == root and (not (isinstance(body.get('@odata.type'), str) and re.fullmatch('#ServiceRoot(?:\\.v[0-9]+_[0-9]+_[0-9]+)?\\.ServiceRoot', body['@odata.type']))):
                unread(final, 'Starting endpoint does not identify ServiceRoot')
            for kind, reference, field in _links(body):
                issues = inspect_uri(reference, final, field, kind)
                source = {'resource': final, 'field': field}
                if kind in ('action', 'context'):
                    observations['excluded'].append({'source': source, 'uri': reference, 'reason': 'Inspected only; no Action or metadata request'})
                    continue
                if issues:
                    unread(final, 'Invalid advertised URI was not requested', source)
                    continue
                try:
                    target = _url(reference, final)
                except (ValueError, TypeError):
                    unread(final, 'Resource URI could not be resolved', source)
                    continue
                if _origin(target) != origin:
                    observations['excluded'].append({'source': source, 'uri': reference, 'reason': 'External service; reference inspected, not traversed'})
                    continue
                if '/Actions/' in urlsplit(target).path or urlsplit(target).path.endswith('/Actions'):
                    observations['excluded'].append({'source': source, 'uri': reference, 'reason': 'Action endpoint is not invoked'})
                    continue
                if kind == 'page':
                    page_edges.add((final, target))
                if target not in scheduled:
                    scheduled.add(target)
                    queue.append(target)
        if _has_page_cycle({(aliases.get(a, a), aliases.get(b, b)) for a, b in page_edges}):
            unread(root, 'Collection pagination cycle detected')
        flow.check('Traversal complete', not errors, expected='No unread in-scope resources or pages', actual={'resources': len(resources), 'unread': errors, 'excluded': observations['excluded']})
        if not observations['uris']:
            return flow.finish('Fail', 'No service-provided URI evidence was obtained', observations)
        flow.begin_step(3)
        for item in observations['uris']:
            flow.check('Original URI character and encoding rules', not item['issues'], expected='Safe URI components; percent encoding only in query', actual=item)
        observations['resource_response_count'] = len(resources)
        observations['uri_occurrence_count'] = len(observations['uris'])
        observations['traversal_complete'] = not errors
        flow.check('Scope sufficient for Pass', not errors, expected='Complete discovered scope', actual={'unread': errors})
    except CaseFailure:
        raise
    except Exception as error:
        observations['pending'] = list(queue)
        return flow.finish('Error', 'Unexpected program error (' + type(error).__name__ + ')', observations)
    failed = bool(errors or observations['violations'])
    reason = f"URI violations: {len(observations['violations'])}; traversal issues: {len(errors)}." if failed else f"No URI character or encoding violations in {len(observations['uris'])} URI occurrences from {len(resources)} resource/page responses in the discovered scope."
    return flow.finish('Fail' if failed else 'Pass', reason, observations)


def run(ctx):
    with ExitStack() as stack:
        return _evaluate(_Steps(ctx, stack))


def execute(client, context=None, preset=None):
    from case_v1_context import execute_case
    return execute_case(TEST_CASE, run, context, preset, CaseFailure)
