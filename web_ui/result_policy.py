"""Current method judgement contract; historical display normalization is read-only."""


def method_status(status):
    return {'CP': 'C-PASS', 'NOT_RUN': 'Skip', 'NOT_EVALUATED': 'Skip', 'NOT_RECORDED': 'Skip',
            'RECORDED': 'COMPLETED'}.get(status, status)


def validate_method(kind, result):
    status = method_status(result.get('status'))
    allowed = {'Command': {'COMPLETED', 'FAILED', 'ERROR', 'Skip'},
               'Action': {'COMPLETED', 'FAILED', 'ERROR', 'Skip'},
               'Checkpoint': {'PASS', 'FAIL', 'C-PASS', 'Skip'},
               'Record': {'COMPLETED', 'ERROR', 'Skip'}}
    if status not in allowed.get(kind, set()):
        raise ValueError('Invalid status for method item type')
    note = result.get('note')
    if status == 'C-PASS' and (not isinstance(note, str) or not note.strip()):
        raise ValueError('C-PASS requires a Note')
    if note and status != 'C-PASS':
        raise ValueError('Note is reserved for C-PASS')
    if status == 'Skip' and not str(result.get('reason') or '').strip():
        raise ValueError('Skip requires a Reason')
    return dict(result, status=status)


def validate_case_cp(status, result, note):
    if method_status(status) != 'C-PASS':
        return
    if not isinstance(note, str) or not note.strip():
        raise ValueError('C-PASS requires a Note')
    if result.get('errors'):
        raise ValueError('C-PASS cannot override execution errors')
    for record in result.get('log_records', []):
        if not isinstance(record, dict):
            continue
        if record.get('kind') == 'finish' and str(record.get('status', '')).upper() in ('FAIL', 'FAILED', 'ERROR'):
            raise ValueError('C-PASS cannot override a failed execution')
        detail = record.get('result')
        if record.get('kind') == 'step' and isinstance(detail, dict):
            if detail.get('status') in ('FAIL', 'FAILED', 'ERROR'):
                raise ValueError('C-PASS cannot override a failed method item')
            if method_status(detail.get('status')) == 'C-PASS':
                validate_method(record.get('method_type') or detail.get('type'), detail)
        if record.get('kind') == 'check' and record.get('passed') is False:
            raise ValueError('C-PASS cannot override a failed checkpoint')
