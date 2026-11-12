"""Report fields from declared definitions and explicit execution evidence."""
import json
from datetime import datetime, timezone, timedelta

MISSING = '—'


def execution_date(value):
    if not value:
        return MISSING
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return display(value)
    if parsed.tzinfo is None:
        return parsed.strftime('%Y/%m/%d %H:%M:%S') + ' (timezone not recorded)'
    return parsed.astimezone(timezone(timedelta(hours=8))).strftime('%Y/%m/%d %H:%M:%S') + ' (UTC+08:00)'


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


def method_table_rows(result, metadata):
    """ID/type/description/result from explicit evidence, without inferred verdicts.

    Saved definitions may fill missing observations by ID. Current source is only
    a fallback when no historical definition or method evidence exists.
    """
    def observation(value):
        if not isinstance(value, dict):
            text = display(value)
        else:
            parts = []
            if value.get('status'):
                parts.append(str(value['status']))
            for key in ('expected', 'actual', 'reason'):
                if key in value:
                    raw = value[key]
                    rendered = 'null' if raw is None else display(raw)
                    parts.append(key.capitalize() + ': ' + rendered)
            text = '\n'.join(parts) if parts else display(value)
        if len(text) > 1200:
            text = text[:1100].rstrip() + '\n[Excerpt; see full value in saved execution evidence / Test log.]'
        return text

    def typed_row(item, value=None):
        identity = item.get('method_id') or item.get('id') or value.get('id')
        kind = item.get('method_type') or item.get('type') or value.get('type')
        label = display(item.get('step'))
        prefix = f'{identity} | {kind} | '
        if label.startswith(prefix):
            label = label[len(prefix):]
        parent = item.get('step_id') or value.get('step_id')
        if parent and kind != 'Step':
            label += '\nSource: ' + str(parent)
        return (display(identity), display(kind), label,
                observation(value) if value else 'No recorded result')

    records = result.get('log_records')
    records = records if isinstance(records, list) else []
    explicit = [r for r in records if isinstance(r, dict) and r.get('kind') == 'step']
    rows, observed = [], set()
    for record in explicit:
        value = record.get('result')
        detail = value if isinstance(value, dict) else {}
        if record.get('method_id') or detail.get('id'):
            rows.append(typed_row(record, detail))
            observed.add(record.get('method_id') or detail.get('id'))
        else:
            label = display(record.get('step'))
            if record.get('criteria') is not None:
                label += '\nCriteria: ' + display(record['criteria'])
            rows.append((MISSING, 'Legacy', label, observation(value)))
    definition = result.get('report_definition')
    if rows:
        # Only the captured definition is safe to join to historical evidence.
        methods = definition.get('test_method', []) if isinstance(definition, dict) else []
        for item in methods if isinstance(methods, list) else []:
            if isinstance(item, dict) and item.get('id') and item['id'] not in observed:
                rows.append(typed_row(item, {}))
        return rows
    if any(isinstance(r, dict) and r.get('kind') in ('section', 'check') for r in records):
        return [(MISSING, 'Legacy', step + ('\nCriteria: '+criteria if criteria != MISSING else ''), observation(value))
                for step, criteria, value in method_rows(result, metadata)]
    definition = definition if isinstance(definition, dict) else metadata
    methods = definition.get('test_method', [])
    for item in methods if isinstance(methods, list) else []:
        if not isinstance(item, dict):
            continue
        if item.get('id'):
            rows.append(typed_row(item, {}))
        else:
            step = item.get('step', next((v for k, v in item.items() if k.startswith('step_')), None))
            label = display(step)
            if item.get('criteria') is not None:
                label += '\nCriteria: ' + display(item['criteria'])
            rows.append((MISSING, 'Legacy', label, 'No recorded result'))
    return rows or [(MISSING, MISSING, 'No test steps recorded', 'No recorded result')]


def firmware(setup):
    package = setup.get('fw_package') or []
    if not isinstance(package, list):
        return MISSING
    return '\n'.join(display(item.get('component'))+': '+display(item.get('version'))
                     for item in package if isinstance(item, dict)) or MISSING
