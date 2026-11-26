TEST_CASE = {
    "modified_at": "2026-11-26T05:42:12.574147+00:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.1 (unique resource paths)",
        "DSP0266 v1.25.0 section 9.6.2 (resource identity)",
        "DSP0266 v1.25.0 section 7.2.2 (collection pagination)."
    ],
    "created_at": "2026-10-30T06:05:45.102559+00:00",
    "name": "RF-01-009 Resource URI Uniqueness",
    "description": "Traverse discoverable local Redfish resources and collection pages; assess resource identity path uniqueness within the observed scope.",
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
                "resource_identity_evidence": {
                    "expected": "Verify that each resource supplies usable identity and type metadata."
                },
                "collection_pagination_identity": {
                    "expected": "Verify matching collection identity and type across pagination links."
                },
                "traversal_complete": {
                    "expected": "Verify that traversal completed without:\n- Resources that could not be read.\n- Invalid links.\n- Pagination errors."
                }
            }
        },
        {
            "step_number": 3,
            "step": "Group identity paths and compare resource URLs and proven collection-page relationships. Record the number of resource/page responses observed. Record the number of distinct identity paths observed.",
            "checkpoints": {
                "identity_path_uniqueness_within_observed_scope": {
                    "expected": "Verify that each observed identity path maps to one established resource identity.\n\nProject coverage policy:\n- An unresolved identity group fails this check.\n- An unresolved group does not, by itself, prove an identity collision."
                },
                "scope_sufficient_for_pass": {
                    "expected": "Verify that all items within the discovered scope were assessed.\n\nProject coverage policy: incomplete coverage prevents PASS."
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
import re
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit
from contextlib import ExitStack


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


_CHECKS = [('Task\\ origin\\ available', 'task_origin_available'),
 ('Resource\\ identity\\ evidence', 'resource_identity_evidence'),
 ('Collection\\ pagination\\ identity', 'collection_pagination_identity'),
 ('Traversal\\ evidence\\ available', 'traversal_complete'),
 ('Traversal\\ complete', 'traversal_complete'),
 ('Identity\\ path\\ uniqueness\\ within\\ observed\\ scope',
  'identity_path_uniqueness_within_observed_scope'),
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
        if 'resource_response_count' in observations:
            self.begin_step(3)
            self.step.record(observations['resource_response_count'])
        if 'identity_path_count' in observations:
            self.begin_step(3)
            self.step.record(observations['identity_path_count'])
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


def _links(body):
    """Yield typed links and exclusions without guessing arbitrary string properties."""
    stack = [(body, "$")]
    while stack:
        value, field = stack.pop()
        if isinstance(value, dict):
            for key, child in value.items():
                location = field + "/" + key.replace("~", "~0").replace("/", "~1")
                if key == "Actions":
                    yield "action", child, location
                elif key == "@odata.id":
                    yield "resource", child, location
                elif key == "@odata.nextLink" or key.endswith("@odata.nextLink"):
                    yield "page", child, location
                elif isinstance(child, (dict, list)):
                    stack.append((child, location))
        elif isinstance(value, list):
            stack.extend((child, field + "/" + str(index)) for index, child in enumerate(value))


def _reject_json_constant(value):
    raise ValueError("Non-finite JSON constant: " + value)


def _fetch(session, url, origin, cache):
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

            if response.status_code in (301, 302, 307, 308):
                location = response.headers.get('Location')
                if not location:
                    raise CaseFailure('Redirect response has no Location')
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

    observations = {'resources': [], 'links': [], 'excluded': [], 'unread': [], 'unresolved': [], 'scope': 'Local structured resource links and collection pages'}
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
    queue = deque([root])
    scheduled = {root}
    cache = {}
    resources = {}
    aliases = {}
    page_edges = set()
    errors = observations['unread']

    def unread(uri, reason, source=None):
        errors.append({'uri': uri, 'source': source, 'reason': reason})
        flow.check('Traversal evidence available', False, expected='Readable local resource or page', actual=errors[-1])
    flow.begin_step(2)
    try:
        session = flow.get
        while queue:
            requested = queue.popleft()
            try:
                final, body = _fetch(session, requested, origin, cache)
            except (CaseFailure, requests.RequestException) as error:
                reason = str(error) if isinstance(error, CaseFailure) else 'HTTP request could not complete (' + type(error).__name__ + ')'
                cache[requested] = CaseFailure(reason)
                unread(requested, reason)
                continue
            aliases[requested] = final
            if final in resources:
                continue
            identity = body.get('@odata.id')
            resource_type = body.get('@odata.type')
            identity_path = None
            try:
                declared = _url(identity, final)
                if urlsplit(identity).fragment:
                    raise ValueError('Top-level fragment identity cannot establish a resource path')
                identity_path = urlsplit(declared).path
            except (ValueError, TypeError):
                unread(final, 'Missing or unusable top-level @odata.id')
            if not isinstance(resource_type, str) or not resource_type:
                unread(final, 'Missing or unusable @odata.type; identity evidence is incomplete')
            if requested == root and (not (isinstance(resource_type, str) and re.fullmatch('#ServiceRoot(?:\\.v[0-9]+_[0-9]+_[0-9]+)?\\.ServiceRoot', resource_type))):
                unread(final, 'Starting endpoint does not identify ServiceRoot')
            record = {'request_uri': requested, 'final_uri': final, '@odata.id': identity, '@odata.type': resource_type, 'identity_path': identity_path}
            resources[final] = record
            observations['resources'].append(record)
            flow.check('Resource identity evidence', identity_path is not None and isinstance(resource_type, str) and bool(resource_type), expected='Resource identity path and type', actual=record)
            for kind, reference, field in _links(body):
                source = {'resource': final, 'field': field}
                if kind == 'action':
                    observations['excluded'].append({'source': source, 'reason': 'Actions subtree is excluded'})
                    continue
                try:
                    target = _url(reference, final)
                except (ValueError, TypeError):
                    unread(final, 'Invalid ' + kind + ' link at ' + field, source)
                    continue
                link = {'source': source, 'reference': reference, 'target': target, 'kind': kind}
                observations['links'].append(link)
                if _origin(target) != origin:
                    observations['excluded'].append(dict(link, reason='External service is excluded'))
                    continue
                if '/Actions/' in urlsplit(target).path or urlsplit(target).path.endswith('/Actions'):
                    observations['excluded'].append(dict(link, reason='Action endpoint is excluded'))
                    continue
                if kind == 'page':
                    page_edges.add((final, target))
                if target not in scheduled:
                    scheduled.add(target)
                    queue.append(target)
        resolved_edges = {(aliases.get(a, a), aliases.get(b, b)) for a, b in page_edges}
        if _has_page_cycle(resolved_edges):
            unread(root, 'Collection pagination cycle detected')
        page_pairs = set()
        for parent, page in resolved_edges:
            left, right = (resources.get(parent), resources.get(page))
            if left is None or right is None:
                continue
            kind = left['@odata.type']
            valid = isinstance(kind, str) and kind.endswith('Collection') and (kind == right['@odata.type']) and (left['identity_path'] is not None) and (left['identity_path'] == right['identity_path'])
            flow.check('Collection pagination identity', valid, expected='Matching collection identity and type', actual={'parent': parent, 'page': page})
            if valid:
                page_pairs.add((parent, page))
            else:
                unread(page, 'Pagination identity cannot be established', parent)
        flow.check('Traversal complete', not errors, expected='No unread in-scope resources or invalid pagination', actual={'resources': len(resources), 'unread': errors, 'excluded': observations['excluded']})
        if not resources:
            return flow.finish('Fail', 'No resource identity evidence was obtained', observations)
        flow.begin_step(3)
        representatives = {uri: uri for uri in resources}

        def find(uri):
            while representatives[uri] != uri:
                representatives[uri] = representatives[representatives[uri]]
                uri = representatives[uri]
            return uri
        for parent, page in page_pairs:
            representatives[find(page)] = find(parent)
        groups = {}
        for uri, record in resources.items():
            path = record['identity_path']
            if path is not None:
                groups.setdefault(path, []).append(uri)
        for path, uris in sorted(groups.items()):
            instances = {find(uri) for uri in uris}
            resolved = len(instances) == 1
            details = {'identity_path': path, 'responses': [resources[uri] for uri in uris], 'classification': 'No distinct-instance evidence' if resolved else 'Unresolved alias or identity collision'}
            flow.check('Identity path uniqueness within observed scope', resolved, expected='One established resource identity per path', actual=details)
            if not resolved:
                observations['unresolved'].append(details)
        observations['resource_response_count'] = len(resources)
        observations['identity_path_count'] = len(groups)
        observations['traversal_complete'] = not errors
        flow.check('Scope sufficient for Pass', not errors, expected='Complete discovered scope', actual={'unread': errors})
    except CaseFailure:
        raise
    except Exception as error:
        observations['pending'] = list(queue)
        return flow.finish('Error', 'Unexpected program error (' + type(error).__name__ + ')', observations)
    failed = bool(errors or observations['unresolved'])
    reason = f"Traversal incomplete: {len(errors)} issue(s); unresolved identity groups: {len(observations['unresolved'])}. No confirmed collision is inferred from payload differences." if failed else f'No unresolved identity paths among {len(resources)} resource/page responses and {len(groups)} identity paths in the discovered scope.'
    return flow.finish('Fail' if failed else 'Pass', reason, observations)


def run(ctx):
    with ExitStack() as stack:
        return _evaluate(_Steps(ctx, stack))


def execute(client, context=None, preset=None):
    from case_v1_context import execute_case
    return execute_case(TEST_CASE, run, context, preset, CaseFailure,
                        [(3, 'Record the number of resource/page responses observed.'), (3, 'Record the number of distinct identity paths observed.')])
