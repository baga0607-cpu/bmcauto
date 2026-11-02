import json
import re
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit

TEST_CASE = {
    "modified_at": "2026-11-02T06:11:19.396101+00:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.1 (unique resource paths); section 9.6.2 (resource identity); section 7.2.2 (collection pagination).",
        "BMCAgent RF-01-009 coverage policy: complete discovered scope and no unresolved identity groups; unresolved candidates are not proof of a collision."
    ],
    'created_at': '2026-10-30T06:05:45.102559+00:00',
 'name': 'RF-01-009 Resource URI Uniqueness',
 'description': 'Traverse discoverable local Redfish resources and collection pages; assess '
                'resource identity path uniqueness within the observed scope.',
 'test_method': [{'step_1': 'Validate Task connection settings and initialize a read-only session.',
                  'criteria': 'Task supplies a valid HTTP(S) origin. No editable parameters. '
                              'Missing dependencies or program defects are Error; invalid '
                              'connection settings are Fail.'},
                 {'step_2': 'Starting at /redfish/v1/, GET local @odata.id links, including '
                            'standard and OEM links, and collection nextLink pages. Record '
                            'sources, HTTP evidence, identities and exclusions.',
                  'criteria': 'Read each discovered URL once, preserving query strings for '
                              'pagination. HTTP 200 and JSON objects with usable identity metadata '
                              'are required. Exclude external services and Actions, recording '
                              'reasons. Follow at most five same-origin redirects per request with '
                              'loop detection. Requests time out after 15 seconds. Unread '
                              'resources, invalid links or pagination cycles are Fail with scope '
                              'evidence. Redirect rules remain provisional pending RF-02.'},
                 {'step_3': 'Group declared @odata.id values by case-sensitive path and assess '
                            'duplicate identities using final response URLs and collection '
                            'pagination relationships.',
                  'criteria': 'Pass only when traversal is complete and no unresolved identity '
                              'groups remain in the observed scope. Repeated references and '
                              'redirects to the same response are not separate instances. '
                              'Validated pages of one collection are not separate instances. '
                              'Different final resource URLs declaring the same identity path are '
                              'unresolved candidates unless equivalence is established; Fail with '
                              'evidence, without claiming a confirmed collision from payload '
                              'differences. Results do not cover undiscovered resources.'}],
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


def _fetch(session, url, conf, origin, context, evidence, cache):
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
            if response.status_code in (301, 302, 307, 308):
                location = response.headers.get("Location")
                if not location:
                    raise CaseFailure("Redirect response has no Location")
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
    """Read only discoverable structured links; never invoke an Action."""
    if not isinstance(context, dict):
        raise RuntimeError("BMCAgent did not supply a dictionary execution context")
    evidence = []
    observations = {"resources": [], "links": [], "excluded": [], "unread": [],
                    "unresolved": [], "scope": "Local structured resource links and collection pages"}
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
    queue = deque([root])
    scheduled = {root}
    cache = {}
    resources = {}
    aliases = {}
    page_edges = set()
    errors = observations["unread"]

    def unread(uri, reason, source=None):
        errors.append({"uri": uri, "source": source, "reason": reason})
        _log(context, "check", "Traversal evidence available", False,
             expected="Readable local resource or page", actual=errors[-1])

    _log(context, "section", "Resource traversal and HTTP evidence", report_step=2)
    try:
        with requests.Session() as session:
            session.trust_env = False
            session.auth = (conf.get("username", ""), conf.get("password", ""))
            while queue:
                requested = queue.popleft()
                try:
                    final, body = _fetch(session, requested, conf, origin, context, evidence, cache)
                except (CaseFailure, requests.RequestException) as error:
                    reason = str(error) if isinstance(error, CaseFailure) else (
                        "HTTP request could not complete (" + type(error).__name__ + ")")
                    cache[requested] = CaseFailure(reason)
                    unread(requested, reason)
                    continue
                aliases[requested] = final
                if final in resources:
                    continue
                identity = body.get("@odata.id")
                resource_type = body.get("@odata.type")
                identity_path = None
                try:
                    declared = _url(identity, final)
                    if urlsplit(identity).fragment:
                        raise ValueError("Top-level fragment identity cannot establish a resource path")
                    identity_path = urlsplit(declared).path
                except (ValueError, TypeError):
                    unread(final, "Missing or unusable top-level @odata.id")
                if not isinstance(resource_type, str) or not resource_type:
                    unread(final, "Missing or unusable @odata.type; identity evidence is incomplete")
                if requested == root and not (
                        isinstance(resource_type, str) and re.fullmatch(
                            r"#ServiceRoot(?:\.v[0-9]+_[0-9]+_[0-9]+)?\.ServiceRoot", resource_type)):
                    unread(final, "Starting endpoint does not identify ServiceRoot")
                record = {"request_uri": requested, "final_uri": final, "@odata.id": identity,
                          "@odata.type": resource_type, "identity_path": identity_path}
                resources[final] = record
                observations["resources"].append(record)
                _log(context, "check", "Resource identity evidence",
                     identity_path is not None and isinstance(resource_type, str) and bool(resource_type),
                     expected="Resource identity path and type", actual=record)
                for kind, reference, field in _links(body):
                    source = {"resource": final, "field": field}
                    if kind == "action":
                        observations["excluded"].append({"source": source, "reason": "Actions subtree is excluded"})
                        continue
                    try:
                        target = _url(reference, final)
                    except (ValueError, TypeError):
                        unread(final, "Invalid " + kind + " link at " + field, source)
                        continue
                    link = {"source": source, "reference": reference, "target": target, "kind": kind}
                    observations["links"].append(link)
                    if _origin(target) != origin:
                        observations["excluded"].append(dict(link, reason="External service is excluded"))
                        continue
                    if "/Actions/" in urlsplit(target).path or urlsplit(target).path.endswith("/Actions"):
                        observations["excluded"].append(dict(link, reason="Action endpoint is excluded"))
                        continue
                    if kind == "page":
                        page_edges.add((final, target))
                    if target not in scheduled:
                        scheduled.add(target)
                        queue.append(target)

        resolved_edges = {(aliases.get(a, a), aliases.get(b, b)) for a, b in page_edges}
        if _has_page_cycle(resolved_edges):
            unread(root, "Collection pagination cycle detected")
        # Only explicit pages with matching collection identity/type establish equivalence.
        page_pairs = set()
        for parent, page in resolved_edges:
            left, right = resources.get(parent), resources.get(page)
            if left is None or right is None:
                continue
            kind = left["@odata.type"]
            valid = (isinstance(kind, str) and kind.endswith("Collection")
                     and kind == right["@odata.type"]
                     and left["identity_path"] is not None
                     and left["identity_path"] == right["identity_path"])
            _log(context, "check", "Collection pagination identity", valid,
                 expected="Matching collection identity and type", actual={"parent": parent, "page": page})
            if valid:
                page_pairs.add((parent, page))
            else:
                unread(page, "Pagination identity cannot be established", parent)
        _log(context, "check", "Traversal complete", not errors,
             expected="No unread in-scope resources or invalid pagination",
             actual={"resources": len(resources), "unread": errors,
                     "excluded": observations["excluded"]})
        if not resources:
            return _finish(context, "Fail", "No resource identity evidence was obtained", evidence, observations)

        _log(context, "section", "Resource URI uniqueness assessment", report_step=3)
        # Union only proven pagination relationships; redirects already share final keys.
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
            path = record["identity_path"]
            if path is not None:
                groups.setdefault(path, []).append(uri)
        for path, uris in sorted(groups.items()):
            # Query variants need explicit pagination evidence before treating them as aliases.
            instances = {find(uri) for uri in uris}
            resolved = len(instances) == 1
            details = {"identity_path": path, "responses": [resources[uri] for uri in uris],
                       "classification": "No distinct-instance evidence" if resolved else
                                         "Unresolved alias or identity collision"}
            _log(context, "check", "Identity path uniqueness within observed scope", resolved,
                 expected="One established resource identity per path", actual=details)
            if not resolved:
                observations["unresolved"].append(details)
        observations["resource_response_count"] = len(resources)
        observations["identity_path_count"] = len(groups)
        observations["traversal_complete"] = not errors
        _log(context, "check", "Scope sufficient for Pass", not errors,
             expected="Complete discovered scope", actual={"unread": errors})
    except CaseFailure:
        raise
    except Exception as error:
        observations["pending"] = list(queue)
        return _finish(context, "Error", "Unexpected program error (" + type(error).__name__ + ")",
                       evidence, observations)
    failed = bool(errors or observations["unresolved"])
    reason = (f"Traversal incomplete: {len(errors)} issue(s); unresolved identity groups: "
              f"{len(observations['unresolved'])}. No confirmed collision is inferred from payload differences."
              if failed else
              f"No unresolved identity paths among {len(resources)} resource/page responses "
              f"and {len(groups)} identity paths in the discovered scope.")
    return _finish(context, "Fail" if failed else "Pass", reason, evidence, observations)
