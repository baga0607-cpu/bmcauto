import ipaddress
import json
import re
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit

TEST_CASE = {'modified_at': '2026-11-12T08:32:24.158088+00:00',
 'test_type': 'compliance',
 'spec_ref': ['DSP0266 v1.25.0 section 6.1 (URI characters and percent encoding).',
              'RFC 3986 sections 2.1, 3.2.2 and 3.5 (encoding, IPv6 authority and fragments); RFC 6901 '
              'sections 3 and 6 (JSON Pointer escapes).'],
 'created_at': '2026-10-30T06:16:31.055575+00:00',
 'name': 'RF-01-010 URI Character and Encoding Rules',
 'description': 'Inspect original resource URI references discovered from ServiceRoot for unsafe characters, '
                'fragment delimiters and percent-encoding outside query components.',
 'test_method': [{'step_number': 1,
                  'type': 'Action',
                  'step': 'Prepare a read-only traversal of the service.'},
                 {'step_number': 1,
                  'type': 'Checkpoint',
                  'step': 'Verify that a valid HTTP(S) service origin is available.'},
                 {'step_number': 2,
                  'type': 'Command',
                  'step': 'GET discoverable local resources and collection pages from /redfish/v1/. Do not '
                          'invoke Actions or fetch external services.'},
                 {'step_number': 2,
                  'type': 'Checkpoint',
                  'step': 'Verify that traversal completed without unread resources, invalid links or '
                          'pagination issues.'},
                 {'step_number': 3,
                  'type': 'Action',
                  'step': 'Inspect original URI components before normalization.'},
                 {'step_number': 3,
                  'type': 'Checkpoint',
                  'step': 'Verify safe characters and valid encoding: percent escapes only in queries; allow '
                          'structural IPv6 and JSON Pointer escapes.'},
                 {'step_number': 3,
                  'type': 'Checkpoint',
                  'step': 'Verify that the complete discovered scope was assessed.'}],
 'automation': 'automatic',
 'parameters': {}}


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


_METHOD_CHECKS = [('Task\\ origin\\ available', 1),
 ('Traversal\\ evidence\\ available', 3),
 ('Traversal\\ complete', 3),
 ('Original\\ URI\\ character\\ and\\ encoding\\ rules', 5),
 ('Scope\\ sufficient\\ for\\ Pass', 6)]


def _method_emit(context, index, status, **detail):
    item = TEST_CASE["test_method"][index]
    result = dict(method_index=index, step_number=item["step_number"], type=item["type"],
                  status=status, **detail)
    result = json.loads(json.dumps(result, ensure_ascii=False), parse_constant=lambda value: value)
    context.setdefault("_method_results", []).append(result)
    logger = context.get("log")
    if callable(getattr(logger, "method_item", None)):
        logger.method_item(item, result)
    elif callable(getattr(logger, "step", None)):
        logger.step(item["step"], None, result)
    else:
        print(json.dumps({"method": item, "result": result}, ensure_ascii=False))


def _report_flush(context, status=None, reason=None):
    phase = context.get("_method_phase")
    if phase is None:
        return
    pending = context.get("_method_pending", [])
    requests = context.get("_method_http", [])
    index = next(i for i, item in enumerate(TEST_CASE["test_method"])
                 if item["step_number"] == phase and item["type"] in ("Command", "Action"))
    failed_parse = any(label in ("Valid JSON", "Valid XML", "XML parser safety boundary")
                       and result["status"] == "FAIL" for _, label, result in pending)
    skipped = context.pop("_method_action_skip", None)
    outcome = ("Skip" if skipped else "ERROR" if status == "Error" else "FAILED" if failed_parse
               or status == "Fail" and not pending else "COMPLETED")
    detail = {"actual": {"responses": requests} if requests else "Operation completed"}
    if outcome in ("FAILED", "ERROR", "Skip"):
        detail = {"reason": skipped or reason or "Response parsing did not complete"}
    _method_emit(context, index, outcome, **detail)
    for index, label, result in pending:
        _method_emit(context, index, **result)
    context["_method_phase"] = None
    context["_method_pending"], context["_method_http"] = [], []


def _report_begin(context, number):
    if context.get("_method_phase") == number:
        return
    _report_flush(context)
    context["_method_phase"] = number
    context.setdefault("_method_visited", set()).add(number)
    context["_method_pending"], context["_method_http"] = [], []
    item = next(item for item in TEST_CASE["test_method"]
                if item["step_number"] == number and item["type"] in ("Command", "Action"))
    if context.get("log") is not None:
        context["log"].section(f'Step {number} | {item["type"]} | {item["step"]}')


def _log(context, method, *args, **kwargs):
    if method == "section":
        number = kwargs.pop("report_step", None)
        if number is not None:
            _report_begin(context, number)
        return
    if method == "check":
        import re
        label, passed = args
        index = next((index for pattern, index in _METHOD_CHECKS if re.fullmatch(pattern, label)), None)
        if index is None:
            raise RuntimeError("No declared Checkpoint for " + label)
        phase = TEST_CASE["test_method"][index]["step_number"]
        if context.get("_method_phase") != phase:
            _report_begin(context, phase)
        note = kwargs.get("note")
        status = kwargs.pop("judgement", None) or ("C-PASS" if passed and note else "PASS" if passed else "FAIL")
        result = {"status": status, "expected": kwargs.get("expected", True),
                  "actual": {"source": label, "value": kwargs.get("actual", bool(passed))}}
        if note and status == "C-PASS":
            result["note"] = note
        if kwargs.get("reason"):
            result["reason"] = kwargs["reason"]
        context.setdefault("_method_pending", []).append((index, label, result))
        return
    if method == "http":
        context.setdefault("_method_http", []).append({"method": args[0], "uri": args[1], "status": args[2]})
    logger = context.get("log")
    if logger is not None:
        return getattr(logger, method)(*args, **kwargs)
    print(json.dumps({"event": method, "details": args, **kwargs}, ensure_ascii=False))


def _finish(context, status, reason, evidence, observations):
    _report_flush(context, status, reason)
    results = context.setdefault("_method_results", [])
    for index, item in enumerate(TEST_CASE["test_method"]):
        if item["type"] == "Record" and item.get("observation") in observations:
            _method_emit(context, index, "COMPLETED", actual=observations[item["observation"]])
    observed = {result["method_index"] for result in results}
    for index, item in enumerate(TEST_CASE["test_method"]):
        if index not in observed:
            skip_reason = ("No applicable item was encountered for this check."
                           if item["step_number"] in context.get("_method_visited", set()) and status == "Pass"
                           else "Prerequisite was unavailable or execution ended: " + reason)
            _method_emit(context, index, "Skip", reason=skip_reason)
    notes = list(dict.fromkeys(result["note"] for result in results if result["status"] == "C-PASS"))
    if status == "Pass" and any(result["status"] in ("FAIL", "FAILED", "ERROR") for result in results):
        status, reason = "Fail", "A required method item failed; see its recorded result"
    elif status == "Pass" and notes:
        status = "C-PASS"
    note = "\n".join(notes) if status == "C-PASS" else ""
    context["case_result"] = dict(status=status, reason=reason, note=note, evidence=evidence,
                                  observations=observations, method_results=results)
    context["_tc_status"] = {"Pass": "PASS", "C-PASS": "C-PASS", "Block": "BLOCK"}.get(status, "FAIL")
    if context.get("log") is not None:
        context["log"].finish(status, reason, **({"note": note} if note else {}))
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
