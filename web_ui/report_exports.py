"""Read-consistent Task and Plan reports; transient export copies never change live data."""
import io
import json
import sqlite3
import tempfile
import uuid
import zipfile
from contextlib import closing
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Project, ProjectPlan, Task, TaskTestCase
from plan_state import StateError, task_case_dict, co


def selected_tasks(session, project_id, data):
    if not isinstance(data, dict):
        raise StateError('Choose a Plan or Tasks from one Plan.')
    if session.get(Project, project_id) is None:
        raise StateError('Project not found.', 404)
    plans, tasks = data.get('plan_ids', []), data.get('task_ids', [])
    for ids in (plans, tasks):
        if not isinstance(ids, list) or len(ids) > 100 or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
            raise StateError('Select up to 100 unique reports.')
    if not plans and not tasks:
        raise StateError('Select a Plan or Task before generating a report.')
    chosen_plans = [session.get(ProjectPlan, identity) for identity in plans]
    chosen_tasks = [session.get(Task, identity) for identity in tasks]
    if any(p is None or p.project_id != project_id for p in chosen_plans):
        raise StateError('Selected Plan does not belong to this Project.', 400)
    if any(t is None or session.get(ProjectPlan, t.plan_id).project_id != project_id for t in chosen_tasks):
        raise StateError('Selected Task does not belong to this Project.', 400)
    scope = {p.id for p in chosen_plans} | {t.plan_id for t in chosen_tasks}
    if len(scope) != 1:
        raise StateError('Select a Plan or Tasks within the same Plan.')
    plan = session.get(ProjectPlan, next(iter(scope)))
    ids = {t.id for t in chosen_tasks}
    ordered = [t for t in plan.tasks if chosen_plans or t.id in ids]
    if any(t.execution_active for t in ordered):
        raise StateError('Finish active Tasks before generating their reports.', 409)
    return plan, ordered, bool(chosen_plans) or len(ordered) != 1


def final_memberships(session, plan, tasks):
    """Same eligible statuses, timestamp fallback and later-column tie rule as PlanMatrix."""
    cases = co.plan_rows(session, plan.id, plan.testcases)
    maps = [{r.testcase_id:r for r in task.task_testcases} for task in tasks]
    result = []
    for tc in cases:
        winner, source, latest = None, None, float('-inf')
        for task, memberships in zip(tasks, maps):
            row = memberships.get(tc.system_id)
            if row is None or row.status not in ('Passed', 'Failed', 'Block', 'CP', 'C-PASS'):
                continue
            case = task_case_dict(row, tc)
            raw = case.get('result_updated_at') or (case.get('manual_override') or {}).get('modified_at') or case.get('executed_at')
            try:
                timestamp = datetime.fromisoformat(raw.replace('Z', '+00:00')).timestamp() if raw else float('-inf')
            except (ValueError, TypeError):
                timestamp = float('-inf')
            if timestamp >= latest:
                winner, source, latest = row, task, timestamp
        result.append((tc, winner, source))
    return result


def redact_environment(raw):
    def redact(value):
        if isinstance(value, dict):
            return {k:('[redacted]' if any(term in k.lower() for term in ('password','token','secret','authorization')) else redact(v)) for k,v in value.items()}
        if isinstance(value, list):
            return [redact(v) for v in value]
        return value
    try:
        return json.dumps(redact(json.loads(raw)), ensure_ascii=False) if raw else ''
    except (ValueError, TypeError):
        return 'Task-specific environment'


def report_groups(session, project_id, data):
    """Resolve each area in list order; Task matrix order remains Plan-owned."""
    if not isinstance(data, dict):
        raise StateError('Choose reports before generating a report.')
    if 'report_area' not in data and 'reference_area' not in data:
        return [('report', *selected_tasks(session, project_id, data))]
    if 'plan_ids' in data or 'task_ids' in data:
        raise StateError('Use report areas or a legacy selection, not both.')
    if session.get(Project, project_id) is None:
        raise StateError('Project not found.', 404)
    areas = [data.get('report_area'), data.get('reference_area', [])]
    if any(not isinstance(area, list) for area in areas) or not areas[0]:
        raise StateError('Keep at least one report in Report Area.')
    if sum(map(len, areas)) > 100:
        raise StateError('Select up to 100 unique reports.')
    groups, used_tasks, used_plans, used_all_plans = [], set(), set(), set()
    for area_name, entries in zip(('report', 'reference'), areas):
        by_plan, seen = {}, set()
        for entry in entries:
            if (not isinstance(entry, dict) or entry.get('kind') not in ('plan', 'task')
                    or not isinstance(entry.get('id'), str) or not entry['id']):
                raise StateError('Each report needs a Plan or Task ID.')
            kind, identity = entry['kind'], entry['id']
            if (kind, identity) in seen:
                raise StateError('Each report can appear only once in an area.')
            seen.add((kind, identity))
            if kind == 'plan':
                plan = session.get(ProjectPlan, identity)
                task = None
            else:
                task = session.get(Task, identity)
                plan = session.get(ProjectPlan, task.plan_id) if task else None
            if plan is None or plan.project_id != project_id:
                raise StateError('Selected report does not belong to this Project.')
            scope = by_plan.setdefault(plan.id, {'plan_ids': [], 'task_ids': []})
            scope['plan_ids' if kind == 'plan' else 'task_ids'].append(identity)
        area_tasks, area_plans = set(), set()
        for scope in by_plan.values():
            plan, tasks, final = selected_tasks(session, project_id, scope)
            ids = {task.id for task in tasks}
            if ids & used_tasks or plan.id in used_plans or (scope['plan_ids'] and plan.id in used_all_plans):
                raise StateError('A Plan or Task cannot appear in both report areas.')
            area_tasks.update(ids)
            if scope['plan_ids']:
                area_plans.add(plan.id)
            groups.append((area_name, plan, tasks, final))
        used_tasks.update(area_tasks)
        used_plans.update(area_plans)
        used_all_plans.update(by_plan)
    return groups


def prepare_report(session, plan, tasks, final):
    """Prepare a render target in the disposable database only."""
    from report_generator import _safe_name
    source_tasks = None
    source_details = None
    if final:
        report_task = Task(id=str(uuid.uuid4()), plan_id=plan.id, name='Final Report - '+plan.name,
            environment_config='Per-case environment belongs to the source Task.',
            task_metadata=json.dumps({'report_type':'Final Report', 'source_task_count':len(tasks),
                'aggregation':'Latest PASS / FAIL / C-PASS / Block per case; NR and Running ignored. Equal times use later Task column.',
                'environment_note':'Per-case evidence comes from the source Task; Task environments may differ.'}))
        session.add(report_task)
        session.flush()
        source_tasks = {}
        source_details = {}
        for position, (tc, winner, source) in enumerate(final_memberships(session, plan, tasks)):
            values = {key:getattr(winner,key) for key in ('status','bug_id','executed_at','result_json','log_text','api_log_text','manual_override_json','needs_retest')} if winner else {'status':'TBD'}
            session.add(TaskTestCase(task_id=report_task.id, testcase_id=tc.system_id, position=position, selected=True, **values))
            if source:
                source_tasks[tc.system_id] = source.name
                source_details[tc.system_id] = {'name':source.name, 'setup':json.loads(source.task_metadata or '{}')}
        label, filename = plan.name, _safe_name(plan.name)+'_Final_Report.pdf'
    else:
        report_task = tasks[0]
        report_task.environment_config = redact_environment(report_task.environment_config)
        label, filename = report_task.name, _safe_name(report_task.name)+'_Test_Report.pdf'
    return {'identity':report_task.id, 'source_tasks':source_tasks,
            'scope':[t.name for t in tasks] if final else None, 'final':final, 'source_details':source_details,
            'label':label, 'filename':filename}


def reference_separator():
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from report_generator import _build_styles, A4, MARGIN, C_BORDER
    buffer = io.BytesIO()
    styles = _build_styles()
    SimpleDocTemplate(buffer, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN).build([
        Spacer(1, 200), Paragraph('Reference Reports', styles['cover_title']),
        Spacer(1, 18), HRFlowable(width='100%', color=C_BORDER), Spacer(1, 18),
        Paragraph('Supporting reports follow. Their results are separate from the formal reports.', styles['cover_sub'])])
    return buffer.getvalue()


def merge_reports(parts):
    """Keep report order and all log attachments, including colliding filenames."""
    import pypdf
    from report_generator import _safe_name
    writer = pypdf.PdfWriter()
    report_root = None
    reference_root = None
    for index, (area, report, content) in enumerate(parts, 1):
        if area == 'reference' and reference_root is None:
            divider_page = len(writer.pages)
            writer.append_pages_from_reader(pypdf.PdfReader(io.BytesIO(reference_separator())))
            reference_root = writer.add_outline_item('Reference Reports', divider_page)
        reader = pypdf.PdfReader(io.BytesIO(content))
        offset = len(writer.pages)
        writer.append_pages_from_reader(reader)
        if report_root is None:
            report_root = writer.add_outline_item('Report Area', 0)
        writer.add_outline_item(report['label'], offset, parent=reference_root if area == 'reference' else report_root)
        for name, attachments in reader.attachments.items():
            for occurrence, attachment in enumerate(attachments, 1):
                prefix = f'{index:02d}_{_safe_name(report["label"])[:60]}_{occurrence}__'
                writer.add_attachment(prefix+name, attachment)
    writer.add_metadata({'/Title':'BMC Reports', '/Author':'BMCAgent'})
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def generate_selection(db_path, project_id, data, output_format='pdf'):
    from report_generator import generate_task_pdf_report
    with tempfile.TemporaryDirectory(prefix='bmca-report-') as temp:
        copied = Path(temp) / 'export.db'
        with closing(sqlite3.connect(Path(db_path).resolve().as_uri()+'?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(copied)) as destination:
                source.backup(destination)
        engine = create_engine('sqlite:///'+str(copied))
        try:
            with Session(engine) as session:
                # Resolve every scope before adding synthetic Tasks to the copy.
                groups = report_groups(session, project_id, data)
                reports = [(area, prepare_report(session, plan, tasks, final)) for area, plan, tasks, final in groups]
                session.commit()
            if output_format == 'html':
                from report_html import generate_html_bundle
                return generate_html_bundle(str(copied), reports), 'BMC_HTML_Report.zip'
            parts = []
            for index, (area, report) in enumerate(reports):
                output = Path(temp) / f'report-{index}.pdf'
                generate_task_pdf_report(report['identity'], str(output), db_path=str(copied),
                    report_title='BMC Final Report' if report['final'] else 'BMC Test Report',
                    source_tasks=report['source_tasks'], report_scope=report['scope'], source_details=report['source_details'])
                parts.append((area, report, output.read_bytes()))
            if len(parts) == 1:
                return parts[0][2], parts[0][1]['filename']
            return merge_reports(parts), 'BMC_Reports.pdf'
        finally:
            engine.dispose()


def generate_log_archive(db_path, project_id, data):
    """Export exactly the attachments selected by the PDF's Final/Reference rules."""
    import pypdf
    content, filename = generate_selection(db_path, project_id, data)
    reader = pypdf.PdfReader(io.BytesIO(content))
    output = io.BytesIO()
    count = 0
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, attachments in reader.attachments.items():
            # A numeric prefix guarantees distinct portable entries even after sanitizing.
            safe = ''.join('_' if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in name).rstrip('. ')[:180] or 'test.log'
            for attachment in attachments:
                count += 1
                archive.writestr(f'{count:03d}_{safe}', attachment)
    if not count:
        raise StateError('No Test log attachments are available for this selection.', 404)
    return output.getvalue(), Path(filename).stem+'_Logs.zip'
