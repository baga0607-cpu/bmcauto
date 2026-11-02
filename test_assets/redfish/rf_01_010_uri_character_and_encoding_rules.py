import ipaddress
import json
import re
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit

TEST_CASE = {
    "modified_at": "2026-11-02T06:11:19.396101+00:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.1 (URI characters and percent encoding).",
        "RFC 3986 sections 2.1, 3.2.2 and 3.5 (encoding, IPv6 authority and fragments); RFC 6901 sections 3 and 6 (JSON Pointer escapes)."
    ],
    'created_at': '2026-10-30T06:16:31.055575+00:00',
 'name': 'RF-01-010 URI Character and Encoding Rules',
 'description': 'Inspect original resource URI references discovered from ServiceRoot for unsafe '
                'characters, fragment delimiters and percent-encoding outside query components.',
 'test_method': [{'step_1': 'Validate Task connection settings and initialize a read-only session.',
                  'criteria': 'A valid HTTP(S) Task origin is required. Invalid settings are Fail; '
                              'missing dependencies or unexpected program defects are Error.'},
                 {'step_2': 'Traverse local structured resource links and collection pages from '
                            '/redfish/v1/. Collect original URI references and their source fields '
                            'before normalization.',
                  'criteria': 'Record HTTP evidence and scope. GET only, fixed 15-second timeout, '
                              'at most five same-origin redirects, no repeated URL requests. Never '
                              'invoke Actions or traverse external services. Invalid advertised '
                              'URIs are not repaired or requested. Unread resources, invalid links '
                              'or pagination cycles prevent Pass. Redirect safeguards remain '
                              'provisional pending RF-02.'},
                 {'step_3': 'Check raw URI components against the approved DSP0266 1.23.0 section '
                            '6.1 character and encoding rules.',
                  'criteria': 'No RFC1738 unsafe characters or raw controls/non-ASCII characters. '
                              'A single # may delimit a fragment. Valid IPv6 authority brackets '
                              'and JSON Pointer ~0/~1 fragment escapes are structural exceptions. '
                              'Valid %HH escapes are allowed only in query, not path, authority or '
                              'fragment; malformed percent escapes fail everywhere. Fragment '
                              'target and pointer semantics belong to RF-01-011. Pass requires '
                              'complete discovered scope and no violations; record original URI, '
                              'source field and failed rule.'}],
 'automation': 'automatic',
 'parameters': {}}


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


def _report_emit(context, number, result):
    """Record the authored method and criteria without changing case judgement."""
    method = TEST_CASE["test_method"][number - 1]
    step = method.get("step_" + str(number), method.get("step"))
    criteria = method.get("criteria")
    logger = context.get("log")
    write = getattr(logger, "step", None) if logger is not None else None
    if callable(write):
        note = result.get('note') if isinstance(result, dict) else None
        write(step, criteria, result, **({'note': note} if note else {}))
    else:
        print("\n--- REPORT STEP ---")
        print(json.dumps({"step": step, "criteria": criteria, "result": result}, ensure_ascii=False, indent=2))


def _report_flush(context, status=None, reason=None):
    state = context.get("_report_steps")
    if not state or state["number"] is None:
        return
    number, checks = state["number"], state["checks"]
    if status is not None:
        outcome = status.upper()
    elif checks:
        outcome = "PASS" if all(check["passed"] for check in checks) else "FAIL"
    else:
        outcome = None
    result = {"status": outcome, "checks": checks} if outcome is not None else None
    if reason and result is not None:
        result["reason"] = reason
    notes = [check['note'] for check in checks if check.get('note')]
    if notes and result is not None:
        result['note'] = '\n'.join(dict.fromkeys(notes))
    _report_emit(context, number, result)
    state["seen"].append(number)
    state["number"], state["checks"] = None, []


def _report_begin(context, number):
    state = context.setdefault("_report_steps", {"number": None, "checks": [], "seen": []})
    if state["number"] != number:
        _report_flush(context)
        state["number"] = number


def _report_finish(context, status, reason):
    _report_flush(context, status, reason)
    state = context.get("_report_steps", {"seen": []})
    for number in range(1, len(TEST_CASE["test_method"]) + 1):
        if number not in state["seen"]:
            _report_emit(context, number, None)
    context.pop("_report_steps", None)


def _log(context, method, *args, **kwargs):
    # Report evidence is separate from assertions and the final case outcome.
    if method == "section":
        number = kwargs.pop("report_step", None)
        if number is not None:
            _report_begin(context, number)
    elif method == "check":
        if kwargs.get("note"):
            context.setdefault("_result_notes", []).append(kwargs["note"])
        state = context.get("_report_steps")
        if state and state["number"] is not None:
            state["checks"].append({"label": args[0], "passed": bool(args[1]),
                                    "expected": kwargs.get("expected"), "actual": kwargs.get("actual"), "note": kwargs.get("note")})
    logger = context.get("log")
    if logger is not None:
        return getattr(logger, method)(*args, **kwargs)
    # Standalone/offline execution remains possible without a platform import.
    print("\n--- " + method.upper() + " ---")
    print(json.dumps({"details": args, **kwargs}, ensure_ascii=False, indent=2))


def _finish(context, status, reason, evidence, observations):
    _report_finish(context, status, reason)
    note = "\n".join(dict.fromkeys(context.get("_result_notes", [])))
    context["case_result"] = {
        "status": status, "reason": reason, "note": note, "evidence": evidence,
        "observations": observations,
    }
    # Compatibility with the current runner; it still stores Error as Failed.
    context["_tc_status"] = "PASS" if status == "Pass" else "FAIL"
    if context.get("log") is not None:
        _log(context, "finish", status, reason, **({"note": note} if note else {}))
    else:
        print(json.dumps(context["case_result"], ensure_ascii=False))
    if status == "Fail":
        raise CaseFailure(reason)
    if status == "Error":
        raise RuntimeError(reason)


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


def _fetch(session, url, conf, origin, context, evidence, cache, inspect_uri):
    chain = []
    current = url
    try:
        for hop in range(6):
            if current in chain:
                raise CaseFailure("Redirect loop detected")
            if current in cache:
                result = cache[current]
                if isinstance(result, Exception):
                    raise result
                for alias in chain:
                    cache[alias] = result
                return result
            chain.append(current)
            response = session.get(current, headers={"Accept": "application/json"},
                                   verify=conf.get("verify_ssl", False), timeout=15,
                                   allow_redirects=False)
            headers = {k: v for k, v in response.headers.items()
                       if k.lower() not in ("set-cookie", "authorization", "x-auth-token")}
            evidence.append({"uri": current, "status": response.status_code,
                             "headers": headers, "body": response.text})
            _log(context, "http", "GET", current, response.status_code, headers,
                 response.text, request_headers={"Accept": "application/json"})
            location_issues = []
            if response.headers.get("Location") is not None:
                location_issues = inspect_uri(response.headers.get("Location"), current,
                                              "headers/Location", "header")
            if response.status_code in (301, 302, 307, 308):
                location = response.headers.get("Location")
                if not location:
                    raise CaseFailure("Redirect response has no Location")
                if location_issues:
                    raise CaseFailure("Advertised redirect URI violates character or encoding rules")
                try:
                    target = _url(location, current)
                except ValueError:
                    raise CaseFailure("Redirect URL is invalid") from None
                if _origin(target) != origin:
                    raise CaseFailure("Redirect leaves Task origin; credentials were not forwarded")
                if "/Actions/" in urlsplit(target).path or urlsplit(target).path.endswith("/Actions"):
                    raise CaseFailure("Redirect to an Action endpoint was not followed")
                if hop == 5:
                    raise CaseFailure("Redirect limit exceeded (5 redirects)")
                current = target
                continue
            if response.status_code != 200:
                raise CaseFailure(f"Expected HTTP status = 200; Received HTTP status = {response.status_code}")
            try:
                body = json.loads(response.text, parse_constant=_reject_json_constant)
            except ValueError:
                raise CaseFailure("Response body is not valid JSON") from None
            if not isinstance(body, dict):
                raise CaseFailure("Response body is not a JSON object")
            result = current, body
            for alias in chain:
                cache[alias] = result
            return result
        raise CaseFailure("Redirect could not complete")
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



def execute(client, context=None, preset=None):
    """Inspect service-provided URI strings without synthesizing invalid requests."""
    if not isinstance(context, dict):
        raise RuntimeError("BMCAgent did not supply a dictionary execution context")
    evidence = []
    observations = {"resources": [], "uris": [], "violations": [], "excluded": [], "unread": [],
                    "scope": "Structured resource/page links, Action references, OData context and Location"}
    _log(context, "section", "Task connection settings", report_step=1)
    conf = context.get("redfish")
    try:
        if not isinstance(conf, dict):
            raise ValueError("Missing Task settings")
        host = _url(conf.get("host"), "")
        origin = _origin(host)
    except (ValueError, TypeError):
        return _finish(context, "Fail", "Task BMC URL is missing or invalid", evidence, observations)
    try:
        import requests
    except ImportError:
        return _finish(context, "Error", "Required requests package is unavailable", evidence, observations)
    _log(context, "check", "Task origin available", True, expected="HTTP(S) origin",
         actual=urlunsplit((urlsplit(host).scheme, urlsplit(host).netloc, "", "", "")))
    root = _url("/redfish/v1/", host)
    queue, scheduled, cache = deque([root]), {root}, {}
    resources, aliases, page_edges = set(), {}, set()
    errors = observations["unread"]

    def unread(uri, reason, source=None):
        errors.append({"uri": uri, "source": source, "reason": reason})
        _log(context, "check", "Traversal evidence available", False,
             expected="Readable in-scope resource or page", actual=errors[-1])

    def inspect_uri(raw, source, field, kind):
        issues = _uri_issues(raw)
        item = {"source": source, "field": field, "uri": raw, "kind": kind, "issues": issues}
        observations["uris"].append(item)
        if issues:
            observations["violations"].append(item)
        return issues

    _log(context, "section", "Resource traversal and HTTP evidence", report_step=2)
    try:
        with requests.Session() as session:
            session.trust_env = False
            session.auth = (conf.get("username", ""), conf.get("password", ""))
            while queue:
                requested = queue.popleft()
                try:
                    final, body = _fetch(session, requested, conf, origin, context, evidence, cache, inspect_uri)
                except (CaseFailure, requests.RequestException) as error:
                    reason = str(error) if isinstance(error, CaseFailure) else (
                        "HTTP request could not complete (" + type(error).__name__ + ")")
                    cache[requested] = CaseFailure(reason)
                    unread(requested, reason)
                    continue
                aliases[requested] = final
                if final in resources:
                    continue
                resources.add(final)
                observations["resources"].append({"request_uri": requested, "final_uri": final})
                if "@odata.id" not in body:
                    unread(final, "Missing top-level @odata.id; resource URI evidence is incomplete")
                if requested == root and not (
                        isinstance(body.get("@odata.type"), str) and re.fullmatch(
                            r"#ServiceRoot(?:\.v[0-9]+_[0-9]+_[0-9]+)?\.ServiceRoot", body["@odata.type"])):
                    unread(final, "Starting endpoint does not identify ServiceRoot")
                for kind, reference, field in _links(body):
                    issues = inspect_uri(reference, final, field, kind)
                    source = {"resource": final, "field": field}
                    if kind in ("action", "context"):
                        observations["excluded"].append({"source": source, "uri": reference,
                                                         "reason": "Inspected only; no Action or metadata request"})
                        continue
                    if issues:
                        unread(final, "Invalid advertised URI was not requested", source)
                        continue
                    try:
                        target = _url(reference, final)
                    except (ValueError, TypeError):
                        unread(final, "Resource URI could not be resolved", source)
                        continue
                    if _origin(target) != origin:
                        observations["excluded"].append({"source": source, "uri": reference,
                                                         "reason": "External service; reference inspected, not traversed"})
                        continue
                    if "/Actions/" in urlsplit(target).path or urlsplit(target).path.endswith("/Actions"):
                        observations["excluded"].append({"source": source, "uri": reference,
                                                         "reason": "Action endpoint is not invoked"})
                        continue
                    if kind == "page":
                        page_edges.add((final, target))
                    if target not in scheduled:
                        scheduled.add(target)
                        queue.append(target)
        if _has_page_cycle({(aliases.get(a, a), aliases.get(b, b)) for a, b in page_edges}):
            unread(root, "Collection pagination cycle detected")
        _log(context, "check", "Traversal complete", not errors,
             expected="No unread in-scope resources or pages",
             actual={"resources": len(resources), "unread": errors, "excluded": observations["excluded"]})
        if not observations["uris"]:
            return _finish(context, "Fail", "No service-provided URI evidence was obtained", evidence, observations)
        _log(context, "section", "URI character and encoding validation", report_step=3)
        for item in observations["uris"]:
            _log(context, "check", "Original URI character and encoding rules", not item["issues"],
                 expected="Safe URI components; percent encoding only in query", actual=item)
        observations["resource_response_count"] = len(resources)
        observations["uri_occurrence_count"] = len(observations["uris"])
        observations["traversal_complete"] = not errors
        _log(context, "check", "Scope sufficient for Pass", not errors,
             expected="Complete discovered scope", actual={"unread": errors})
    except CaseFailure:
        raise
    except Exception as error:
        observations["pending"] = list(queue)
        return _finish(context, "Error", "Unexpected program error (" + type(error).__name__ + ")",
                       evidence, observations)
    failed = bool(errors or observations["violations"])
    reason = (f"URI violations: {len(observations['violations'])}; traversal issues: {len(errors)}."
              if failed else
              f"No URI character or encoding violations in {len(observations['uris'])} URI occurrences "
              f"from {len(resources)} resource/page responses in the discovered scope.")
    return _finish(context, "Fail" if failed else "Pass", reason, evidence, observations)
