import io
import zipfile
import zlib
from types import SimpleNamespace
import json
import re
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

TEST_CASE = {'modified_at': "2026-11-12T09:19:33.073309+00:00",
 'test_type': 'compliance',
 'spec_ref': ['DSP0266 v1.25.0 section 6.7 Table 4 (/redfish/v1/Schemas/<SchemaFile>, Required=No); section '
 '8.4.2.1 (local schema references).',
 'DSP0268 v2026.2 section 6.61.3 (JsonSchemaFile Location/Uri and ArchiveUri/ArchiveFile).',
 'DSP0266 v1.25.0 sections 11.1.4 and 11.2.4 (CSDL and JSON Schema format).'],
 'created_at': '2026-10-30T07:27:24.936887+00:00',
 'name': 'RF-01-013 Local Schema File Endpoint',
 'description': 'Retrieve advertised local schema files and assess document recognition separately from the '
                'recommended /redfish/v1/Schemas/ endpoint.',
 'test_method': [{'step_number': 1,
                  'type': 'Action',
                  'step': 'Prepare a read-only traversal of the service.'},
                 {'step_number': 1,
                  'type': 'Checkpoint',
                  'step': 'Verify that a valid HTTP(S) service origin is available.'},
                 {'step_number': 2,
                  'type': 'Command',
                  'step': 'GET ServiceRoot, the advertised JsonSchemas collection, its pages and '
                          'descriptors.'},
                 {'step_number': 2,
                  'type': 'Checkpoint',
                  'step': 'Verify that at least one supported local schema file is declared.'},
                 {'step_number': 2,
                  'type': 'Checkpoint',
                  'step': 'Verify that all advertised declarations and pages are readable and valid.'},
                 {'step_number': 3,
                  'type': 'Command',
                  'step': 'GET each declared local schema file or archive.'},
                 {'step_number': 3,
                  'type': 'Checkpoint',
                  'step': 'Verify successful acquisition of each declared local file (HTTP 200).'},
                 {'step_number': 4,
                  'type': 'Action',
                  'step': 'Read the declared archive member if applicable and parse the schema document.'},
                 {'step_number': 4,
                  'type': 'Checkpoint',
                  'step': "Verify the minimum document structure for the declared file type:\n- JSON Schema.\n- CSDL XML.\n\nThis check performs minimum document recognition, not full schema validation."},
                 {'step_number': 4,
                  'type': 'Checkpoint',
                  'step': "For a recognized JSON schema document, assess its declared dialect:\n- PASS: Uses http://redfish.dmtf.org/schemas/v1/redfish-schema-v1.json.\n- C-PASS: Uses another dialect accepted by the supported document-recognition checks.\n\nC-PASS is a project acceptance policy. Include the actual file, dialect and acceptance reason in Note."},
                 {'step_number': 4,
                  'type': 'Checkpoint',
                  'step': 'Verify that every supported declared file was acquired and recognized.'},
                 {'step_number': 5,
                  'type': 'Action',
                  'step': 'Assess the recommended /redfish/v1/Schemas/ endpoint and the verified scope.'},
                 {'step_number': 5,
                  'type': 'Checkpoint',
                  'step': "Assess the advertised /redfish/v1/Schemas/<SchemaFile> entries:\n- PASS: At least one advertised entry was successfully retrieved and recognized.\n- C-PASS: No advertised entry was verified.\n\nC-PASS is a project acceptance policy:\n- Explain the observed scope and acceptance reason in Note.\n- Missing verified evidence does not prove that the endpoint is absent.\n- Evaluate files at other declared local locations independently."},
                 {'step_number': 5,
                  'type': 'Checkpoint',
                  'step': "Verify that all required checks completed:\n- Discovery is complete.\n- Every declared supported local file was successfully retrieved.\n- Every retrieved file passed the supported document-recognition checks.\n\nProject acceptance policy:\n- Required failures keep the Case at FAIL, even if a recommendation check is C-PASS.\n- If an unsupported archive is the only remaining obstacle, retain the Case outcome Block."}],
 'automation': 'automatic',
 'parameters': {}}


class ArchiveUnsupported(Exception):
    """The archive cannot be verified using this test's supported formats."""


class CaseFailure(AssertionError):
    """Non-program failure with an actionable reason."""


_METHOD_CHECKS = [('Task\\ origin\\ available', 1),
 ('Declared\\ local\\ files\\ found', 3),
 ('Discovery\\ evidence\\ available', 4),
 ('Discovery\\ complete', 4),
 ('Declared\\ file\\ acquisition', 6),
 ('Schema\\ document\\ recognition', 8),
 ('Recommended\\ JSON\\ schema\\ dialect', 9),
 ('All\\ declared\\ files\\ verified', 10),
 ('Recommended\\ /Schemas/\\ endpoint\\ assessment', 12),
 ('Complete\\ local\\ file\\ verification', 13)]


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
                _report_begin(context, 3)
                result={"uri":uri,"kind":kind,"acquired":False,"recognized":False}
                accept="application/json" if kind=="json" else "application/xml"
                try:
                    final,response=fetch(uri,ARCHIVE_ACCEPT if member is not None else accept)
                    result.update(final_uri=final,acquired=True)
                    _log(context,"check","Declared file acquisition",True,expected=200,
                         actual={"uri":uri,"final_uri":final,"status":200})
                    _report_begin(context, 4)
                    if member is not None:
                        result["archive_file"] = member
                        response = _archive_member(response,final,member,kind)
                    result.update(_recognize(response,kind))
                    result["recognized"]=True
                except ArchiveUnsupported as error:
                    result["blocked"] = True
                    result["reason"] = str(error)
                    observations["blocked"].append(result)
                except CaseFailure as error:
                    result["reason"]=str(error)
                    failures.append(result)
                    if not result["acquired"]:
                        _log(context,"check","Declared file acquisition",False,
                             expected=200,actual=result.copy())
                _report_begin(context, 4)
                if not result["acquired"] or result.get("blocked"):
                    context["_method_action_skip"] = result.get("reason", "File acquisition did not complete")
                _log(context,"check","Schema document recognition",result["recognized"],
                     judgement="Skip" if not result["acquired"] or result.get("blocked") else None,
                     reason=result.get("reason"),
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
                         expected=preferred, actual={"uri":uri,"archive_file":member,"dialect":actual}, note=note)
                observations["files"].append(result)
            _report_begin(context, 4)
            _log(context,"check","All declared files verified",bool(files) and not failures and not observations["blocked"],
                 expected="At least one file; every supported declared file acquired and recognized",
                 actual={"files":len(files),"failures":len(failures)},
                 judgement="Skip" if observations["blocked"] and not failures else None,
                 reason="Unsupported archive prevented complete verification" if observations["blocked"] and not failures else None)
            _log(context,"section","Recommended Schema endpoint and scope",report_step=5)
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
                    "(should support). The recommendation check is accepted as C-PASS; "
                    "other declared local locations are evaluated independently. "
                    "This does not prove that the /Schemas/ entry is absent.") if not recommended else None
            _log(context,"check","Recommended /Schemas/ endpoint assessment",True,
                 expected="At least one verified advertised entry at /redfish/v1/Schemas/<SchemaFile>",
                 actual={"entries":recommended,"recommendation_met":bool(recommended)}, note=note)
            _log(context,"check","Complete local file verification",not errors and bool(files) and not failures and not observations["blocked"],
                 expected="Complete discovery and all declared local files verified",
                 actual={"discovery_errors":errors,"files":observations["files"]},
                 judgement="Skip" if observations["blocked"] and not errors and not failures else None,
                 reason="Unsupported archive prevented complete verification" if observations["blocked"] and not errors and not failures else None)
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
