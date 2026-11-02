import io
import zipfile
import zlib
from types import SimpleNamespace
import json
import re
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

TEST_CASE = {
    "modified_at": "2026-11-02T07:51:48.596919+00:00",
    "test_type": "compliance",
    "spec_ref": [
        "DSP0266 v1.25.0 section 6.7 Table 4 (/redfish/v1/Schemas/<SchemaFile>, Required=No); section 8.4.2.1 (local schema references).",
        "DSP0268 v2026.2 section 6.61.3 (JsonSchemaFile Location/Uri and ArchiveUri/ArchiveFile).",
        "DSP0266 v1.25.0 sections 11.1.4 and 11.2.4 (CSDL and JSON Schema format).",
        "BMCAgent RF-01-013 acceptance policy: declared local supported files are accepted independently of /Schemas/ evidence; minimum recognition is not full schema validation."
    ],
    'created_at': '2026-10-30T07:27:24.936887+00:00',
 'name': 'RF-01-013 Local Schema File Endpoint',
 'description': 'Retrieve advertised local schema files and assess document recognition separately '
                'from the recommended /redfish/v1/Schemas/ endpoint.',
 'test_method': [{'step_1': 'Validate Task settings and initialize a read-only session.',
                  'criteria': 'A valid Task HTTP(S) origin is required. Invalid settings are Fail; '
                              'missing dependencies or program defects are Error.'},
                 {'step_2': 'GET ServiceRoot and follow its JsonSchemas collection, all pages and '
                            'member descriptors. Collect declared local files and archive members without '
                            'guessing filenames.',
                  'criteria': 'All discovered descriptors/pages are readable JSON objects. '
                              'Preserve declarations, exclusions and HTTP evidence. Only local '
                              'individual files and declared archive members are tested. External locations are '
                              'not fetched. Unsupported archive formats are blocked; invalid declarations are '
                              'failures. No local URI or incomplete discovery is '
                              'Fail.'},
                 {'step_3': 'GET every distinct declared local JSON/XML schema file with a '
                            'format-appropriate Accept header and recognize its document '
                            'structure, reading the exact ArchiveFile member when archived.',
                  'criteria': 'Final HTTP status is 200. JSON requires an object with a nonempty '
                              'string $schema and object definitions; the recognized '
                              '2019-09/2020-12 dialects may instead use object $defs. Other shapes '
                              'are outside this minimum recognition profile, not automatically '
                              'invalid JSON Schema. CSDL XML contains a Schema element in the '
                              'OData EDM namespace, independent of prefix. DTDs are not processed. '
                              'Record per-file acquisition and recognition outcomes separately. '
                              'This is not full schema validation.'},
                 {'step_4': 'Assess the recommended /redfish/v1/Schemas/<SchemaFile> entry and '
                            'summarize the observed scope.',
                  'criteria': 'Record the recommended /Schemas/ entry independently (DSP0266 1.25.0, '
                              'section 6.7 Table 4, Required=No). Missing entry evidence is accepted '
                              'as PASS with Note, never proof that the entry is absent. Accept '
                              'declared local file locations without a path-prefix whitelist '
                              '(DSP0268 2026.2 section 6.61). Overall Pass requires complete '
                              'discovery and every tested local file to pass; unsupported archive formats yield Block unless a failure is proven.'}],
 'automation': 'automatic',
 'parameters': {}}


class ArchiveUnsupported(Exception):
    """The archive cannot be verified using this test's supported formats."""


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
    context["_tc_status"] = {"Pass": "PASS", "Block": "BLOCK"}.get(status, "FAIL")
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



class UnsupportedDTD(ValueError):
    pass


class SchemaTreeBuilder(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise UnsupportedDTD("DTD processing is disabled")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON property")
        result[key] = value
    return result


def _bad_constant(value):
    raise ValueError("Non-finite JSON constant")


def _json(text):
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_bad_constant)
    except ValueError:
        raise CaseFailure("Response is not an unambiguous JSON document") from None
    if not isinstance(value, dict):
        raise CaseFailure("Response is not a JSON object")
    return value


def _local(raw, base, origin):
    target = _url(raw, base)
    if urlsplit(raw).fragment:
        raise ValueError("File or discovery URI contains a fragment")
    if _origin(target) != origin:
        raise ValueError("URI leaves the Task origin")
    path = urlsplit(target).path
    if "/Actions/" in path or path.endswith("/Actions"):
        raise ValueError("Action endpoint is excluded")
    return target


def _fetch(session, uri, accept, conf, origin, context, evidence, cache):
    chain, current = [], uri
    try:
        for hop in range(6):
            if current in chain:
                raise CaseFailure("Redirect loop detected")
            key = (current, accept)
            if key in cache:
                result = cache[key]
                if isinstance(result, Exception):
                    raise result
                for alias in chain:
                    cache[(alias, accept)] = result
                return result
            chain.append(current)
            response = session.get(current, headers={"Accept":accept},
                                   verify=conf.get("verify_ssl",False), timeout=15, allow_redirects=False)
            headers = {k:v for k,v in response.headers.items()
                       if k.lower() not in ("set-cookie","authorization","x-auth-token")}
            body_log = (f"[Archive: {len(response.content)} bytes]" if accept == ARCHIVE_ACCEPT else response.text)
            evidence.append({"uri":current,"status":response.status_code,
                             "headers":headers,"body":body_log,"accept":accept})
            _log(context,"http","GET",current,response.status_code,headers,body_log,
                 request_headers={"Accept":accept})
            if response.status_code in (301,302,307,308):
                location=response.headers.get("Location")
                if not location:
                    raise CaseFailure("Redirect response has no Location")
                try:
                    target=_local(location,current,origin)
                except (ValueError,TypeError):
                    raise CaseFailure("Redirect URL is invalid or outside the permitted local scope") from None
                if hop==5:
                    raise CaseFailure("Redirect limit exceeded (5 redirects)")
                current=target
                continue
            if response.status_code!=200:
                raise CaseFailure(f"Expected HTTP status = 200; Received HTTP status = {response.status_code}")
            result=(current,response)
            for alias in chain:
                cache[(alias,accept)]=result
            return result
        raise CaseFailure("Redirect could not complete")
    except Exception as error:
        for alias in chain:
            cache[(alias,accept)]=error
        raise


ARCHIVE_ACCEPT = "*/*"
MAX_MEMBER_BYTES = 32 * 1024 * 1024


def _archive_member(response, uri, member, kind):
    data = io.BytesIO(response.content)
    if not zipfile.is_zipfile(data):
        if urlsplit(uri).path.lower().endswith(".zip") or response.content.startswith(b"PK"):
            raise CaseFailure("Declared ZIP is invalid")
        raise ArchiveUnsupported("Unsupported archive format; member was not verified")
    try:
        with zipfile.ZipFile(data) as archive:
            matches = [item for item in archive.infolist() if item.filename == member]
            if len(matches) != 1 or matches[0].is_dir():
                raise CaseFailure("Declared ArchiveFile is missing or ambiguous: " + member)
            item = matches[0]
            if item.flag_bits & 1 or item.file_size > MAX_MEMBER_BYTES:
                raise ArchiveUnsupported("Encrypted or oversized member exceeds test capability")
            with archive.open(item) as stream:
                content = stream.read(MAX_MEMBER_BYTES + 1)
            if len(content) > MAX_MEMBER_BYTES:
                raise ArchiveUnsupported("Member exceeds test size limit")
            return SimpleNamespace(content=content, text=content.decode("utf-8-sig") if kind == "json" else "")
    except NotImplementedError as error:
        raise ArchiveUnsupported("Unsupported ZIP compression") from error
    except (zipfile.BadZipFile, UnicodeError, EOFError, zlib.error) as error:
        raise CaseFailure("Invalid ZIP member or document encoding") from error


def _recognize(response, kind):
    if kind=="json":
        body=_json(response.text)
        dialect=body.get("$schema")
        if not isinstance(dialect,str) or not dialect.strip():
            raise CaseFailure("JSON schema recognition requires a nonempty string $schema")
        if isinstance(body.get("definitions"),dict):
            return {"format":"JSON","profile":"definitions","dialect":dialect}
        modern = dialect.rstrip("#") in (
            "https://json-schema.org/draft/2019-09/schema",
            "https://json-schema.org/draft/2020-12/schema")
        if modern and isinstance(body.get("$defs"),dict):
            return {"format":"JSON","profile":"$defs","dialect":dialect}
        raise CaseFailure("JSON document is outside the minimum schema recognition profile; full schema validity is not determined")
    try:
        body=ET.fromstring(response.content,parser=ET.XMLParser(target=SchemaTreeBuilder()))
    except UnsupportedDTD:
        raise CaseFailure("XML DTD processing is disabled; document remains unverified") from None
    except (ET.ParseError,LookupError,ValueError):
        raise CaseFailure("Response could not be parsed as XML") from None
    count=sum(1 for element in body.iter() if element.tag=="{http://docs.oasis-open.org/odata/ns/edm}Schema")
    if not count:
        raise CaseFailure("XML contains no Schema element in the OData EDM namespace")
    return {"format":"XML","profile":"CSDL Schema","schema_elements":count}


def _recommended(uri):
    path=urlsplit(uri).path
    prefix="/redfish/v1/Schemas/"
    if not path.startswith(prefix):
        return False
    name=path[len(prefix):]
    return bool(name) and "/" not in name and "%" not in name and name not in (".","..")


def execute(client,context=None,preset=None):
    if not isinstance(context,dict):
        raise RuntimeError("BMCAgent did not supply a dictionary execution context")
    evidence=[]
    observations={"declarations":[],"files":[],"excluded":[],"discovery_errors":[],
                  "blocked":[],"scope":"Declared local files and archive members from the advertised JsonSchemas collection"}
    errors=observations["discovery_errors"]
    _log(context,"section","Task connection settings",report_step=1)
    conf=context.get("redfish")
    try:
        if not isinstance(conf,dict):
            raise ValueError("Missing Task settings")
        host=_url(conf.get("host"),"")
        origin=_origin(host)
    except (ValueError,TypeError):
        return _finish(context,"Fail","Task BMC URL is missing or invalid",evidence,observations)
    try:
        import requests
    except ImportError:
        return _finish(context,"Error","Required requests package is unavailable",evidence,observations)
    _log(context,"check","Task origin available",True,expected="HTTP(S) origin",
         actual=urlunsplit((urlsplit(host).scheme,urlsplit(host).netloc,"","","")))
    cache={}
    files={}
    pages=set()
    descriptors=set()
    edges=set()
    aliases={}
    failures=[]

    def issue(uri,reason):
        item={"uri":uri,"reason":reason}
        errors.append(item)
        _log(context,"check","Discovery evidence available",False,
             expected="Readable complete local schema declaration",actual=item)

    _log(context,"section","Schema file discovery",report_step=2)
    try:
        with requests.Session() as session:
            session.trust_env=False
            session.auth=(conf.get("username",""),conf.get("password",""))

            def fetch(uri,accept="application/json"):
                try:
                    return _fetch(session,uri,accept,conf,origin,context,evidence,cache)
                except requests.RequestException as error:
                    raise CaseFailure("HTTP request could not complete ("+type(error).__name__+")") from None

            def document(uri):
                final,response=fetch(uri)
                return final,_json(response.text)

            root=_url("/redfish/v1/",host)
            queue=deque()
            scheduled=set()
            try:
                final,body=document(root)
                if not isinstance(body.get("@odata.type"),str) or not re.fullmatch(
                        r"#ServiceRoot(?:\.v[0-9]+_[0-9]+_[0-9]+)?\.ServiceRoot",body["@odata.type"]):
                    raise CaseFailure("Starting endpoint does not identify ServiceRoot")
                link=body.get("JsonSchemas")
                if not isinstance(link,dict):
                    raise CaseFailure("ServiceRoot did not advertise a JsonSchemas collection; no URL was guessed")
                uri=_local(link.get("@odata.id"),final,origin)
                queue.append((uri,"page"))
                scheduled.add((uri,"page"))
            except (CaseFailure,ValueError,TypeError) as error:
                issue(root,str(error))

            while queue:
                uri,role=queue.popleft()
                try:
                    final,body=document(uri)
                    aliases[uri]=final
                    visited=pages if role=="page" else descriptors
                    if final in visited:
                        continue
                    visited.add(final)
                    if role=="page":
                        members=body.get("Members")
                        if not isinstance(members,list):
                            raise CaseFailure("JsonSchemas collection page has no Members array")
                        for index,member in enumerate(members):
                            try:
                                if not isinstance(member,dict):
                                    raise ValueError("Member is not an object")
                                target=_local(member.get("@odata.id"),final,origin)
                                if (target,"descriptor") not in scheduled:
                                    scheduled.add((target,"descriptor"))
                                    queue.append((target,"descriptor"))
                            except (ValueError,TypeError) as error:
                                issue(final,f"Invalid member {index}: {error}")
                        for key in ("Members@odata.nextLink","@odata.nextLink"):
                            if key in body:
                                target=_local(body[key],final,origin)
                                edges.add((final,target))
                                if (target,"page") not in scheduled:
                                    scheduled.add((target,"page"))
                                    queue.append((target,"page"))
                        continue
                    locations=body.get("Location")
                    if not isinstance(locations,list):
                        raise CaseFailure("Schema descriptor has no Location array")
                    for index,location in enumerate(locations):
                        field=f"Location/{index}"
                        if not isinstance(location,dict):
                            issue(final,field+" is not an object")
                            continue
                        if "PublicationUri" in location:
                            observations["excluded"].append({"source":final,"field":field+"/PublicationUri",
                                "uri":location["PublicationUri"],"reason":"Publication location is not a declared local file"})
                        if not any(key in location for key in ("Uri","ArchiveUri","PublicationUri")):
                            issue(final,field+": no recognizable file location")
                        for key in ("Uri", "ArchiveUri"):
                            if key not in location:
                                continue
                            member = location.get("ArchiveFile") if key == "ArchiveUri" else None
                            raw = location[key]
                            declaration = {"source":final,"field":field+"/"+key,"uri":raw}
                            observations["declarations"].append(declaration)
                            try:
                                target = _local(raw,final,origin)
                                if key == "ArchiveUri":
                                    if not isinstance(member,str) or not member.strip():
                                        raise ValueError("ArchiveUri needs an ArchiveFile member name")
                                    declaration["archive_file"] = member
                                filename = member if member is not None else urlsplit(target).path
                                kind = filename.rsplit(".",1)[-1].lower()
                                if kind not in ("json","xml"):
                                    raise ValueError("Unsupported declared schema filename")
                            except (ValueError,TypeError) as error:
                                issue(final,field+": "+str(error))
                                continue
                            declaration.update(resolved_uri=target,kind=kind)
                            files.setdefault((target,member),kind)
                except (CaseFailure,ValueError,TypeError) as error:
                    issue(uri,str(error))

            if _has_page_cycle({(aliases.get(a,a),aliases.get(b,b)) for a,b in edges}):
                issue(root,"JsonSchemas pagination cycle detected")
            _log(context,"check","Declared local files found",bool(files),
                 expected="At least one supported individual local schema file",
                 actual={"count":len(files),"declarations":observations["declarations"]})
            _log(context,"check","Discovery complete",not errors,
                 expected="No unread declarations or pages",actual=errors)
            _log(context,"section","Declared schema file acquisition and recognition",report_step=3)
            for (uri,member),kind in files.items():
                result={"uri":uri,"kind":kind,"acquired":False,"recognized":False}
                accept="application/json" if kind=="json" else "application/xml"
                try:
                    final,response=fetch(uri,ARCHIVE_ACCEPT if member is not None else accept)
                    result.update(final_uri=final,acquired=True)
                    _log(context,"check","Declared file acquisition",True,expected=200,
                         actual={"uri":uri,"final_uri":final,"status":200})
                    if member is not None:
                        result["archive_file"] = member
                        response = _archive_member(response,final,member,kind)
                    result.update(_recognize(response,kind))
                    result["recognized"]=True
                except ArchiveUnsupported as error:
                    result["reason"] = str(error)
                    observations["blocked"].append(result)
                except CaseFailure as error:
                    result["reason"]=str(error)
                    failures.append(result)
                    if not result["acquired"]:
                        _log(context,"check","Declared file acquisition",False,
                             expected=200,actual=result.copy())
                _log(context,"check","Schema document recognition",result["recognized"],
                     expected="Recognized JSON Schema or CSDL XML minimum structure",actual=result.copy())
                if result["recognized"] and kind == "json":
                    preferred = "http://redfish.dmtf.org/schemas/v1/redfish-schema-v1.json"
                    actual = result["dialect"]
                    schema_source = f"{uri} member {member!r}" if member is not None else uri
                    note = None if actual == preferred else (
                        f"{schema_source} declares $schema={actual!r}. DSP0266 v1.25.0 section "
                        f"11.2.4 Table 29 recommends {preferred}. The document passed "
                        "the supported JSON recognition checks; the dialect difference is accepted."
                    )
                    _log(context, "check", "Recommended JSON schema dialect", True,
                         expected=preferred, actual=actual, note=note)
                observations["files"].append(result)
            _log(context,"check","All declared files verified",bool(files) and not failures and not observations["blocked"],
                 expected="At least one file; every supported declared file acquired and recognized",
                 actual={"files":len(files),"failures":len(failures)})
            _log(context,"section","Recommended Schema endpoint and scope",report_step=4)
            recommended=[]
            for result in observations["files"]:
                result["recommended_entry"]=result["recognized"] and "archive_file" not in result and (
                    _recommended(result["uri"]) or _recommended(result["final_uri"]))
                if result["recommended_entry"]:
                    recommended.append(result["uri"])
            observations["recommended_entries"]=recommended
            observations["discovery_complete"]=not errors
            note = ("No verified advertised /redfish/v1/Schemas/<SchemaFile> entry was found. "
                    "DSP0266 1.25.0 section 6.7 Table 4 marks this entry Required=No "
                    "(should support). The recommendation check is accepted as PASS; "
                    "other declared local locations are evaluated independently. "
                    "This does not prove that the /Schemas/ entry is absent.") if not recommended else None
            _log(context,"check","Recommended /Schemas/ endpoint assessment",True,
                 expected="At least one verified advertised entry at /redfish/v1/Schemas/<SchemaFile>",
                 actual={"entries":recommended,"recommendation_met":bool(recommended)}, note=note)
            _log(context,"check","Complete local file verification",not errors and bool(files) and not failures and not observations["blocked"],
                 expected="Complete discovery and all declared local files verified",
                 actual={"discovery_errors":errors,"files":observations["files"]})
    except Exception as error:
        return _finish(context,"Error","Unexpected program error ("+type(error).__name__+")",
                       evidence,observations)
    if observations["blocked"] and not errors and not failures:
        return _finish(context,"Block",observations["blocked"][0]["reason"],evidence,observations)
    passed=not errors and bool(files) and not failures and not observations["blocked"]
    reason=("All discovered local schema files verified; recommendation recorded separately"
            if passed else f"Discovery issues: {len(errors)}; file failures: {len(failures)}; "
            f"verified recommended entries: {len(recommended)} (informational only).")
    return _finish(context,"Pass" if passed else "Fail",reason,evidence,observations)
