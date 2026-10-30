"""Worksheet-1 report fields from declared definitions and explicit execution evidence."""
import json

MISSING = '—'


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


def firmware(setup):
    package = setup.get('fw_package') or []
    if not isinstance(package, list):
        return MISSING
    return '\n'.join(display(item.get('component'))+': '+display(item.get('version'))
                     for item in package if isinstance(item, dict)) or MISSING
