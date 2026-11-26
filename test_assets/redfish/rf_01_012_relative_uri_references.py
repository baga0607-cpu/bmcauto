import json
import re
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit

TEST_CASE = {'modified_at': '2026-11-26T04:03:58.628274+00:00',
 'test_type': 'compliance',
 'spec_ref': ['DSP0266 v1.25.0 sections 6.1 and 6.7 (relative references in response bodies and HTTP headers).',
 'RFC 3986 section 4.2 (relative-reference syntax); Redfish section 6.7 imposes narrower allowed '
 'forms.', 'RFC 8288 section 3 (Link parameter syntax) and Appendix B.3 (compatible parsing).'],
 'created_at': '2026-10-30T07:19:35.437164+00:00',
 'name': 'RF-01-012 Relative URI References',
 'description': 'Inspect discovered Body and GET-response header URI references for the Redfish '
                'relative-reference form requirement.',
 'command_routes': {'bmc_redfish': {'from': 'bmcagent', 'to': 'bmc', 'method': 'redfish',
                                    'lan_port': 'task.bmc.lan_ports.port1',
                                    'username': 'task.bmc.username', 'password': 'task.bmc.password'}},
 'test_method': [{'step_number': 1,
                  'type': 'Action',
                  'step': 'Prepare a read-only traversal of the service.',
                  'checkpoints': {
                      'service_origin_valid': {'expected': 'Verify that a valid HTTP(S) service origin is available.'},
                  }},
                 {'step_number': 2,
                  'type': 'Command',
                  'route': 'bmc_redfish',
                  'step': 'GET discoverable local resources and collection pages from /redfish/v1/. Do not '
                          'invoke Actions or fetch external services. Inspect each response before following '
                          'same-origin 301, 302, 307 or 308 redirects (maximum five).',
                  'checkpoints': {
                      'link_header_syntax': {'expected': 'Verify Link header parameter syntax under RFC 8288 section 3. Values containing non-token characters must be quoted. Record syntax failures while continuing compatible parsing and subsequent URI checks.'},
                      'traversal_complete': {'expected': "Verify that traversal completed without:\n- Resources that could not be read.\n- Invalid links.\n- Pagination errors."},
                  }},
                 {'step_number': 3,
                  'type': 'Action',
                  'step': 'Classify original Body and GET-response header URI references before resolution.',
                  'checkpoints': {
                      'uri_reference_form': {'expected': "Verify that each relative reference uses either accepted form:\n- /path: starts with a single /.\n- //authority/path: starts with // and includes a valid authority.\n\nAbsolute URIs are also allowed."},
                      'relative_reference_present': {'expected': "Verify that at least one applicable relative reference was found.\n\nProject coverage policy: no applicable references means FAIL for this check."},
                      'discovered_scope_assessed': {'expected': "Verify that all items within the discovered scope were assessed.\n\nProject coverage policy: incomplete coverage prevents PASS."},
                  }}],
 'automation': 'automatic',
 'parameters': {}}


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


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




def _classify(raw):
    """Classify before urljoin can hide a relative-path defect."""
    if not isinstance(raw, str):
        return "unknown", ["URI reference is not a string"]
    if not raw:
        return "relative", ["Empty relative reference"]
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in raw):
        return "unknown", ["URI reference contains whitespace or control characters"]
    try:
        parts = urlsplit(raw)
        if parts.netloc:
            parts.port
    except ValueError:
        return "unknown", ["URI authority cannot be parsed"]
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw):
        return "absolute", []
    if raw.startswith("//"):
        if not parts.netloc or not parts.hostname or raw.startswith("///"):
            return "relative", ["Network-path reference has no valid authority"]
        return "relative", []
    if raw.startswith("/"):
        return "relative", []
    return "relative", ["Relative reference must start with / or //authority"]


def _link_references(header, syntax_issues=None):
    """Parse Link targets and anchor parameters with quoted/angle-bracket boundaries."""
    if not isinstance(header, str) or not header.strip():
        raise CaseFailure("Empty or non-string Link header")
    values, start, quoted, escaped, angle = [], 0, False, False, False
    for index, char in enumerate(header):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif angle:
            if char == ">":
                angle = False
            elif char == "<":
                raise CaseFailure("Nested angle bracket in Link header")
        elif char == '"':
            quoted = True
        elif char == "<":
            angle = True
        elif char == ",":
            values.append(header[start:index].strip())
            start = index + 1
    if quoted or angle or escaped:
        raise CaseFailure("Unterminated Link header delimiter")
    values.append(header[start:].strip())
    results = []
    token = r"[!#$%&'*+.^_\x60|~0-9A-Za-z-]+"
    # Accept unquoted URI-like values with unambiguous boundaries (RFC8288 B.3).
    # Keep names token-only; reject whitespace, controls and broken delimiters.
    unquoted = r'[^\s;,"<>\\\x00-\x1f\x7f]+'
    parameter = re.compile(r"[ \t]*;[ \t]*(" + token + r')[ \t]*(?:=[ \t]*("(?:\\.|[^"\\])*"|' + unquoted + r"))?[ \t]*(?=;|$)")
    for index, value in enumerate(values):
        match = re.match(r"^<([^<>]*)>", value)
        if not match:
            raise CaseFailure("Link value has no delimited URI target")
        results.append((f"Link[{index}]/target", match.group(1)))
        offset = match.end()
        anchor_seen = False
        while value[offset:].strip():
            param = parameter.match(value, offset)
            if not param:
                raise CaseFailure(f"Uninterpretable Link parameter at Link[{index}], offset {offset}: {value[offset:offset + 120]!r}")
            name, text = param.groups()
            if text is not None and not text.startswith('"') and not re.fullmatch(token, text):
                if syntax_issues is not None:
                    syntax_issues.append({"field": f"Link[{index}]/{name}", "parameter": name,
                                          "value": text, "reason": "Parameter value contains non-token characters and requires double quotes"})
            if name.lower() == "anchor":
                if anchor_seen or text is None:
                    raise CaseFailure("Missing or duplicate Link anchor value")
                anchor_seen = True
                if text.startswith('"'):
                    text = re.sub(r"\\(.)", r"\1", text[1:-1])
                results.append((f"Link[{index}]/anchor", text))
            offset = param.end()
    return results


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
                elif ("Uri" in key or "URI" in key) and isinstance(child, str):
                    yield "property", child, location
                elif isinstance(child, (dict, list)):
                    stack.append((child, location, actions))
        elif isinstance(value, list):
            stack.extend((child, field + "/" + str(index), in_actions)
                         for index, child in enumerate(value))


def _reject_json_constant(value):
    raise ValueError("Non-finite JSON constant: " + value)


def _resource_body(response):
    if response.status != 200:
        raise CaseFailure(f"Expected HTTP status = 200; Received HTTP status = {response.status}")
    try:
        body = json.loads(response.text, parse_constant=_reject_json_constant)
    except ValueError:
        raise CaseFailure("Response body is not valid JSON") from None
    if not isinstance(body, dict):
        raise CaseFailure("Response body is not a JSON object")
    return body


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
    from case_log import ReportedCase
    report = ReportedCase(context, TEST_CASE, CaseFailure)
    observations = {"resources": [], "uris": [], "violations": [], "excluded": [], "unread": [],
                    "header_errors": [], "header_syntax_errors": [], "header_observations": [],
                    "scope": "Explicit Body URI fields and observed GET Location/Content-Location/Link headers"}
    report.begin_step(1)
    from redfish_route import RedfishRoute
    route_name = next(m["route"] for m in TEST_CASE["test_method"] if m.get("step_number") == 2 and "route" in m)
    try:
        route = RedfishRoute(context, TEST_CASE["command_routes"][route_name])
        host = _url(route.host, "")
        origin = _origin(host)
    except (ValueError, TypeError):
        reason = "Task BMC URL is missing or invalid"
        report.checkpoint("service_origin_valid", "FAIL", reason=reason, expected="HTTP(S) origin",
             actual="Missing or invalid Task BMC URL")
        return report.finish(observations, blocked=reason, operation_failure=reason)
    report.checkpoint("service_origin_valid", "PASS", expected="HTTP(S) origin",
         actual=urlunsplit((urlsplit(host).scheme, urlsplit(host).netloc, "", "", "")))
    root = _url("/redfish/v1/", host)
    queue, scheduled = deque([root]), {root}
    resources, aliases, page_edges = set(), {}, set()
    errors = observations["unread"]

    def unread(uri, reason, source=None):
        errors.append({"uri": uri, "source": source, "reason": reason})
        report.checkpoint("traversal_complete", "FAIL", reason=reason,
             expected="Readable in-scope resource or page", actual=errors[-1])

    def inspect_uri(raw, source, field, kind):
        classification, issues = _classify(raw)
        item = {"source": source, "field": field, "uri": raw, "kind": kind, "classification": classification, "issues": issues}
        observations["uris"].append(item)
        if issues:
            observations["violations"].append(item)
        return issues


    redirect_statuses = (301, 302, 307, 308)

    def inspect_hop(hop):
        uri, present = hop.uri, hop.headers
        names = ("location", "content-location", "link")
        observations["header_observations"].append({
            "response_uri": uri, "present": [n for n in names if n in present],
            "absent": [n for n in names if n not in present]})
        location_issues = []
        for name in ("location", "content-location"):
            for value in present.get(name, []):
                issues = inspect_uri(value, uri, "headers/" + name, "header")
                if name == "location":
                    location_issues.extend(issues)
        if "link" in present:
            details = []
            for header_index, value in enumerate(present["link"], 1):
                syntax_issues = []
                try:
                    for field, reference in _link_references(value, syntax_issues):
                        inspect_uri(reference, uri, "headers/" + field, "header")
                except CaseFailure as error:
                    item = {"source": uri, "evidence_id": hop.evidence_id, "header_index": header_index, "reason": str(error)}
                    observations["header_errors"].append(item)
                    unread(uri, "Link header cannot be completely interpreted", item)
                    syntax_issues.append({"reason": str(error)})
                details.extend(dict(issue, header_index=header_index) for issue in syntax_issues)
            observations["header_syntax_errors"].extend(details)
            report.checkpoint("link_header_syntax", "FAIL" if details else "PASS",
                 reason="Link header contains invalid parameter syntax" if details else "",
                 expected="RFC 8288 parameter values use token or quoted-string syntax",
                 actual={"uri": uri, "evidence_id": hop.evidence_id, "issues": details})
        if hop.status in redirect_statuses and location_issues:
            raise CaseFailure("Advertised redirect URI violates relative-reference rules")

    def allow_target(uri):
        path = urlsplit(uri).path
        return "/Actions/" not in path and not path.endswith("/Actions")

    report.begin_step(2)
    try:
        with route.traversal(redirect_statuses=redirect_statuses, max_redirects=5,
                             allow_target=allow_target, inspect_hop=inspect_hop) as get:
            while queue:
                requested = queue.popleft()
                try:
                    response = get(requested)
                    final, body = response.uri, _resource_body(response)
                except (CaseFailure, ValueError) as error:
                    reason = str(error)
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
                    if kind in ("action", "context", "property"):
                        observations["excluded"].append({"source": source, "uri": reference,
                                                         "reason": "Inspected only; no Action, metadata or non-resource request"})
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
        if not any("link" in item["present"] for item in observations["header_observations"]):
            if errors:
                status = "Not executed"
                reason = "No Link header observed; traversal was incomplete: " + errors[0]["reason"]
            else:
                status = "Skip"
                reason = "No response in the completed traversal contained a Link header."
            report.checkpoint("link_header_syntax", status, reason=reason)
        report.checkpoint("traversal_complete", "FAIL" if errors else "PASS",
             reason=errors[0]["reason"] if errors else "",
             expected="No unread in-scope resources or pages",
             actual={"source": "Traversal complete", "value": {"resources": len(resources),
                    "unread": errors, "excluded": observations["excluded"]}})
        if not observations["uris"]:
            return report.finish(observations, blocked="No service-provided URI evidence was obtained")
        report.begin_step(3)
        for item in observations["uris"]:
            report.checkpoint("uri_reference_form", "FAIL" if item["issues"] else "PASS", reason=", ".join(item["issues"]),
                 expected="Absolute URI or relative reference starting with / or //authority", actual=item)

        counts = {area: {category: 0 for category in ("relative", "absolute", "unknown")}
                  for area in ("body", "headers")}
        for item in observations["uris"]:
            counts["headers" if item["kind"] == "header" else "body"][item["classification"]] += 1
        observations["counts"] = counts
        relative_count = sum(values["relative"] for values in counts.values())
        observations["relative_reference_count"] = relative_count
        seen_headers = {name for item in observations["header_observations"] for name in item["present"]}
        observations["absent_headers"] = sorted({"location", "content-location", "link"} - seen_headers)
        report.checkpoint("relative_reference_present", "PASS" if relative_count else "FAIL",
             reason="" if relative_count else "No applicable relative URI references were found",
             expected="At least one relative reference in the observed GET scope",
             actual={"counts": counts, "absent_headers": observations["absent_headers"]})
        observations["resource_response_count"] = len(resources)
        observations["uri_occurrence_count"] = len(observations["uris"])
        observations["traversal_complete"] = not errors
        report.checkpoint("discovered_scope_assessed", "FAIL" if errors else "PASS", reason=errors[0]["reason"] if errors else "",
             expected="Complete discovered scope", actual={"unread": errors})
    except CaseFailure:
        raise
    except Exception as error:
        observations["pending"] = list(queue)
        return report.finish(observations, error="Unexpected program error (" + type(error).__name__ + ")")
    summary = (f"Relative references: {relative_count}; relative URI violations: {len(observations['violations'])}; "
               f"Link syntax issues: {len(observations['header_syntax_errors'])}; traversal issues: {len(errors)}")
    return report.finish(observations, summary=summary)
