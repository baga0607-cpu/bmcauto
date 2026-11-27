"""Per-execution readable logs. Sections describe evidence, never execution steps."""
from datetime import datetime, timezone
from taipei_time import TAIPEI, format_timestamp
from result_policy import declared_method_items, method_status, validate_method, validate_case_cp
import json
import re
from pathlib import Path
from uuid import uuid4
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_UNSET = object()
_SECRET_HEADERS = {'authorization', 'proxy-authorization', 'cookie', 'set-cookie', 'x-auth-token'}
_SECRET_QUERY = {'password', 'passwd', 'token', 'access_token', 'api_key'}


def log_filenames(task_name, case_name, task_id, case_id):
    """A fresh local-time/offset and run identity for each test execution."""
    def label(value, limit):
        value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(value)).strip(' .')
        return value.encode('utf-16-le')[:limit * 2].decode('utf-16-le', errors='ignore').rstrip(' .') or 'unnamed'
    match = re.match(r'^([A-Za-z]+-\d+(?:-\d+)+)\b', str(case_name))
    case_label = match.group(1) if match else case_id
    stamp = datetime.now(TAIPEI).strftime('%Y%m%d_%H%M%S_%f%z')
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


def http_lines(method, uri, status, request_headers, headers, raw_body):
    try:
        display_body = json.dumps(json.loads(raw_body), indent=2, ensure_ascii=False)
        body_label = 'Body (formatted JSON; original retained in structured evidence):'
    except (ValueError, TypeError):
        display_body, body_label = raw_body, 'Body (original text):'
    return [f'Request: {method} {uri}', 'Request headers:',
             json.dumps(request_headers, indent=2, ensure_ascii=False),
             f'Response status: {status}', 'Response headers:',
             json.dumps(headers, indent=2, ensure_ascii=False), body_label, display_body]


def checkpoint_letter(position):
    suffix = ''
    while position:
        position, digit = divmod(position - 1, 26)
        suffix = chr(65 + digit) + suffix
    return suffix


class CaseLog:
    """Public context['log'] API; writes directly, independently of stdout."""

    def __init__(self, result_file, emit):
        self.result_file, self.emit = result_file, emit
        self.records = []
        self.checkpoint_letters = {}
        self.named_checkpoints = {}
        self.pending_checkpoints = {}
        self.operations = {}
        self.managed_step = None
        self.reported_operation = None
        self.finished = False
        self.section_number = 0
        self.http_number = 0
        self.section_checks = 0

    def declare_methods(self, methods):
        for index, method in declared_method_items(methods):
            if isinstance(method, dict) and method.get('type') in ('Command', 'Action'):
                self.operations[method['step_number']] = (method, index)
            if isinstance(method, dict) and method.get('type') == 'Checkpoint':
                self._checkpoint_letter(method.get('step_number'), index)
                if 'checkpoint_id' in method:
                    self.named_checkpoints[index] = method

    def begin_step(self, number):
        """Open a platform-owned operation; checkpoints can arrive immediately."""
        if self.managed_step is not None or number not in self.operations:
            raise ValueError('Invalid managed step boundary')
        item, index = self.operations[number]
        self.managed_step = (item, index)
        self.section(f"Step {number} | {item['type']} | {item['step']}")

    def operation_result(self, *, actual=_UNSET, failure=None):
        """Acknowledge the operation fact now; render its Outcome at the step boundary."""
        if not self.managed_step or self.reported_operation is not None:
            raise ValueError('An operation result requires an active step without a result')
        if (actual is _UNSET) == (failure is None):
            raise ValueError('Supply either Actual or a failure reason')
        if failure is not None and (not isinstance(failure, str) or not failure.strip()):
            raise ValueError('Operation failure requires a reason')
        detail = {'status': 'FAILED', 'reason': failure} if failure is not None else {
            'status': 'COMPLETED', 'actual': actual}
        self.reported_operation = json.loads(json.dumps(detail, allow_nan=False))
        item, index = self.managed_step
        record = dict(kind='operation_observation', step_number=item['step_number'],
                      method_index=index, detail=self.reported_operation)
        self.records.append(record)
        self.emit({'type': 'operation_observation', 'log_record': record})

    def end_step(self, *, error=None, stopped=False, failure=None):
        if self.managed_step is None:
            raise ValueError('No active managed step')
        item, index = self.managed_step
        detail = self.reported_operation
        if detail is None:
            if stopped or error or failure:
                detail = {'status': 'Stopped' if stopped else 'ERROR' if error else 'FAILED',
                          'reason': error or failure}
            else:
                count = sum(r['kind'] == 'http' and r.get('step_number') == item['step_number']
                            for r in self.records)
                actual = {'http_responses': count} if item['type'] == 'Command' or count else 'Operation completed'
                detail = {'status': 'COMPLETED', 'actual': actual}
        result = dict(method_index=index, step_number=item['step_number'], type=item['type'], **detail)
        self.method_item(item, result)
        self.reported_operation = None
        self.managed_step = None
        return result

    def recover_open_step(self, reason, *, stopped=False):
        """Finish the interrupted worker's last operation from acknowledged events."""
        for pos in range(len(self.records) - 1, -1, -1):
            record = self.records[pos]
            if record['kind'] in ('finish', 'section'):
                break
        else:
            return
        item = record.get('operation')
        if not item:
            return
        tail = self.records[pos + 1:]
        if any(r.get('method_index') == record['method_index'] and r['kind'] == 'step'
               for r in tail):
            return  # Outcome and checkpoint summaries were flushed before acknowledgement.
        number = item['step_number']
        self.managed_step = (item, record['method_index'])
        self.declare_methods([item])
        for r in tail:
            if r['kind'] == 'operation_observation' and r.get('method_index') == record['method_index']:
                self.reported_operation = r['detail']
            if r.get('method_type') == 'Checkpoint' and r.get('step_number') == number:
                key = r['checkpoint_id']
                heading = f"Step {number} | Checkpoint {self._checkpoint_letter(number, key)} | {r['step']}"
                self._collect_observation(heading, r, (number, key))
        # If killed during final rendering, replace only the unfinished projection.
        self.result_file.seek(0)
        text = self.result_file.read()
        marker = '\n' + '=' * 72 + f'\nStep {number} | Outcome\n'
        start = text.rfind(marker)
        if start >= 0 and start > text.rfind(f'\nStep {number} | Action | '):
            self.result_file.seek(0)
            self.result_file.read(start)
            self.result_file.truncate(self.result_file.tell())
        self.result_file.seek(0, 2)
        self.end_step(error=reason, stopped=stopped)

    def _checkpoint_letter(self, number, index):
        indices = self.checkpoint_letters.setdefault(number, {})
        return indices.setdefault(index, checkpoint_letter(len(indices) + 1))

    def _flush_checkpoints(self):
        for number, identities in self.checkpoint_letters.items():
            for identity in identities:
                group = self.pending_checkpoints.pop((number, identity), None)
                if group:
                    self._write_checkpoint_group(*group)

    def _collect_observation(self, heading, record, key):
        _, observations = self.pending_checkpoints.setdefault(key, (heading, {}))
        result = record['result']
        status = result['status']
        if status not in observations:
            stamp = format_timestamp(record['timestamp'])
            body = '\n'.join(self._result_lines(result))
            text = '\n' + '=' * 72 + f'\n{heading}\nTime: {stamp}\n' + '-' * 72 + '\n' + body + '\n'
            observations[status] = [0, text, f'Time: {stamp}\n' + body]
        observations[status][0] += 1

    def _write_checkpoint_group(self, heading, observations):
        total = sum(count for count, _, _ in observations.values())
        if total == 1:
            text = next(iter(observations.values()))[1]
        else:
            lines = [heading, f'Total observations: {total}']
            lines.extend(f'{status}: {count}' for status, (count, _, _) in observations.items())
            for status, (_, _, example) in observations.items():
                lines.extend(('', f'First {status} observation', example))
            text = '\n' + '=' * 72 + '\n' + '\n'.join(lines) + '\n'
        self.result_file.write(text)
        self.result_file.flush()
        self.emit({'type': 'log', 'text': text.rstrip('\n')})

    def _close_section(self):
        self._flush_checkpoints()
        if self.section_number and not self.section_checks:
            text = '  No check results recorded for this section.\n'
            self.result_file.write(text)
            self.result_file.flush()
            self.emit({'type': 'log', 'text': text[:-1]})

    def _write(self, kind, heading, lines, **data):
        instant = datetime.now(timezone.utc)
        stamp = format_timestamp(instant)
        text = '\n' + '=' * 72 + f'\n{heading}\nTime: {stamp}\n' + '-' * 72 + '\n' + '\n'.join(lines) + '\n'
        if kind == 'section':
            text = '\n' + '=' * 72 + f'\n{heading}\nTime: {stamp}\n'
        elif kind == 'step' and heading.endswith(' | Outcome'):
            text = '\n' + '=' * 72 + f'\n{heading}\n' + '\n'.join(lines) + '\n'
        elif kind == 'check':
            text = '\n'.join('  ' + line for line in lines) + '\n'
        elif kind == 'http' and self.section_number:
            text = '\n' + '-' * 72 + f'\n{heading}\nTime: {stamp}\n' + '\n'.join(lines) + '\n' + '-' * 72 + '\n'
        record = dict(kind=kind, timestamp=instant.isoformat(timespec='milliseconds'), **data)
        self.records.append(record)
        if kind == 'step' and data.get('method_type') == 'Checkpoint' and ('checkpoint_id' in data or 'method_index' in data):
            key = (data['step_number'], data.get('checkpoint_id', data.get('method_index')))
            self._collect_observation(heading, record, key)
            self.emit({'type': 'checkpoint_observation', 'log_record': record})
            return
        managed_outcome = kind == 'step' and self.managed_step and heading.endswith(' | Outcome')
        if kind == 'step' and not managed_outcome:
            self._flush_checkpoints()
        self.result_file.write(text)
        self.result_file.flush()
        if managed_outcome:
            self.emit({'type': 'log', 'text': text[:-1]})
            self._flush_checkpoints()
            self.emit({'type': 'operation_result', 'log_record': record})
            return
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
        heading = str(title).replace(' | Command | ', ' | Action | ', 1) if numbered else str(title)
        metadata = {}
        if self.managed_step:
            item, index = self.managed_step
            metadata = {'operation': item, 'method_index': index}
        self._write('section', heading, [], title=str(title), **metadata)

    def http(self, method, uri, status, headers, body, request_headers=None, *, link_values=None):
        self.http_number += 1
        uri, headers = safe_uri(uri), safe_headers(headers)
        request_headers = safe_headers(request_headers)
        if link_values is not None:
            link_key = next((k for k in headers if k.lower() == "link"), "Link")
            headers[link_key] = list(link_values)
        raw_body = str(body)
        lines = http_lines(method, uri, status, request_headers, headers, raw_body)
        self._write('http', f'HTTP evidence #{self.http_number}', lines,
                    evidence_id=self.http_number, method=method, uri=uri, status=status, headers=headers,
                    request_headers=request_headers, body=raw_body,
                    **({"step_number": self.method_step_number} if getattr(self, "method_step_number", None) else {}),
                    **({"step_id": self.method_step_id} if getattr(self, "method_step_id", None) else {}))

        return self.http_number

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
        checkpoint_id = result.get('checkpoint_id')
        if checkpoint_id is not None or 'checkpoint_id' in item:
            declared = self.named_checkpoints.get(checkpoint_id)
            if declared is None or declared != item or kind != 'Checkpoint':
                raise ValueError('Checkpoint does not match its declaration')
            identity = {'checkpoint_id': checkpoint_id}
        elif type(index) is not int or index < 0:
            raise ValueError('Invalid method position')
        else:
            identity = {'method_index': index}
        json.dumps([item, result], ensure_ascii=False, allow_nan=False)
        self.section_checks += 1
        label = kind
        if kind in ('Command', 'Action'):
            label = 'Outcome'
        elif kind == 'Checkpoint':
            label += ' ' + self._checkpoint_letter(number, checkpoint_id or index)
        heading = f'Step {number} | {label}'
        if label != 'Outcome':
            heading += ' | ' + item['step']
        self._write('step', heading, self._result_lines(result),
                    step=item['step'], criteria=None, result=result,
                    method_type=kind, step_number=number, **identity)

    @staticmethod
    def _result_lines(result):
        lines = []
        for key in ('expected', 'actual'):
            if key in result and not (key == 'actual' and result['status'] in ('Skip',) and result[key] is None):
                lines.append(key.capitalize() + ': ' + json.dumps(result[key], ensure_ascii=False))
        if result.get('reason'):
            lines.append('Reason: ' + result['reason'])
        if result.get('note'):
            lines.append('Note: ' + result['note'])
        lines.append('Judgement: ' + result['status'])
        return lines

    def finish(self, status, reason, note=None):
        status = method_status(status)
        if self.finished:
            return
        validate_case_cp(status, {'log_records': self.records}, note)
        if self.managed_step:
            self.end_step(error=reason)
        self._close_section()
        self.finished = True
        self._write('finish', 'Final result', [f'Result: {status}', f'Reason: {reason}'] +
                    ([f'Note: {note}'] if note else []), status=status, reason=reason,
                    **({'note': str(note)} if note else {}))


class ReportedCase:
    """Aggregate explicitly reported method results for an opted-in single-file Case."""

    def __init__(self, context, definition, failure_type=AssertionError):
        self.context = context
        self.failure_type = failure_type
        methods = definition['test_method']
        self.items = dict(declared_method_items(methods))
        logger = context.get('log')
        if not isinstance(logger, CaseLog) or not callable(logger.method_item):
            import sys
            # Direct callers can still consume the readable log and legacy method rows.
            def forward(event):
                record = event.get('log_record', {})
                if record.get('kind') == 'step' and callable(getattr(logger, 'method_item', None)):
                    result = record['result']
                    key = result.get('checkpoint_id', result.get('method_index'))
                    logger.method_item(self.items[key], result)
                elif record.get('kind') == 'step' and callable(getattr(logger, 'step', None)):
                    logger.step(record['step'], None, record['result'])
                elif record.get('kind') == 'finish' and callable(getattr(logger, 'finish', None)):
                    logger.finish(record['status'], record['reason'], **({'note': record['note']} if record.get('note') else {}))
            context['log'] = CaseLog(sys.stdout, forward)
        self.log = context['log']
        self.log.declare_methods(methods)

    def begin_step(self, number):
        if self.log.managed_step:
            self.log.end_step()
        self.log.begin_step(number)

    def operation_result(self, *, actual=_UNSET, failure=None):
        self.log.operation_result(actual=actual, failure=failure)

    def checkpoint(self, key, judgement, **detail):
        item = self.items[key]
        if not self.log.managed_step or item['type'] != 'Checkpoint' or self.log.method_step_number != item['step_number']:
            raise ValueError('Checkpoint does not belong to the current step')
        if judgement in ('PASS', 'FAIL', 'C-PASS') and 'actual' not in detail:
            raise ValueError('Evaluated checkpoint requires Actual')
        self._report(key, judgement, detail)

    def record(self, actual):
        """Complete the current operation and record its declared informational value."""
        if not self.log.managed_step:
            raise ValueError('Record requires an active step')
        number = self.log.method_step_number
        keys = [key for key, item in self.items.items()
                if item['step_number'] == number and item['type'] == 'Record']
        if len(keys) != 1:
            raise ValueError('Expected one declared Record for this step')
        self.log.end_step()
        self._report(keys[0], 'COMPLETED', {'actual': actual})

    def _failure_summary(self, checks):
        reasons = {}
        for result in checks:
            if result['status'] == 'FAIL':
                key = result.get('checkpoint_id', result.get('method_index'))
                reason = result.get('reason') or self.items[key]['step']
                reasons.setdefault(key, {})[reason] = None
        if not reasons:
            return ''
        lines = ['1 checkpoint failed.' if len(reasons) == 1 else f'{len(reasons)} checkpoints failed.']
        for key, item in self.items.items():
            if key in reasons:
                number = item['step_number']
                letter = self.log.checkpoint_letters[number][key]
                lines.append(f"Step {number} | Checkpoint {letter} | " + ' '.join(reasons[key]))
        return '\n'.join(lines)

    def _report(self, key, status, detail):
        item = self.items[key]
        identity = {'checkpoint_id': key} if 'checkpoint_id' in item else {'method_index': key}
        self.log.method_item(item, dict(identity, step_number=item['step_number'], type=item['type'],
                                        status=status, **detail))

    def finish(self, observations, *, summary='', blocked='', error='', note='', operation_failure=''):
        if self.log.managed_step:
            self.log.end_step(error=error, failure=operation_failure)
        results = [r['result'] for r in self.log.records if r['kind'] == 'step' and 'method_type' in r]
        seen = {r.get('checkpoint_id', r.get('method_index')) for r in results}
        missing_reason = error or blocked or 'Execution ended before this item was evaluated'
        for key in self.items:
            if key not in seen:
                self._report(key, 'Not executed', {'reason': missing_reason})
        results = [r['result'] for r in self.log.records if r['kind'] == 'step' and 'method_type' in r]
        states = {r['status'] for r in results}
        checks = [r for r in results if r['type'] == 'Checkpoint']
        if error:
            status, reason = 'Error', error
        elif states.intersection(('FAIL', 'FAILED', 'ERROR')):
            status, reason = 'Fail', summary or self._failure_summary(checks) or blocked or 'A required method item failed'
        elif blocked or 'Not executed' in states or not any(r['status'] in ('PASS', 'C-PASS') for r in checks):
            status, reason = 'Block', blocked or next((r['reason'] for r in results if r['status'] == 'Not executed'),
                                                      'No required validation completed')
        elif 'C-PASS' in states:
            status, reason = 'C-PASS', summary or 'Conditional acceptance criteria met'
        else:
            status, reason = 'Pass', summary or 'All applicable checkpoints passed'
        if status == 'C-PASS' and not note:
            note = '\n'.join(dict.fromkeys(r['note'] for r in checks if r['status'] == 'C-PASS'))
        self.log.finish(status, reason, note=note or None)
        self.context['case_result'] = dict(status=status, reason=reason, note=note,
                                           observations=observations, method_results=results)
        self.context['_tc_status'] = {'Pass': 'PASS', 'Block': 'BLOCK', 'C-PASS': 'C-PASS'}.get(status, 'FAIL')
        if status == 'Error':
            raise RuntimeError(reason)
        if status == 'Fail':
            raise self.failure_type(reason)
        return self.context['case_result']


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
        stamp = format_timestamp(datetime.now(TAIPEI))
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
