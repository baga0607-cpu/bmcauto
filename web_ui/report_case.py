"""Report fields from declared definitions and explicit execution evidence."""
import re

from result_policy import declared_method_items, method_status
import json
from taipei_time import format_timestamp as execution_date

MISSING = '—'


def result_summary(result, manual=None, limit=600):
    """Use recorded final reasons, never infer a verdict from detailed step data."""
    reason = None
    if isinstance(manual, dict):
        reason = manual.get('reason')
        prefix = 'Manual result: '
    else:
        prefix = ''
        records = result.get('log_records')
        if isinstance(records, list):
            final = next((r for r in reversed(records) if isinstance(r, dict) and r.get('kind') == 'finish'), {})
            reason = final.get('reason')
        if not isinstance(reason, str) or not reason.strip():
            reason = result.get('reason')
    if not isinstance(reason, str) or not reason.strip():
        return 'No recorded summary. See the Test log for available evidence.'
    text = prefix + reason.strip()
    if len(text) > limit:
        suffix = ' ... [Excerpt; see full reason in the Test log or manual result note.]'
        return text[:limit-len(suffix)].rstrip() + suffix
    return text


def display(value):
    if value is None or value == '':
        return MISSING
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def method_rows(result, metadata):
    records = result.get('log_records') or []
    if not isinstance(records, list):
        records = []
    explicit = [r for r in records if isinstance(r, dict) and r.get('kind') == 'step']
    if explicit:
        return [(display(r.get('step')), display(r.get('criteria')), display(r.get('result'))) for r in explicit]
    # Old section/check evidence has explicit labels, expected and actual values.
    # Use its own section titles; never align it to declared steps by guessed indexes.
    rows, section, pending = [], None, False
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get('kind') == 'section':
            if pending:
                rows.append((display(section), MISSING, MISSING))
            section, pending = record.get('title'), True
        elif record.get('kind') == 'check':
            criterion = display(record.get('label'))
            if record.get('expected') is not None:
                criterion += '\nExpected: '+display(record['expected'])
            result_text = 'PASS' if record.get('passed') is True else 'FAIL' if record.get('passed') is False else MISSING
            if record.get('actual') is not None:
                result_text += '\nActual: '+display(record['actual'])
            rows.append((display(section), criterion, result_text))
            pending = False
    if pending:
        rows.append((display(section), MISSING, MISSING))
    if rows:
        return rows
    definition = result.get('report_definition')
    definition = definition if isinstance(definition, dict) else metadata
    methods = definition.get('test_method', [])
    for item in methods if isinstance(methods, list) else []:
        if isinstance(item, dict):
            step = item.get('step')
            if step is None:
                step = next((v for k,v in item.items() if k.startswith('step_')), None)
            rows.append((display(step), display(item.get('criteria')), MISSING))
    return rows or [(MISSING, MISSING, MISSING)]


def description(result, metadata):
    definition = result.get('report_definition')
    return display((definition if isinstance(definition, dict) else metadata).get('description'))


class MethodResult(str):
    """Displayed result text with the recorded Note boundary, not a text guess."""
    def __new__(cls, text, note_start=None):
        instance = super().__new__(cls, text)
        instance.note_start = note_start
        return instance


class MissingObservation(str):
    """Display fallback for a row without recorded evidence."""


def _method_table_rows(result, metadata, number_subitems):
    """Step / Type / Description / Result / Judgement; never infer a verdict.

    Numbered definitions join observations by captured method position. Historical
    S/C/R evidence is adapted for display only; saved records are never rewritten.
    """
    def bounded(text, note_start=None):
        if len(text) > 1200:
            full = MethodResult(text, note_start)
            prefix = text[:1100].rstrip()
            if note_start is not None and note_start >= len(prefix):
                note_start = None
            text = prefix + '\n[Excerpt; see full value in saved execution evidence / Test log.]'
            excerpt = MethodResult(text, note_start)
            if number_subitems:
                excerpt.full = full
            return excerpt
        return MethodResult(text, note_start)

    def observation(value, kind):
        if not isinstance(value, dict):
            return bounded(display(value)), MISSING
        if 'status' not in value:
            return bounded(display(value)), MISSING
        actual_span = None
        status, parts = method_status(value['status']), []
        if number_subitems and value['status'] in ('NOT_RUN', 'NOT_EVALUATED', 'NOT_RECORDED', 'BLOCKED', 'Block'):
            status = 'Not executed'
        note_start = None
        if kind == 'Record' and status == 'NOT_RECORDED':
            parts.append('Not recorded')
        for key in ('expected', 'actual', 'reason', 'note'):
            if key not in value:
                continue
            raw = value[key]
            if key == 'reason' and not str(raw or '').strip():
                continue
            if key == 'actual' and raw is None and status in ('Skip',):
                continue
            rendered = 'null' if raw is None else '""' if raw == '' else display(raw)
            if number_subitems and key in ('actual', 'expected'):
                rendered = json.dumps(raw, ensure_ascii=False)
            if key == 'actual':
                start = sum(len(part) + 1 for part in parts)
                actual_span = (start, start + len('Actual: ') + len(rendered))
            if key == 'note':
                note_start = len('\n'.join(parts)) + (1 if parts else 0)
            parts.append(key.capitalize() + ': ' + rendered)
        text = '\n'.join(parts) or ('Recorded' if kind == 'Record' and status == 'RECORDED' else MISSING)
        result_text = bounded(text, note_start)
        getattr(result_text, 'full', result_text).actual_span = actual_span
        return result_text, display(status)

    checkpoint_labels = {}
    checkpoint_counts = {}

    def step_label(number, kind, identity=None):
        if kind in ('Action', 'Command'):
            return display(number)
        if not number_subitems or number is None:
            return ''
        if kind == 'Record':
            return display(number)
        if kind != 'Checkpoint':
            return ''
        key = (str(number), identity)
        if identity is not None and key in checkpoint_labels:
            return checkpoint_labels[key]
        count = checkpoint_counts.get(str(number), 0) + 1
        checkpoint_counts[str(number)] = count
        suffix = ''
        while count:
            count, letter = divmod(count - 1, 26)
            suffix = chr(ord('a') + letter) + suffix
        label = str(number) + suffix
        if identity is not None:
            checkpoint_labels[key] = label
        return label

    def typed(item, value=None, definition_index=None):
        detail = value if isinstance(value, dict) else {}
        kind = item.get('method_type') or item.get('type') or detail.get('type')
        identity = detail.get('checkpoint_id') or item.get('checkpoint_id') or item.get('method_id') or item.get('id') or detail.get('id')
        label = display(item.get('step'))
        label = label.removeprefix(f'{identity} | {kind} | ')
        if kind == 'Checkpoint' and not number_subitems:
            # Compact descriptions only; preserve recorded observation formatting.
            label = re.sub(r'\r?\n(?:[ \t]*\r?\n)+', '\n', label)
        number = item.get('step_number', detail.get('step_number'))
        if number is None:
            parent = item.get('step_id') or detail.get('step_id')
            if isinstance(parent, str) and parent.startswith('S') and parent[1:].isdigit():
                number = int(parent[1:])
        # Old Step did not distinguish commands from other actions.
        kind = 'Action' if kind == 'Step' else kind
        content, judgement = observation(value, kind) if value is not None else (MissingObservation('No recorded result'), MISSING)
        index = detail.get('method_index', item.get('method_index', definition_index))
        return (step_label(number, kind, identity or index),
                display(kind), label, content, judgement)

    def detail_of(item):
        return item.get('result') if isinstance(item.get('result'), dict) else {}

    def matches_item(item, index, record):
        detail = detail_of(record)
        key = detail.get('checkpoint_id', record.get('checkpoint_id'))
        if key is not None or 'checkpoint_id' in item:
            return (key == item.get('checkpoint_id') and detail.get('step_number') == item.get('step_number')
                    and item.get('type') == 'Checkpoint')
        return (detail.get('method_index') == index
                or item.get('id') and (record.get('method_id') or detail.get('id')) == item['id'])

    def is_typed(item):
        detail = item.get('result') if isinstance(item.get('result'), dict) else {}
        kind = item.get('method_type') or item.get('type') or detail.get('type')
        return kind in ('Command', 'Action', 'Checkpoint', 'Record', 'Step')

    def legacy(item, number, value=None):
        label = item.get('step', next((v for k, v in item.items() if k.startswith('step_')), None))
        label = display(label)
        if item.get('criteria') is not None:
            label += '\nCriteria: ' + display(item['criteria'])
        content, judgement = observation(value, 'Action') if value is not None else (MissingObservation('No recorded result'), MISSING)
        return (str(number), 'Action', label, content, judgement)

    records = result.get('log_records')
    records = records if isinstance(records, list) else []
    explicit = [r for r in records if isinstance(r, dict) and r.get('kind') == 'step']
    definition = result.get('report_definition')
    methods = definition.get('test_method', []) if isinstance(definition, dict) else []
    methods = methods if isinstance(methods, list) else []
    rows = []
    if explicit:
        remaining = list(enumerate(explicit))
        # Only a saved definition may supply missing rows; never join current source.
        for index, item in declared_method_items(methods):
            if not isinstance(item, dict) or not is_typed(item):
                continue
            matches = [(position, r) for position, r in remaining
                       if matches_item(item, index, r)]
            if matches:
                for match in matches:
                    remaining.remove(match)
                    rows.append(typed({**item, **match[1]}, match[1].get('result'), index))
            else:
                rows.append(typed(item, definition_index=index))
        for number, (_, record) in enumerate(remaining, 1):
            rows.append(typed(record, record.get('result')) if is_typed(record)
                        else legacy(record, number, record.get('result')))
        for record in explicit:
            detail = record.get('result')
            if isinstance(detail, dict):
                for check in detail.get('checks', []):
                    if isinstance(check, dict):
                        value = dict(check, status='PASS' if check.get('passed') is True else 'FAIL' if check.get('passed') is False else MISSING)
                        content, judgement = observation(value, 'Checkpoint')
                        parent = record.get('step_number', detail.get('step_number'))
                        rows.append((step_label(parent, 'Checkpoint'), 'Checkpoint', display(check.get('label')), content, judgement))
        return rows
    if any(isinstance(r, dict) and r.get('kind') in ('section', 'check') for r in records):
        number = 0
        for record in records:
            if not isinstance(record, dict):
                continue
            if record.get('kind') == 'section':
                number += 1
                rows.append((str(number), 'Action', display(record.get('title')), MissingObservation(MISSING), MISSING))
            elif record.get('kind') == 'check':
                value = {k: record[k] for k in ('expected', 'actual', 'note') if k in record}
                value['status'] = 'PASS' if record.get('passed') is True else 'FAIL' if record.get('passed') is False else MISSING
                content, judgement = observation(value, 'Checkpoint')
                rows.append((step_label(number or None, 'Checkpoint'), 'Checkpoint', display(record.get('label')), content, judgement))
        return rows
    definition = definition if isinstance(definition, dict) else metadata
    methods = definition.get('test_method', [])
    for index, item in declared_method_items(methods if isinstance(methods, list) else []):
        if isinstance(item, dict):
            rows.append(typed(item) if is_typed(item) else legacy(item, index + 1))
    return rows or [('', MISSING, 'No test steps recorded', MissingObservation('No recorded result'), MISSING)]


def firmware(setup):
    package = setup.get('fw_package') or []
    if not isinstance(package, list):
        return MISSING
    return '\n'.join(display(item.get('component'))+': '+display(item.get('version'))
                     for item in package if isinstance(item, dict)) or MISSING


def method_table_rows(result, metadata, *, number_subitems=False):
    # Case-only notes remain in saved evidence; reports show step-associated notes.
    return _method_table_rows(result, metadata, number_subitems)
