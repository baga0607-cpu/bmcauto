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


def generate_html_report(db_path, reports):
    sections, logs, totals = [], {}, Counter()
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        for group_index, (area, report) in enumerate(reports):
            task = conn.execute('SELECT t.*,p.name AS plan_name,pr.name AS project_name FROM tasks t JOIN project_plans p ON p.id=t.plan_id JOIN projects pr ON pr.id=p.project_id WHERE t.id=?', (report['identity'],)).fetchone()
            rows = conn.execute('SELECT m.*,c.display_name,c.script_path,c.script_kind,c.folder_id FROM task_testcases m JOIN testcases c ON c.system_id=m.testcase_id WHERE m.task_id=? AND c.plan_id=? ORDER BY m.position', (task['id'], task['plan_id'])).fetchall()
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
                status = {'Passed':'PASS', 'Failed':'FAIL', 'Block':'Block', 'Running':'Running'}.get(row['status'], 'NR')
                if area == 'report':
                    totals[status] += 1
                text = test_log_text(row['log_text'], row['api_log_text'])
                filename = str(row['display_name'] or row['testcase_id'])
                filename = ''.join('_' if c in '<>:"/\\|?*' or ord(c)<32 else c for c in filename)[:100].rstrip('. ')+'__test.log'
                actions = '<span class="muted">No Test log available</span>'
                if text:
                    from urllib.parse import quote
                    attachment = f'logs/{group_index+1:02d}-{index+1:03d}_{filename}'
                    logs[attachment] = text.encode('utf-8')
                    href = escape(quote(attachment), quote=True)
                    actions = f'<a class="attachment-link" href="{href}" target="_blank" rel="noopener">Open Log attachment ↗</a><span class="muted">.log</span>'
                notes = []
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
                methods = ('<table class="method-table"><caption>Test Steps &amp; Results</caption>'
                           '<colgroup><col class="method-id"><col class="method-type"><col><col class="method-result"></colgroup>'
                           '<thead><tr><th scope="col">ID</th><th scope="col">Type</th>'
                           '<th scope="col">Description</th><th scope="col">Result</th></tr></thead>'
                           '<tbody>'+method_body+'</tbody></table>')
                cards.append(f'''<article class="case" id="{key}" data-status="{status}">
<details class="case-disclosure"><summary class="case-heading"><svg class="case-chevron" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="m6 3 5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg><span class="case-title">{escape(row['display_name'] or row['testcase_id'])}</span><span class="status {status.lower()}">{status}</span></summary>
<div class="case-expanded"><details class="test-data"><summary>Test Data</summary><dl class="data-fields">
<dt>Description</dt><dd class="description">{escape(description(result,metadata))}</dd>
<dt>Result Summary</dt><dd class="reason">{escape(result_summary(result, manual))}</dd>
<dt>Note</dt><dd class="execution-note">{escape(note_text(result))}</dd>
{spec_field}<dt>Log</dt><dd class="case-actions">{actions}</dd></dl>
{methods}
{''.join('<p class="notice">'+escape(note)+'</p>' for note in notes)}
</details><details class="test-information"><summary>Test Information</summary>
<div class="detail-content"><dl>{info}</dl></div></details>
</div></details></article>''')
            label = 'Reference' if area == 'reference' else 'Final Report' if report['final'] else 'Test Report'
            sections.append(f'<section class="report-group"><div class="group-heading"><p class="eyebrow">{label} / {escape(task["project_name"])}</p><h2>{escape(report["label"])}</h2><p class="muted">{escape(task["plan_name"])} · {len(rows)} cases</p></div>'+''.join(cards)+'</section>')
    generated = execution_date(datetime.now(timezone.utc).isoformat())
    stats = ''.join(f'<div><strong>{count}</strong><span>{label}</span></div>' for label,count in [('Total',sum(totals.values())),('PASS',totals['PASS']),('FAIL',totals['FAIL']),('Block',totals['Block']),('NR',totals['NR']),('Running',totals['Running'])] if count or label in ('Total','PASS','FAIL'))
    template = (Path(__file__).parent/'templates'/'standalone_report.html').read_text(encoding='utf-8')
    # Replace once: user-controlled values must never become template instructions.
    import re
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
