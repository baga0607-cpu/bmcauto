"""Per-execution readable logs. Sections describe evidence, never execution steps."""
from datetime import datetime, timezone
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
                    request_headers=request_headers, body=raw_body)

    def check(self, label, passed, expected=None, actual=None):
        status = 'PASS' if passed else 'FAIL'
        self.section_checks += 1
        lines = [f'{status} | {label}']
        if expected is not None:
            lines.append('Expected: ' + json.dumps(expected, ensure_ascii=False))
        if actual is not None:
            lines.append('Actual: ' + json.dumps(actual, ensure_ascii=False))
        self._write('check', 'Validation result', lines, label=label, passed=bool(passed),
                    expected=expected, actual=actual)

    def finish(self, status, reason):
        if self.finished:
            return
        self._close_section()
        self.finished = True
        self._write('finish', 'Final result', [f'Result: {status}', f'Reason: {reason}'],
                    status=status, reason=reason)


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
