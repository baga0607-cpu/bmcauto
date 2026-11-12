import json
import re
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit

TEST_CASE = {'modified_at': "2026-11-12T09:19:33.010505+00:00",
 'test_type': 'compliance',
 'spec_ref': ['DSP0266 v1.25.0 section 6.1 (unique resource paths); section 9.6.2 (resource identity); section '
 '7.2.2 (collection pagination).'],
 'created_at': '2026-10-30T06:05:45.102559+00:00',
 'name': 'RF-01-009 Resource URI Uniqueness',
 'description': 'Traverse discoverable local Redfish resources and collection pages; assess resource '
                'identity path uniqueness within the observed scope.',
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
                  'step': 'Verify that each resource supplies usable identity and type metadata.'},
                 {'step_number': 2,
                  'type': 'Checkpoint',
                  'step': 'Verify matching collection identity and type across pagination links.'},
                 {'step_number': 2,
                  'type': 'Checkpoint',
                  'step': "Verify that traversal completed without:\n- Resources that could not be read.\n- Invalid links.\n- Pagination errors."},
                 {'step_number': 3,
                  'type': 'Action',
                  'step': 'Group identity paths and compare resource URLs and proven collection-page '
                          'relationships.'},
                 {'step_number': 3,
                  'type': 'Checkpoint',
                  'step': "Verify that each observed identity path maps to one established resource identity.\n\nProject coverage policy:\n- An unresolved identity group fails this check.\n- An unresolved group does not, by itself, prove an identity collision."},
                 {'step_number': 3,
                  'type': 'Checkpoint',
                  'step': "Verify that all items within the discovered scope were assessed.\n\nProject coverage policy: incomplete coverage prevents PASS."},
                 {'step_number': 3,
                  'type': 'Record',
                  'step': 'Record the number of resource/page responses observed.',
                  'observation': 'resource_response_count'},
                 {'step_number': 3,
                  'type': 'Record',
                  'step': 'Record the number of distinct identity paths observed.',
                  'observation': 'identity_path_count'}],
 'automation': 'automatic',
 'parameters': {}}


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


_METHOD_CHECKS = [('Task\\ origin\\ available', 1),
 ('Resource\\ identity\\ evidence', 3),
 ('Collection\\ pagination\\ identity', 4),
 ('Traversal\\ evidence\\ available', 5),
 ('Traversal\\ complete', 5),
 ('Identity\\ path\\ uniqueness\\ within\\ observed\\ scope', 7),
 ('Scope\\ sufficient\\ for\\ Pass', 8)]


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
