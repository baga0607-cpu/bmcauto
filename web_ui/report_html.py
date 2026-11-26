"""Portable HTML report package with separate full log files and print layout."""
import io
import zipfile
import json
import os
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from types import SimpleNamespace

from case_log import checkpoint_letter, http_lines, test_log_text
from report_case import description, display, execution_date, firmware, result_summary, method_table_rows, MethodResult, MissingObservation
from report_presentation import note_text, specification_reference, result_parts, judgement_class


def method_row_html(method):
    step, kind, description_text, result, judgement = method
    return table_row(step, description_text, evidence_html(result, judgement), judgement, checkpoint=kind == "Checkpoint")


def evidence_html(result, judgement, *, fold_actual=True):
    if isinstance(result, MissingObservation):
        return ''
    full = getattr(result, 'full', result)
    span = getattr(full, 'actual_span', None)
    if fold_actual and span and span[1] - span[0] - len('Actual: ') > 240:
        before, note = result_parts(full)
        start, end = span
        content = (escape(before[:start]) + '<details><summary>Detail</summary>'
                   + escape(before[start:end]) + '</details>' + escape(before[end:]))
    else:
        before, note = result_parts(result)
        content = escape(before)
    if note:
        note_html = '<strong>Note: </strong>'+escape(note[6:]) if note.startswith('Note: ') else escape(note)
        content += '<span class="result-note">'+note_html+'</span>'
    verdict = '<span class="judgement-text">'+escape(judgement)+'</span>' if judgement else ''
    return verdict + content


def table_row(step, description_text, content, judgement='', *, checkpoint=False):
    row_class = 'method-' + judgement_class(judgement)
    if checkpoint:
        row_class += ' checkpoint-row'
    elif step.isdecimal() or step.endswith(' | Action'):
        row_class += ' main-step-row'
    return ('<tr class="'+row_class+'">'
            + ''.join('<td>'+escape(value)+'</td>' for value in (step, description_text))
            + '<td class="result-text">'+content+'</td></tr>')


def observations_html(observations):
    if len(observations) <= 1:
        return ''.join(evidence_html(text, status) for text, status in observations)
    groups = defaultdict(list)
    for text, status in observations:
        groups[status].append(getattr(text, 'full', text))
    parts = []
    for status, texts in groups.items():
        items = ''.join('<li>'+evidence_html(text, '', fold_actual=False)+'</li>' for text in texts)
        parts.append(f'<div data-judgement="{judgement_class(status)}">'
                     f'<span class="judgement-text">{escape(status)} {len(texts)}</span>'
                     f'<details><summary>Detail</summary><ol>{items}</ol></details></div>')
    return ''.join(parts)


def legacy_method_body(result, metadata):
    rows = method_table_rows(result, metadata, number_subitems=True)
    http = defaultdict(list)
    for index, record in enumerate((r for r in result.get('log_records') or []
                                    if isinstance(r, dict) and r.get('kind') == 'http'), 1):
        lines = http_lines(record.get('method'), record.get('uri'), record.get('status'),
                           record.get('request_headers'), record.get('headers'), record.get('body', ''))
        if record.get('timestamp'):
            lines.insert(0, 'Time: ' + record['timestamp'])
        evidence_id = escape(str(record.get('evidence_id', index)))
        http[str(record.get('step_number'))].append(
            f'<details><summary>HTTP evidence #{evidence_id}</summary><pre>'
            + escape('\n'.join(lines)) + '</pre></details>')
    checkpoints = defaultdict(list)
    for step, kind, _, text, status in rows:
        if kind == 'Checkpoint' and step and not isinstance(text, MissingObservation):
            checkpoints[step].append((text, status))
    parts = []
    seen = set()
    for step, kind, label, text, status in rows:
        if kind in ('Action', 'Command') and step.isdecimal():
            requests = http.pop(step, [])
            evidence = ''.join(requests)
            if len(requests) > 1:
                evidence = (f'<details><summary>Details · HTTP evidence ({len(requests):,})</summary>'
                            + evidence + '</details>')
            parts.append(table_row(f'Step {step} | Action', label, evidence))
            parts.append(table_row(f'Step {step} | Outcome', '', evidence_html(text, status), status))
        elif kind == 'Checkpoint' and step and step.rstrip('abcdefghijklmnopqrstuvwxyz').isdecimal():
            if step in seen:
                continue
            seen.add(step)
            number = step.rstrip('abcdefghijklmnopqrstuvwxyz')
            tag = f'Step {number} | Checkpoint {step[len(number):].upper()}'
            parts.append(table_row(tag, label, observations_html(checkpoints[step]),
                                   status if len(checkpoints[step]) == 1 else '', checkpoint=True))
        elif kind == 'Record' and step.isdecimal():
            parts.append(table_row(f'Step {step} | Record', label, evidence_html(text, status), status))
        else:
            parts.append(method_row_html((step, kind, label, text, status)))
    return ''.join(parts)


def event_evidence(event):
    status = event.get('judgement') or event.get('status') or ''
    if status in ('NOT_RUN', 'NOT_EVALUATED', 'NOT_RECORDED', 'BLOCKED', 'Block'):
        status = 'Not executed'
    parts = []
    note_start = None
    actual_span = None
    for key in ('expected', 'actual', 'reason', 'note'):
        if key in event:
            value = event[key]
            value = (value or '""') if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            if key == 'actual':
                start = sum(len(part) + 1 for part in parts)
                actual_span = (start, start + len('Actual: ') + len(value))
            if key == 'note':
                note_start = sum(len(part) + 1 for part in parts)
            parts.append(key.capitalize()+': '+value)
    text = MethodResult('\n'.join(parts), note_start)
    text.actual_span = actual_span
    return text, status


def snapshot_method_body(methods, events):
    steps = defaultdict(list)
    checkpoints = defaultdict(list)
    for event in events:
        if not isinstance(event, dict):
            continue
        number = event.get('step_number')
        if event.get('event') == 'checkpoint_result':
            checkpoints[number, event.get('checkpoint_id')].append(event_evidence(event))
        elif event.get('event') in ('step_observation', 'step_result'):
            steps[number].append(event_evidence(event))
    rows = []
    for method in methods:
        number = method['step_number']
        evidence = steps[number]
        # Show the recorded completion status before the step's observation values.
        step_content = ''.join('<div>'+evidence_html(text, status)+'</div>'
                               for text, status in sorted(evidence, key=lambda item: not item[1]))
        rows.append(table_row(f'Step {number} | Action', method['step'], ''))
        rows.append(table_row(f'Step {number} | Outcome', '', step_content))
        for index, (key, declaration) in enumerate(method.get('checkpoints', {}).items(), 1):
            tag = f'Step {number} | Checkpoint {checkpoint_letter(index)}'
            observations = checkpoints[number, key]
            status = observations[0][1] if len(observations) == 1 else ''
            rows.append(table_row(tag, declaration['expected'],
                                  observations_html(observations), status, checkpoint=True))
    return ''.join(rows)


def object_value(raw):
    try:
        value = json.loads(raw or '{}')
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def generate_html_report(db_path, reports, preview_case_id=None):
    sections, logs, totals = [], {}, Counter()
    preview = preview_case_id is not None
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri()+'?mode=ro', uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('BEGIN')
        for group_index, (area, report) in enumerate(reports):
            task = conn.execute('SELECT t.*,p.name AS plan_name,pr.name AS project_name FROM tasks t JOIN project_plans p ON p.id=t.plan_id JOIN projects pr ON pr.id=p.project_id WHERE t.id=?', (report['identity'],)).fetchone()
            if task is None:
                from plan_state import StateError
                raise StateError('Task not found.', 404)
            columns = ('m.testcase_id,m.status,m.result_json,m.manual_override_json,m.executed_at,'
                       "(length(coalesce(m.log_text,''))>0 OR length(coalesce(m.api_log_text,''))>0) AS has_log"
                       if preview else 'm.*')
            where = ' AND m.testcase_id=?' if preview else ''
            args = (task['id'], task['plan_id'], preview_case_id) if preview else (task['id'], task['plan_id'])
            rows = conn.execute('SELECT '+columns+',c.display_name,c.script_path,c.script_kind,c.folder_id FROM task_testcases m JOIN testcases c ON c.system_id=m.testcase_id WHERE m.task_id=? AND c.plan_id=?'+where+' ORDER BY m.position', args).fetchall()
            if preview and not rows:
                from plan_state import StateError
                raise StateError('Test Case is not in this Task.', 404)
            folders = {folder['id']: folder for folder in conn.execute('SELECT id,name,parent_id FROM plan_folders WHERE plan_id=?', (task['plan_id'],))}
            cards = []
            for index, row in enumerate(rows):
                key = f'case-{group_index}-{index}'
                result = object_value(row['result_json'])
                events = result.get('events', result.get('log_records', []))
                events = events if isinstance(events, list) else []
                if not isinstance(result.get('report_definition'), dict):
                    for event in events:
                        if isinstance(event, dict) and event.get('event') == 'case_started' and isinstance(event.get('definition'), dict):
                            result['report_definition'] = event['definition']
                            break
                manual = object_value(row['manual_override_json']) or None
                metadata = {}
                if not isinstance(result.get('report_definition'), dict) and row['script_kind'] == 'single':
                    try:
                        from single_case import metadata as read_metadata, script_file
                        root = os.environ.get('BMC_MAIN_PROGRAM_DIR', str(Path(__file__).parent.parent/'main_program'))
                        metadata = read_metadata(script_file(root, SimpleNamespace(script_path=row['script_path'])).read_text(encoding='utf-8'))
                    except (OSError, ValueError):
                        pass
                source = report['source_details'].get(row['testcase_id'], {}) if report['source_details'] is not None else {'name':task['name'], 'setup':object_value(task['task_metadata'])}
                setup = source.get('setup') or {}
                status = {'Passed':'PASS', 'CP':'C-PASS', 'C-PASS':'C-PASS', 'Failed':'FAIL', 'Block':'Block', 'Running':'Running'}.get(row['status'], 'NR')
                if area == 'report':
                    totals[status] += 1
                text = '' if preview else test_log_text(row['log_text'], row['api_log_text'])
                filename = str(row['display_name'] or row['testcase_id'])
                filename = ''.join('_' if c in '<>:"/\\|?*' or ord(c)<32 else c for c in filename)[:100].rstrip('. ')+'__test.log'
                actions = '<span class="muted">No Test log available</span>'
                if preview and row['has_log']:
                    actions = '<span class="muted">Full Test log available in the Log viewer.</span>'
                if text:
                    from urllib.parse import quote
                    attachment = f'logs/{group_index+1:02d}-{index+1:03d}_{filename}'
                    logs[attachment] = text.encode('utf-8')
                    href = escape(quote(attachment), quote=True)
                    actions = f'<a class="attachment-link" href="{href}" target="_blank" rel="noopener">Open Log attachment ↗</a><span class="muted">.log</span>'
                notes = []
                if preview and row['status'] == 'Running':
                    notes.append('Execution in progress. This preview shows currently saved results. Refresh after execution finishes.')
                if manual:
                    notes.append('Manual result: '+display('C-PASS' if manual.get('status') == 'CP' else manual.get('status'))+' · '+display(manual.get('reason')))
                fields = [('Task Name', source.get('name')), ('Tester', setup.get('owner')), ('Execution Time', execution_date(row['executed_at'])), ('FW Package', firmware(setup)), ('Configuration', None)]
                info = ''.join(f'<div><dt>{escape(label)}</dt><dd>{escape('' if label == 'Configuration' else display(value))}</dd></div>' for label,value in fields)
                folder_id, folder_names, visited = row['folder_id'], [], set()
                while folder_id in folders and folder_id not in visited:
                    visited.add(folder_id)
                    folder_names.append(folders[folder_id]['name'])
                    folder_id = folders[folder_id]['parent_id']
                reference = specification_reference(result, metadata, '/'.join(reversed(folder_names)))
                spec_field = '' if reference is None else f'<dt>Spec Ref.</dt><dd>{escape(reference)}</dd>'
                declared = result.get('report_definition', {}).get('test_method', []) if isinstance(result.get('report_definition'), dict) else []
                is_snapshot = isinstance(declared, list) and declared and all(
                    isinstance(item, dict) and 'step_number' in item and isinstance(item.get('step'), str)
                    and 'type' not in item and 'method_type' not in item for item in declared)
                # Imported v1 cases share the snapshot declaration shape, but the production
                # runner saves their checkpoint evidence in typed log records.
                has_method_records = any(isinstance(record, dict) and record.get('kind') == 'step'
                                         and record.get('method_type') for record in result.get('log_records') or [])
                method_body = (snapshot_method_body(declared, events) if is_snapshot and not has_method_records
                               else legacy_method_body(result, metadata))
                if manual and manual.get('status') in ('CP', 'C-PASS'):
                    method_body += method_row_html(('', '—', 'Manual case judgement',
                                                   MethodResult('Note: '+display(manual.get('reason')), 0), 'C-PASS'))
                methods = ('<table class="method-table"><caption>Test Steps &amp; Results</caption>'
                           '<colgroup><col class="method-step"><col><col class="method-result"></colgroup>'
                           '<tbody>'+method_body+'</tbody></table>')
                cards.append(f'''<article class="case" id="{key}" data-status="{status}">
<details class="case-disclosure"><summary class="case-heading"><svg class="case-chevron" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="m6 3 5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg><span class="case-title">{escape(row['display_name'] or row['testcase_id'])}</span><span class="status {status.lower()}">{status}</span></summary>
<div class="case-expanded"><section class="test-data"><h3>Test Data</h3><dl class="data-fields">
<dt>Description</dt><dd class="description">{escape(description(result,metadata))}</dd>
{spec_field}<dt>Log</dt><dd class="case-actions">{actions}</dd></dl>
{methods}
{''.join('<p class="notice">'+escape(note)+'</p>' for note in notes)}
</section><section class="test-information"><h3>Test Information</h3>
<div class="detail-content"><dl>{info}</dl></div></section>
</div></details></article>''')
            label = 'Reference' if area == 'reference' else 'Final Report' if report['final'] else 'Test Report'
            sections.append(''.join(cards) if preview else f'<section class="report-group"><div class="group-heading"><p class="eyebrow">{label} / {escape(task["project_name"])}</p><h2>{escape(report["label"])}</h2><p class="muted">{escape(task["plan_name"])} · {len(rows)} cases</p></div>'+''.join(cards)+'</section>')
    generated = execution_date(datetime.now(timezone.utc).isoformat())
    stats = ''.join(f'<div><strong>{count}</strong><span>{label}</span></div>' for label,count in [('Total',sum(totals.values())),('PASS',totals['PASS']),('FAIL',totals['FAIL']),('C-PASS',totals['C-PASS']),('Block',totals['Block']),('NR',totals['NR']),('Running',totals['Running'])] if count or label in ('Total','PASS','FAIL'))
    template = (Path(__file__).parent/'templates'/'standalone_report.html').read_text(encoding='utf-8')
    # Replace once: user-controlled values must never become template instructions.
    import re
    if preview:
        styles = re.search(r'<style>(.*?)</style>', template, re.S)[1]
        content = ''.join(sections).replace('<details class=', '<details open class=')
        html = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
                '<title>Test Case report preview</title><style>'+styles+
                'body{background:white}main{max-width:none;margin:0;padding:20px}.case{border-bottom:0}'
                '</style></head><body><main>'+content+'</main></body></html>')
        return html.encode('utf-8'), {}
    values = {'GENERATED':escape(generated),'STATS':stats,'SECTIONS':''.join(sections)}
    return re.sub(r'\{\{(GENERATED|STATS|SECTIONS)\}\}', lambda m:values[m[1]], template).encode('utf-8'), logs


def generate_html_bundle(db_path, reports):
    html, logs = generate_html_report(db_path, reports)
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('BMC_Report.html', html)
        archive.writestr('README.txt', 'Extract this ZIP first, then open BMC_Report.html in Chrome. Keep the logs folder beside the HTML. Log content is only in the separate attachments.\n')
        for name, content in logs.items():
            archive.writestr(name, content)
    return output.getvalue()


def generate_case_preview(db_path, task_id, case_id):
    """Read one Task membership through the production renderer; no export or writes."""
    report = {'identity': task_id, 'source_details': None, 'final': False, 'label': ''}
    html, _ = generate_html_report(db_path, [('report', report)], preview_case_id=case_id)
    return html.decode('utf-8')
