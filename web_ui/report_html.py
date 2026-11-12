"""Portable HTML report package with separate full log files and print layout."""
import io
import zipfile
import json
import os
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from types import SimpleNamespace

from case_log import test_log_text
from report_case import description, display, execution_date, firmware, result_summary, method_table_rows
from report_presentation import note_text, specification_reference


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
            columns = ('m.testcase_id,m.status,m.result_json,m.manual_override_json,m.needs_retest,m.executed_at,'
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
                status = {'Passed':'PASS', 'CP':'CP', 'Failed':'FAIL', 'Block':'Block', 'Running':'Running'}.get(row['status'], 'NR')
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
                if row['needs_retest']:
                    notes.append('Rerun needed: retained evidence predates changes to the Plan or Task connection settings.')
                if manual:
                    notes.append('Manual result: '+display(manual.get('status'))+' · '+display(manual.get('reason')))
                fields = [('Task Name', source.get('name')), ('Tester', setup.get('owner')), ('Execution Time', execution_date(row['executed_at'])), ('FW Package', firmware(setup)), ('DUT Configuration', None)]
                info = ''.join(f'<div><dt>{escape(label)}</dt><dd>{escape('' if label == 'DUT Configuration' else display(value))}</dd></div>' for label,value in fields)
                folder_id, folder_names, visited = row['folder_id'], [], set()
                while folder_id in folders and folder_id not in visited:
                    visited.add(folder_id)
                    folder_names.append(folders[folder_id]['name'])
                    folder_id = folders[folder_id]['parent_id']
                reference = specification_reference(result, metadata, '/'.join(reversed(folder_names)))
                spec_field = '' if reference is None else f'<dt>Spec Ref.</dt><dd>{escape(reference)}</dd>'
                method_body = ''.join('<tr>'+''.join('<td>'+escape(value)+'</td>' for value in method)+'</tr>'
                                      for method in method_table_rows(result, metadata))
                if manual and manual.get('status') == 'CP':
                    method_body += '<tr><td></td><td>—</td><td>Manual case judgement</td><td>Note: '+escape(display(manual.get('reason')))+'</td><td>CP</td></tr>'
                methods = ('<table class="method-table"><caption>Test Steps &amp; Results</caption>'
                           '<colgroup><col class="method-step"><col class="method-type"><col><col class="method-result"><col class="method-judgement"></colgroup>'
                           '<thead><tr><th scope="col">Step</th><th scope="col">Type</th>'
                           '<th scope="col">Description</th><th scope="col">Result</th><th scope="col">Judgement</th></tr></thead>'
                           '<tbody>'+method_body+'</tbody></table>')
                cards.append(f'''<article class="case" id="{key}" data-status="{status}">
<details class="case-disclosure"><summary class="case-heading"><svg class="case-chevron" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="m6 3 5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg><span class="case-title">{escape(row['display_name'] or row['testcase_id'])}</span><span class="status {status.lower()}">{status}</span></summary>
<div class="case-expanded"><details class="test-data"><summary>Test Data</summary><dl class="data-fields">
<dt>Description</dt><dd class="description">{escape(description(result,metadata))}</dd>
<dt>Result Summary</dt><dd class="reason">{escape(result_summary(result, manual))}</dd>
{spec_field}<dt>Log</dt><dd class="case-actions">{actions}</dd></dl>
{methods}
{''.join('<p class="notice">'+escape(note)+'</p>' for note in notes)}
</details><details class="test-information"><summary>Test Information</summary>
<div class="detail-content"><dl>{info}</dl></div></details>
</div></details></article>''')
            label = 'Reference' if area == 'reference' else 'Final Report' if report['final'] else 'Test Report'
            sections.append(''.join(cards) if preview else f'<section class="report-group"><div class="group-heading"><p class="eyebrow">{label} / {escape(task["project_name"])}</p><h2>{escape(report["label"])}</h2><p class="muted">{escape(task["plan_name"])} · {len(rows)} cases</p></div>'+''.join(cards)+'</section>')
    generated = execution_date(datetime.now(timezone.utc).isoformat())
    stats = ''.join(f'<div><strong>{count}</strong><span>{label}</span></div>' for label,count in [('Total',sum(totals.values())),('PASS',totals['PASS']),('FAIL',totals['FAIL']),('CP',totals['CP']),('Block',totals['Block']),('NR',totals['NR']),('Running',totals['Running'])] if count or label in ('Total','PASS','FAIL'))
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
                'body{background:white}main{max-width:none;margin:0;padding:20px 24px}.case{border-bottom:0}'
                '</style></head><body><main>'+content+'</main></body></html>')
        return html.encode('utf-8'), {}
    values = {'GENERATED':escape(generated),'STATS':stats,'SECTIONS':''.join(sections)}
    return re.sub(r'\{\{(GENERATED|STATS|SECTIONS)\}\}', lambda m:values[m[1]], template).encode('utf-8'), logs


def generate_html_bundle(db_path, reports):
    html, logs = generate_html_report(db_path, reports)
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('BMC_Report.html', html)
        archive.writestr('README.txt', 'Extract this ZIP first, then open BMC_Report.html in Chrome. Keep the logs folder beside the HTML. Log content is only in the separate attachments. Use Print / Save PDF for a printable copy; retain this package for full evidence.\n')
        for name, content in logs.items():
            archive.writestr(name, content)
    return output.getvalue()


def generate_case_preview(db_path, task_id, case_id):
    """Read one Task membership through the production renderer; no export or writes."""
    report = {'identity': task_id, 'source_details': None, 'final': False, 'label': ''}
    html, _ = generate_html_report(db_path, [('report', report)], preview_case_id=case_id)
    return html.decode('utf-8')
