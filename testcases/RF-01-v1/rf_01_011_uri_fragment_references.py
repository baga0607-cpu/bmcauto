TEST_CASE = {
    "modified_at": "2026-11-26T05:42:12.574147+00:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.1 (fragment references)",
        "DSP0266 v1.25.0 section 9.5.7 (reference properties and resource identity).",
        "DSP0266 v1.25.0 section 9.6.2 (reference properties and resource identity).",
        "DSP0266 v1.25.0 section 8.2 (schema discovery and repository access).",
        "DSP0266 v1.25.0 section 10.5 (schema discovery and repository access).",
        "RFC 6901 section 3 (JSON Pointer syntax, evaluation and URI fragment representation).",
        "RFC 6901 section 4 (JSON Pointer syntax, evaluation and URI fragment representation).",
        "RFC 6901 section 6 (JSON Pointer syntax, evaluation and URI fragment representation)."
    ],
    "created_at": "2026-10-30T06:23:36.474763+00:00",
    "name": "RF-01-011 URI Fragment References",
    "description": "Resolve discovered local URI fragments as JSON Pointers and verify schema-classified resource reference targets.",
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
            "step": "Resolve each fragment as a JSON Pointer and classify its target using advertised schemas with per-run caching.",
            "checkpoints": {
                "applicable_fragment_references_found": {
                    "expected": "Verify that at least one applicable local fragment reference was found.\n\nProject coverage policy: no applicable references means FAIL for this check."
                },
                "fragment_reference_validation": {
                    "expected": "Verify each fragment reference:\n- The JSON Pointer target exists.\n- The advertised schema establishes the reference type.\n- For a resource reference, the target has a nonempty string @odata.id that identifies the referenced resource."
                },
                "scope_sufficient_for_pass": {
                    "expected": "Verify that the assessment includes:\n- All items within the discovered scope.\n- The schema evidence required to classify the references.\n\nProject coverage policy: incomplete scope or schema evidence prevents PASS."
                }
            },
            "route": "bmc_redfish"
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
from urllib.parse import urljoin, urlsplit, urlunsplit, unquote
from contextlib import ExitStack
from functools import partial


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


_CHECKS = [('Task\\ origin\\ available', 'task_origin_available'),
 ('Traversal\\ evidence\\ available', 'traversal_complete'),
 ('Traversal\\ complete', 'traversal_complete'),
 ('Applicable\\ fragment\\ references\\ found', 'applicable_fragment_references_found'),
 ('Fragment\\ reference\\ validation', 'fragment_reference_validation'),
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


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key makes pointer resolution ambiguous")
        result[key] = value
    return result


def _reject_json_constant(value):
    raise ValueError("Non-finite JSON constant: " + value)


def _fetch(session, url, origin, evidence, cache, schema_guard=None, revalidate=False):
    chain = []
    current = url
    request_headers = {'Accept': 'application/json'}
    if revalidate:
        request_headers['Cache-Control'] = 'no-cache'
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
            response = session(current, headers=request_headers)
            headers = {k: v for k, v in response.headers.items() if k.lower() not in ('set-cookie', 'authorization', 'x-auth-token')}
            evidence.append({'uri': current, 'status': response.status_code, 'headers': headers})
            if response.status_code in (301, 302, 307, 308):
                location = response.headers.get('Location')
                if not location:
                    raise CaseFailure('Redirect response has no Location')
                try:
                    target = _url(location, current)
                except ValueError:
                    raise CaseFailure('Redirect URL is invalid') from None
                if schema_guard:
                    target = schema_guard(target)
                elif _origin(target) != origin:
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
                body = json.loads(response.text, parse_constant=_reject_json_constant, object_pairs_hook=_unique_object)
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


def _pointer_tokens(fragment):
    """Decode URI escaping once, then JSON Pointer escaping in RFC6901 order."""
    if re.search(r"%(?![0-9A-Fa-f]{2})", fragment):
        raise CaseFailure("Malformed percent escape in fragment")
    if any(ord(c) < 33 or ord(c) == 127 for c in fragment) or "#" in fragment:
        raise CaseFailure("Invalid raw fragment character")
    try:
        pointer = unquote(fragment, encoding="utf-8", errors="strict")
    except UnicodeError:
        raise CaseFailure("Fragment percent escapes are not valid UTF-8") from None
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise CaseFailure("JSON Pointer must be empty or begin with /")
    result = []
    for token in pointer[1:].split("/"):
        if re.search(r"~(?![01])", token):
            raise CaseFailure("Invalid JSON Pointer tilde escape")
        result.append(token.replace("~1", "/").replace("~0", "~"))
    return result


def _resolve_pointer(document, fragment):
    value = document
    for token in _pointer_tokens(fragment):
        if isinstance(value, dict):
            if token not in value:
                raise CaseFailure("JSON Pointer object key does not exist: " + repr(token))
            value = value[token]
        elif isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise CaseFailure("JSON Pointer array index is invalid: " + repr(token))
            # Avoid integer conversion limits on maliciously long index tokens.
            if len(token) > len(str(len(value))) or int(token) >= len(value):
                raise CaseFailure("JSON Pointer array index is out of bounds")
            value = value[int(token)]
        else:
            raise CaseFailure("JSON Pointer attempts to traverse a scalar value")
    return value


def _links(body):
    stack = [(body, ())]
    while stack:
        value, path = stack.pop()
        if isinstance(value, dict):
            for key, child in value.items():
                location = path + (key,)
                if key == "Actions":
                    yield "excluded", None, location
                elif key == "@odata.id":
                    yield "resource", child, location
                elif key == "@odata.nextLink" or key.endswith("@odata.nextLink"):
                    yield "page", child, location
                elif ("Uri" in key or "URI" in key) and isinstance(child, str) and "#" in child:
                    yield "property", child, location
                elif isinstance(child, (dict, list)):
                    stack.append((child, location))
        elif isinstance(value, list):
            stack.extend((child, path + (index,)) for index, child in enumerate(value))


def _field(path):
    return "$" + "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in path)


def _schema_link(header):
    """Use only one unambiguous rel=describedby URI; never guess a schema URL."""
    matches = []
    for match in re.finditer(r'<([^<>]+)>\s*((?:;[^<>]*)?)(?=,\s*<|$)', header or ""):
        params = match.group(2)
        relation = re.search(r'(?:^|;)\s*rel\s*=\s*(?:"([^"]*)"|([^;\s,]+))', params, re.I)
        if relation and "describedby" in (relation.group(1) or relation.group(2)).lower().split():
            matches.append(match.group(1))
    if len(matches) != 1:
        raise CaseFailure("Missing or ambiguous local describedby JSON Schema link")
    return matches[0]


def _trusted_schema_url(uri):
    uri = _url(uri, uri)
    parts = urlsplit(uri)
    if (parts.hostname != "redfish.dmtf.org" or
            _origin(uri)[2] != (443 if parts.scheme == "https" else 80) or
            not parts.path.startswith("/schemas/") or
            not parts.path.endswith(".json") or parts.query or
            "%" in parts.path or "\\" in parts.path or
            any(p in (".", "..") for p in parts.path.split("/"))):
        raise CaseFailure("Schema source is not trusted: " + uri)
    return urlunsplit(("https", parts.hostname, parts.path, "", ""))


def _schema_kind(schema_uri, path, instance, get_document):
    """Resolve a conservative JSON Schema subset; unsupported branches fail closed."""
    documents = {}
    declared = instance.get("@odata.type", "")
    declared = declared if isinstance(declared, str) else ""
    type_match = re.fullmatch(r"#([A-Za-z0-9_]+)\.(v[0-9]+_[0-9]+_[0-9]+)\.([A-Za-z0-9_]+)", declared)

    def check_version(uri):
        match = re.search(r"/([^/]+)\.(v[0-9]+_[0-9]+_[0-9]+)\.json$", urlsplit(uri).path)
        if match and (not type_match or match.groups() != type_match.groups()[:2]):
            raise CaseFailure("Schema version does not match BMC @odata.type: " + declared + "; schema=" + uri)

    check_version(schema_uri)

    def load(uri):
        if uri in documents:
            return documents[uri]
        physical, document = get_document(uri)
        if physical in documents:
            documents[uri] = documents[physical]
            return documents[physical]
        if not documents:
            check_version(physical)
        logical = physical
        identifier = document.get("$id", document.get("id"))
        if identifier is not None:
            logical = _url(identifier, physical)
            if not documents:
                check_version(logical)
            if urlsplit(identifier).fragment:
                raise CaseFailure("Schema document identifier contains an unsupported anchor")
        # A declared canonical ID can name this already-fetched local document.
        # It does not authorize fetching other documents from that external origin.
        if logical in documents:
            raise CaseFailure("Ambiguous canonical schema document identifier")
        root_node = {k: v for k, v in document.items() if k not in ("$id", "id")}
        result = logical, root_node
        documents[uri] = documents[physical] = documents[logical] = result
        return result

    def expand(node, base, value, seen=()):
        if not isinstance(node, dict):
            raise CaseFailure("Unsupported boolean or non-object schema")
        if any(k in node for k in ("allOf", "if", "then", "else", "$dynamicRef", "$id", "id")):
            raise CaseFailure("Unsupported schema composition or base-URI keyword")
        if "$ref" in node:
            target = urljoin(base, node["$ref"])
            if value is instance and type_match and urlsplit(target).path.rsplit("/", 1)[-1].startswith(type_match[1] + ".v"):
                check_version(target)
            if target in seen or len(seen) >= 64:
                raise CaseFailure("Cyclic or excessive schema reference chain")
            document_uri = _url(target, base)
            final, document = load(document_uri)
            resolved = _resolve_pointer(document, urlsplit(target).fragment)
            return expand(resolved, final, value, seen + (target,))
        for keyword in ("anyOf", "oneOf"):
            if keyword in node:
                branches = node[keyword]
                if value is instance and type_match:
                    expected = type_match[1] + "." + type_match[2] + ".json"
                    selected = [b for b in branches if isinstance(b, dict) and
                                urlsplit(b.get("$ref", "")).path.rsplit("/", 1)[-1] == expected and
                                urlsplit(b.get("$ref", "")).fragment == "/definitions/" + type_match[3]]
                    if selected:
                        if len(selected) != 1:
                            raise CaseFailure("Multiple schema branches match BMC @odata.type")
                        return expand(selected[0], base, value, seen)
                    if any(isinstance(b, dict) and re.search(r"\.v[0-9]+_[0-9]+_[0-9]+\.json", b.get("$ref", "")) for b in branches):
                        raise CaseFailure("Advertised schema has no branch for BMC @odata.type: " + declared)
                candidates = []
                for branch in branches:
                    try:
                        resolved, location = expand(branch, base, value, seen)
                    except CaseFailure:
                        raise
                    branch_type = resolved.get("type")
                    actual = ("null" if value is None else "boolean" if isinstance(value, bool) else
                              "object" if isinstance(value, dict) else "array" if isinstance(value, list)
                              else "string" if isinstance(value, str) else "number")
                    types = branch_type if isinstance(branch_type, list) else [branch_type]
                    if actual in types or (actual == "number" and "integer" in types):
                        candidates.append((resolved, location))
                if len(candidates) != 1:
                    raise CaseFailure("Schema branch classification is ambiguous")
                return candidates[0]
        return node, base

    base, document = load(_url(schema_uri, schema_uri))
    node = document
    current = instance
    # A resource reference is the parent object containing the @odata.id link.
    wanted = path[:-1] if path and path[-1] == "@odata.id" else path
    for part in wanted:
        node, base = expand(node, base, current)
        if isinstance(part, int):
            node = node.get("items")
        else:
            props = node.get("properties", {})
            if part not in props:
                raise CaseFailure("Source property is not explicitly described by the schema")
            node = props[part]
        current = current[part]
    node, base = expand(node, base, current)
    if path and path[-1] == "@odata.id":
        props = node.get("properties", {})
        if "@odata.id" not in props:
            raise CaseFailure("Schema does not establish a resource reference")
        id_node, _ = expand(props["@odata.id"], base, instance_value(instance, path))
        types = id_node.get("type")
        if types == "string" or isinstance(types, list) and "string" in types:
            return "resource"
        raise CaseFailure("Schema resource identifier is not a string")
    types = node.get("type")
    string_type = types == "string" or isinstance(types, list) and "string" in types
    if string_type and isinstance(current, str) and node.get("format") in ("uri", "uri-reference"):
        return "property"
    raise CaseFailure("Schema does not establish a URI property type")


def instance_value(document, path):
    for part in path:
        document = document[part]
    return document


def _evaluate(flow):
    evidence = []
    observations = {'resources': [], 'references': [], 'results': [], 'excluded': [], 'unread': [], 'scope': 'Local structured links and explicit Uri/URI fragment properties'}
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
    bodies, aliases, edges = ({}, {}, set())
    errors = observations['unread']
    failures = []

    def unread(uri, reason):
        errors.append({'uri': uri, 'reason': reason})
        flow.check('Traversal evidence available', False, expected='Readable in-scope JSON document', actual=errors[-1])
    flow.begin_step(2)
    try:
        session = flow.get
        schema_session = partial(flow.get, auth='none')
        schema_cache = {}
        observations['schema_requests'] = []

        def get_document(uri):
            if _origin(uri) != origin:
                raise CaseFailure('External schema or target is not fetched')
            if '/Actions/' in urlsplit(uri).path or urlsplit(uri).path.endswith('/Actions'):
                raise CaseFailure('Action endpoint is not fetched')
            try:
                return _fetch(session, uri, origin, evidence, cache)
            except requests.RequestException as error:
                raise CaseFailure('HTTP request could not complete (' + type(error).__name__ + ')') from None

        def get_schema(uri):
            requested = uri
            item = {'requested_uri': requested, 'cache': 'per-run'}
            observations['schema_requests'].append(item)
            try:
                local = _origin(uri) == origin
                if not local:
                    uri = _trusted_schema_url(uri)
                item.update(fetch_uri=uri, cache_hit=uri in schema_cache, freshness='per-run retrieval; unversioned documents revalidated')
                result = _fetch(session if local else schema_session, uri, origin, evidence, schema_cache, schema_guard=_trusted_schema_url if not local else None, revalidate=not bool(re.search('\\.v[0-9]+_[0-9]+_[0-9]+\\.json$', urlsplit(uri).path)))
                item['resolved_uri'] = result[0]
                return result
            except (CaseFailure, ValueError, requests.RequestException) as error:
                item['reason'] = str(error)
                raise CaseFailure('Schema evidence unavailable; schema=' + requested + '; cause=' + str(error)) from None
        while queue:
            requested = queue.popleft()
            try:
                final, body = get_document(requested)
            except CaseFailure as error:
                unread(requested, str(error))
                continue
            aliases[requested] = final
            if final in bodies:
                continue
            bodies[final] = body
            observations['resources'].append(final)
            if requested == root and (not (isinstance(body.get('@odata.type'), str) and re.fullmatch('#ServiceRoot(?:\\.v[0-9]+_[0-9]+_[0-9]+)?\\.ServiceRoot', body['@odata.type']))):
                unread(final, 'Starting endpoint does not identify ServiceRoot')
            for kind, raw, path in _links(body):
                source = {'source': final, 'field': _field(path), 'uri': raw}
                if kind == 'excluded':
                    observations['excluded'].append(dict(source, reason='Actions subtree'))
                    continue
                try:
                    target = _url(raw, final)
                except (ValueError, TypeError):
                    unread(final, 'Invalid reference at ' + _field(path))
                    continue
                if _origin(target) != origin:
                    observations['excluded'].append(dict(source, reason='External service or anchor'))
                    continue
                if '/Actions/' in urlsplit(target).path or urlsplit(target).path.endswith('/Actions'):
                    observations['excluded'].append(dict(source, reason='Action endpoint'))
                    continue
                if isinstance(raw, str) and '#' in raw and (kind != 'page'):
                    observations['references'].append(dict(source, path=list(path), target=target, fragment=raw.partition('#')[2]))
                if kind == 'page':
                    edges.add((final, target))
                if target not in scheduled:
                    scheduled.add(target)
                    queue.append(target)
        if _has_page_cycle({(aliases.get(a, a), aliases.get(b, b)) for a, b in edges}):
            unread(root, 'Collection pagination cycle detected')
        flow.check('Traversal complete', not errors, expected='No unread resources or pages', actual={'unread': errors, 'excluded': observations['excluded']})
        flow.begin_step(3)
        flow.check('Applicable fragment references found', bool(observations['references']), expected='At least one applicable local reference', actual=len(observations['references']))
        for ref in observations['references']:
            result = {'source': ref['source'], 'field': ref['field'], 'uri': ref['uri']}
            stage = 'pointer'
            try:
                final, document = get_document(ref['target'])
                target_value = _resolve_pointer(document, ref['fragment'])
                result['pointer_resolved'] = True
                source_http = next((item for item in evidence if item['uri'] == ref['source'] and item['status'] == 200))
                header = next((v for k, v in source_http['headers'].items() if k.lower() == 'link'), '')
                stage = 'schema'
                result['declared_type'] = bodies[ref['source']].get('@odata.type')
                schema_uri = _url(_schema_link(header), ref['source'])
                result['schema'] = schema_uri
                kind = _schema_kind(schema_uri, tuple(ref['path']), bodies[ref['source']], get_schema)
                result['schema'] = schema_uri
                result['property_kind'] = kind
                stage = 'identity'
                if kind == 'resource':
                    identifier = target_value.get('@odata.id') if isinstance(target_value, dict) else None
                    if not isinstance(identifier, str) or not identifier:
                        raise CaseFailure('Reference property target has no resource identifier')
                    identity_uri = _url(identifier, final)
                    identity_fragment = identifier.partition('#')[2]
                    identity_final, identity_doc = get_document(identity_uri)
                    if identity_final != final or _pointer_tokens(identity_fragment) != _pointer_tokens(ref['fragment']):
                        raise CaseFailure('Target @odata.id does not identify the referenced resource')
                    _resolve_pointer(identity_doc, identity_fragment)
                result['passed'] = True
            except (CaseFailure, ValueError, TypeError) as error:
                result.update(passed=False, reason=str(error), failure_stage=stage, failure_category='schema_evidence' if stage == 'schema' else 'reference_validation')
                failures.append(result)
            observations['results'].append(result)
            flow.check('Fragment reference validation', result['passed'], expected='Existing pointer target and schema-appropriate resource identity', actual=result)
        observations['resource_response_count'] = len(bodies)
        observations['fragment_count'] = len(observations['references'])
        observations['traversal_complete'] = not errors
        flow.check('Scope sufficient for Pass', not errors, expected='Complete discovered scope', actual=errors)
    except CaseFailure:
        raise
    except Exception as error:
        observations['pending'] = list(queue)
        return flow.finish('Error', 'Unexpected program error (' + type(error).__name__ + ')', observations)
    if not observations['references']:
        reason = 'No applicable fragment property references were found'
    elif failures or errors:
        reason = f'Fragment validation failures: {len(failures)}; traversal issues: {len(errors)}'
    else:
        reason = f"Validated {len(observations['references'])} fragment references in the discovered scope"
    passed = bool(observations['references']) and (not failures) and (not errors)
    return flow.finish('Pass' if passed else 'Fail', reason, observations)


def run(ctx):
    with ExitStack() as stack:
        return _evaluate(_Steps(ctx, stack))


def execute(client, context=None, preset=None):
    from case_v1_context import execute_case
    return execute_case(TEST_CASE, run, context, preset, CaseFailure)
