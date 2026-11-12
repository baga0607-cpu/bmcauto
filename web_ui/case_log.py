"""Per-execution readable logs. Sections describe evidence, never execution steps."""
from datetime import datetime, timezone
from result_policy import validate_method, validate_case_cp
import json
import re
from pathlib import Path
from uuid import uuid4
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_SECRET_HEADERS = {'authorization', 'proxy-authorization', 'cookie', 'set-cookie', 'x-auth-token'}
_SECRET_QUERY = {'password', 'passwd', 'token', 'access_token', 'api_key'}


def log_filenames(task_name, case_name, task_id, case_id):
    """A fresh local-time/offset and run identity for each test execution."""
    def label(value, limit):
        value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(value)).strip(' .')
        return value.encode('utf-16-le')[:limit * 2].decode('utf-16-le', errors='ignore').rstrip(' .') or 'unnamed'
    match = re.match(r'^([A-Za-z]+-\d+(?:-\d+)+)\b', str(case_name))
    case_label = match.group(1) if match else case_id
    stamp = datetime.now().astimezone().strftime('%Y%m%d_%H%M%S_%f%z')
    stem = f'{stamp}__{label(task_name, 24)}__{label(case_label, 36)}__{uuid4().hex}'
    return {'test': f'{stem}__test.log'}


def open_log_files(directory, task_name, case_name, task_id, case_id):
    """Reserve one file exclusively without truncating previous evidence."""
    directory = Path(directory)
    for _ in range(10):
        names = log_filenames(task_name, case_name, task_id, case_id)
        try:
            output = (directory / names['test']).open('x', encoding='utf-8')
        except FileExistsError:
            continue
        return names, output
    raise FileExistsError('Unable to reserve a unique test log')


def test_log_text(execution, api):
    """Read old split evidence as one log, preserving API-only evidence."""
    execution, api = execution or '', api or ''
    if not api or api in execution:
        return execution
    if not execution:
        return api
    # Structured HTTP blocks already appear in the old execution log.
    separator = '\n' + '=' * 72 + '\n'
    if separator in api:
        blocks = [separator + block for block in api.split(separator)[1:]]
        missing = [block for block in blocks if block not in execution]
        if not missing:
            return execution
        api = ''.join(missing)
    if not execution:
        return api
    return execution + '\n=== Retained HTTP / protocol evidence ===\n' + api


def safe_uri(uri):
    parts = urlsplit(str(uri))
    query = parse_qsl(parts.query, keep_blank_values=True)
    if any(key.lower() in _SECRET_QUERY for key, _ in query):
        query_text = urlencode([(key, '[REDACTED]' if key.lower() in _SECRET_QUERY else value)
                                for key, value in query])
    else:
        query_text = parts.query
    return urlunsplit((parts.scheme, parts.netloc.rsplit('@', 1)[-1], parts.path, query_text, parts.fragment))


def safe_headers(headers):
    return {str(key): '[REDACTED]' if key.lower() in _SECRET_HEADERS else str(value)
            for key, value in (headers or {}).items()}


class CaseLog:
    """Public context['log'] API; writes directly, independently of stdout."""

    def __init__(self, result_file, emit):
        self.result_file, self.emit = result_file, emit
        self.records = []
        self.finished = False
        self.section_number = 0
        self.http_number = 0
        self.section_checks = 0

    def _close_section(self):
        if self.section_number and not self.section_checks:
            text = '  No check results recorded for this section.\n'
            self.result_file.write(text)
            self.result_file.flush()
            self.emit({'type': 'log', 'text': text[:-1]})

    def _write(self, kind, heading, lines, **data):
        stamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        text = '\n' + '=' * 72 + f'\n{heading}\nTime: {stamp}\n' + '-' * 72 + '\n' + '\n'.join(lines) + '\n'
        if kind == 'section':
            text = '\n' + '=' * 72 + f'\n{heading}\nTime: {stamp}\n'
        elif kind == 'check':
            text = '\n'.join('  ' + line for line in lines) + '\n'
        elif kind == 'http' and self.section_number:
            text = '\n' + '-' * 72 + f'\n{heading}\nTime: {stamp}\n' + '\n'.join(lines) + '\n' + '-' * 72 + '\n'
        record = dict(kind=kind, timestamp=stamp, **data)
        self.records.append(record)
        self.result_file.write(text)
        self.result_file.flush()
        # One event prevents duplicated HTTP blocks in the existing live viewer.
        self.emit({'type': 'log', 'text': text[:-1], 'log_record': record})

    def section(self, title):
        match = re.match(r'^(S[1-9][0-9]*) \| Step \| ', str(title))
        self.method_step_id = match[1] if match else None
        numbered = re.match(r'^Step ([1-9][0-9]*) \| (?:Command|Action) \| ', str(title))
        self.method_step_number = int(numbered[1]) if numbered else None
        self._close_section()
        self.section_number += 1
        self.section_checks = 0
        self._write('section', f'[{self.section_number}] {title}', [], title=str(title))

    def http(self, method, uri, status, headers, body, request_headers=None):
        self.http_number += 1
        uri, headers = safe_uri(uri), safe_headers(headers)
        request_headers = safe_headers(request_headers)
        raw_body = str(body)
        try:
            display_body = json.dumps(json.loads(raw_body), indent=2, ensure_ascii=False)
            body_label = 'Body (formatted JSON; original retained in structured evidence):'
        except (ValueError, TypeError):
            display_body, body_label = raw_body, 'Body (original text):'
        lines = [f'Request: {method} {uri}', 'Request headers:',
                 json.dumps(request_headers, indent=2, ensure_ascii=False),
                 f'Response status: {status}', 'Response headers:',
                 json.dumps(headers, indent=2, ensure_ascii=False), body_label, display_body]
        self._write('http', f'HTTP evidence #{self.http_number}', lines,
                    method=method, uri=uri, status=status, headers=headers,
                    request_headers=request_headers, body=raw_body,
                    **({"step_number": self.method_step_number} if getattr(self, "method_step_number", None) else {}),
                    **({"step_id": self.method_step_id} if getattr(self, "method_step_id", None) else {}))

    def check(self, label, passed, expected=None, actual=None, note=None):
        status = 'PASS' if passed else 'FAIL'
        self.section_checks += 1
        lines = [f'{status} | {label}']
        if expected is not None:
            lines.append('Expected: ' + json.dumps(expected, ensure_ascii=False))
        if actual is not None:
            lines.append('Actual: ' + json.dumps(actual, ensure_ascii=False))
        if note:
            lines.append('Note: ' + str(note))
        self._write('check', 'Validation result', lines, label=label, passed=bool(passed),
                    expected=expected, actual=actual, **({'note': str(note)} if note else {}))

    def step(self, step, criteria=None, result=None, note=None):
        """One report row: action, acceptance criteria, observed result (JSON values).

        This records evidence only. Use assertions / case_result for case outcome.
        Record each completed or failed action immediately; unperformed steps have
        no invented result. None / empty values render as an em dash in reports.
        """
        for value in (step, criteria, result, note):
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        self.section_checks += 1
        self._write('step', 'Report step', [
            'Step: '+('—' if step is None or step == '' else json.dumps(step, ensure_ascii=False)),
            'Criteria: '+('—' if criteria is None or criteria == '' else json.dumps(criteria, ensure_ascii=False)),
            'Result: '+('—' if result is None or result == '' else json.dumps(result, ensure_ascii=False)),
        ] + (['Note: '+str(note)] if note else []), step=step, criteria=criteria, result=result,
                    **({'note': str(note)} if note else {}))

    def method_item(self, item, result):
        """Write a numbered Command/Action, Checkpoint or Record; accept old IDs.

        kind=step remains the persistence/report adapter; criteria is unused.
        Record is informational and never receives a PASS/FAIL verdict.
        """
        if "step_number" in item:
            return self._numbered_method(item, result)
        # Retain compatibility with independently imported older Plan sources.
        item_id, item_type, step_id = item["id"], item["type"], item["step_id"]
        prefixes = {"Step": "S", "Checkpoint": "C", "Record": "R"}
        prefix = prefixes.get(item_type)
        match = re.fullmatch(r"([SCR])([1-9][0-9]*)([a-z]?)", item_id)
        if not match or match[1] != prefix or step_id != "S" + match[2]:
            raise ValueError("Invalid method item ID or Step association")
        if item_type == "Step" and match[3]:
            raise ValueError("Step IDs cannot have suffixes")
        result = validate_method("Action" if item_type == "Step" else item_type, result)
        if any(result.get(key) != item[key] for key in ("id", "type", "step_id")):
            raise ValueError("Method result association does not match its definition")
        json.dumps([item, result], ensure_ascii=False, allow_nan=False)
        self.section_checks += 1
        description = item["step"].removeprefix(item_id + " | " + item_type + " | ")
        lines = [description, "Source Step: " + step_id, "Status: " + result["status"]]
        if "expected" in result:
            lines.append("Expected: " + json.dumps(result["expected"], ensure_ascii=False))
        if "actual" in result:
            lines.append("Actual: " + json.dumps(result["actual"], ensure_ascii=False))
        if result.get("reason"):
            lines.append("Reason: " + result["reason"])
        if result.get("note"):
            lines.append("Note: " + result["note"])
        self._write("step", item_id + " | " + item_type, lines,
                    step=item["step"], criteria=None, result=result,
                    method_id=item_id, method_type=item_type, step_id=step_id)

    def _numbered_method(self, item, result):
        number, kind = item.get('step_number'), item.get('type')
        kinds = ('Command', 'Action', 'Checkpoint', 'Record')
        if type(number) is not int or number < 1 or kind not in kinds:
            raise ValueError('Invalid Step number or Type')
        result = validate_method(kind, result)
        if any(result.get(key) != item[key] for key in ('type', 'step_number')):
            raise ValueError('Method result association does not match its definition')
        index = result.get('method_index')
        if type(index) is not int or index < 0:
            raise ValueError('Invalid method position')
        json.dumps([item, result], ensure_ascii=False, allow_nan=False)
        self.section_checks += 1
        lines = ['Description: ' + item['step']]
        for key in ('expected', 'actual'):
            if key in result and not (key == 'actual' and result['status'] in ('Skip',) and result[key] is None):
                lines.append(key.capitalize() + ': ' + json.dumps(result[key], ensure_ascii=False))
        if result.get('reason'):
            lines.append('Reason: ' + result['reason'])
        if result.get('note'):
            lines.append('Note: ' + result['note'])
        lines.append('Judgement: ' + result['status'])
        self._write('step', f'Step {number} | {kind}', lines,
                    step=item['step'], criteria=None, result=result,
                    method_type=kind, step_number=number, method_index=index)

    def finish(self, status, reason, note=None):
        if self.finished:
            return
        validate_case_cp(status, {'log_records': self.records}, note)
        self._close_section()
        self.finished = True
        self._write('finish', 'Final result', [f'Result: {status}', f'Reason: {reason}'] +
                    ([f'Note: {note}'] if note else []), status=status, reason=reason,
                    **({'note': str(note)} if note else {}))


class PrintLogWriter:
    """Buffer print fragments while preserving indentation and blank lines."""

    def __init__(self, result_file, emit):
        self.result_file, self.emit = result_file, emit
        self.pending = ''

    def write(self, text):
        self.pending += text
        while '\n' in self.pending:
            line, self.pending = self.pending.split('\n', 1)
            self._line(line)
        return len(text)

    def _line(self, line):
        if self.result_file.closed:
            return
        stamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        self.result_file.write(f'{stamp} - INFO - {line}\n' if line else '\n')
        self.result_file.flush()
        self.emit({'type': 'log', 'text': line or ' '})

    def flush(self):
        if self.pending:
            line, self.pending = self.pending, ''
            self._line(line)
        if not self.result_file.closed:
            self.result_file.flush()


def result_note(result):
    """Return explicit execution notes, preserving order and legacy compatibility."""
    if not isinstance(result, dict):
        return ''
    if isinstance(result.get('note'), str):
        return result['note'].strip()
    records = result.get('log_records')
    if not isinstance(records, list):
        return ''
    final = next((r for r in reversed(records) if isinstance(r, dict) and r.get('kind') == 'finish'), {})
    if isinstance(final.get('note'), str):
        return final['note'].strip()
    notes = []
    for record in records:
        note = record.get('note') if isinstance(record, dict) else None
        if isinstance(note, str) and note.strip() and note.strip() not in notes:
            notes.append(note.strip())
    return '\n'.join(notes)
