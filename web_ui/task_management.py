"""Task information and planned dates, independent of execution scheduling."""
import json
import re
from datetime import date, datetime, timezone
import uuid
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit
from sqlalchemy import literal_column

from models import Task, TaskTestCase, ProjectPlan, Project, ProjectInformation, PlanningTask, PlanSKU, TaskNameSeries, TaskNameReservation, GlobalTaskName, TaskScheduleHistory
from project_naming import compact_name, full_sku_name
from plan_state import StateError, require, unlocked, begin_write

TASK_STATUSES = ('Not Scheduled', 'New', 'On-Going', 'Complete', 'Cancel', 'Pending')


def effective_status(setup):
    if not setup.get('start_date') or not setup.get('end_date'):
        return 'Not Scheduled'
    status = setup.get('task_status', 'New')
    return 'New' if status == 'Not Scheduled' else status


def display_setup(raw):
    setup = json.loads(raw or '{}')
    setup['task_status'] = effective_status(setup)
    return setup

OWNER_FILE = Path(__file__).with_name('task_owners.json')

def owner_options(current=None):
    names = ['TBD'] + json.loads(OWNER_FILE.read_text(encoding='utf-8'))['owners']
    if isinstance(current, str) and current.strip(): names.append(current)
    return list(dict.fromkeys(names))

def validate_owner(value, current=None):
    if not isinstance(value, str) or value not in owner_options(current):
        raise StateError('Choose an Assignee from the list.')
    return value


def validate_name(value):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 255:
        raise StateError('Task name must contain 1 to 255 characters.')
    return value.strip()


def normalize_dates(values):
    if any(v is not None and not isinstance(v, str) for v in values):
        raise StateError('Task dates must be valid YYYY-MM-DD dates.')
    start, end = [v or '' for v in values]
    for value in (start, end):
        if not value:
            continue
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError()
            date.fromisoformat(value)
        except (TypeError, ValueError):
            raise StateError('Task dates must be valid YYYY-MM-DD dates.')
    if start and end and end < start:
        raise StateError('End date must be on or after start date.')
    return start, end

def normalize_idesign(value):
    if not isinstance(value, dict) or set(value) - {'request_id', 'hyperlink'}:
        raise StateError('Supply Request ID and Hyperlink for iDesign ID.')
    request_id, hyperlink = value.get('request_id', ''), value.get('hyperlink', '')
    if not isinstance(request_id, str) or not isinstance(hyperlink, str):
        raise StateError('Supply Request ID and Hyperlink for iDesign ID.')
    request_id, hyperlink = request_id.strip(), hyperlink.strip()
    if not request_id and not hyperlink:
        return {}
    if not request_id or not hyperlink or len(request_id) > 200 or len(hyperlink) > 2048:
        raise StateError('Supply Request ID (up to 200 characters) and Hyperlink (up to 2048 characters).')
    try:
        url = urlsplit(hyperlink)
        url.port  # Reject malformed ports as well as malformed hosts.
        if url.scheme.lower() not in ('http', 'https') or not url.hostname or any(c.isspace() for c in hyperlink):
            raise ValueError()
    except ValueError:
        raise StateError('Hyperlink must be a valid HTTP or HTTPS URL.')
    return dict(request_id=request_id, hyperlink=hyperlink)


def normalize_fw_package(value):
    if not isinstance(value, list) or len(value) > 100:
        raise StateError('FW Package must contain at most 100 Component / Version items.')
    result, seen = [], set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {'component', 'version'}:
            raise StateError('Every FW Package item needs Component and Version.')
        component, version = item['component'], item['version']
        if not isinstance(component, str) or not isinstance(version, str):
            raise StateError('Every FW Package item needs Component and Version.')
        component, version = component.strip(), version.strip()
        if not component or not version or len(component) > 200 or len(version) > 255:
            raise StateError('Component and Version are required (up to 200 / 255 characters).')
        key = component.casefold()
        if key in seen:
            raise StateError('FW Package Component names must be unique.')
        seen.add(key)
        result.append(dict(component=component, version=version))
    return result


def merge_setup(current, incoming, task_type=None):
    if not isinstance(incoming, dict): raise StateError('Task information must be an object.')
    if {'history', 'history_list', 'schedule_history'} & incoming.keys():
        raise StateError('History is read-only.')
    result = dict(json.loads(current or '{}'))
    incoming = dict(incoming)
    if 'idesign' in incoming:
        incoming['idesign'] = normalize_idesign(incoming['idesign'])
    if 'fw_package' in incoming:
        if task_type != 'Test':
            raise StateError('FW Package can only be edited for Test Tasks.')
        incoming['fw_package'] = normalize_fw_package(incoming['fw_package'])
    if 'owner' in incoming:
        validate_owner(incoming['owner'], result.get('owner'))
    if 'task_status' in incoming and incoming['task_status'] not in TASK_STATUSES:
        raise StateError('Choose a valid Task Status.')
    result.update(incoming)
    result['start_date'], result['end_date'] = normalize_dates([result.get('start_date'), result.get('end_date')])
    if 'actual_start_date' in result or 'actual_end_date' in result:
        result['actual_start_date'], result['actual_end_date'] = normalize_dates([result.get('actual_start_date'), result.get('actual_end_date')])
    result['task_status'] = effective_status(result)
    return result


def task_list(session):
    rows = session.query(Task, ProjectPlan, Project).join(ProjectPlan, Task.plan_id == ProjectPlan.id).join(Project, ProjectPlan.project_id == Project.id).all()
    counts = {}
    for (task_id,) in session.query(TaskTestCase.task_id):
        counts[task_id] = counts.get(task_id, 0) + 1
    locked = {task.plan_id for task, _, _ in rows if task.execution_active}
    issued = {r.task_id: r for r in session.query(TaskNameReservation)}
    labels = {p.id: {s['id']: s['full_name'] for s in skus_for(session, p)} for p in session.query(Project)}
    result = []
    for task, plan, project in rows:
        identity = issued.get(task.id)
        result.append(dict(id=task.id, name=task.name, task_type='Test',
                           project_id=project.id, project_name=project.name,
                           sku_id=identity.sku_id if identity else plan_sku(session, plan),
                           sku_name=labels.get(project.id, {}).get(identity.sku_id if identity else plan_sku(session, plan), identity.sku_name if identity else ''),
                           plan_id=plan.id, plan_name=plan.name,
                           setup=display_setup(task.task_metadata),
                           execution_active=bool(task.execution_active), locked=plan.id in locked,
                           scope_count=counts.get(task.id, 0)))
    for task, project in session.query(PlanningTask, Project).join(Project, PlanningTask.project_id == Project.id):
        result.append(dict(id=task.id, name=task.name, task_type='Plan',
                           project_id=project.id, project_name=project.name,
                           sku_id=task.sku_id, sku_name=labels.get(project.id, {}).get(task.sku_id, task.sku_name), plan_id=None, plan_name='',
                           setup=display_setup(task.task_metadata),
                           execution_active=False, locked=False, scope_count=0))
    from schedule_calendar import overrides, working_days
    changes = overrides(session)
    for row in result:
        setup = row['setup']
        start, end = setup.get('start_date'), setup.get('end_date')
        row['working_days'], row['calendar_complete'] = working_days(start, end, changes) if start and end else (None, True)
        actual_start, actual_end = setup.get('actual_start_date'), setup.get('actual_end_date')
        row['actual_working_days'], row['actual_calendar_complete'] = working_days(actual_start, actual_end, changes) if actual_start and actual_end else (None, True)
    return sorted(result, key=lambda r: (r['project_name'], r['task_type'], r['name'], r['id']))


def skus_for(session, project):
    record = session.get(ProjectInformation, project.id)
    skus = json.loads(record.document).get('skus', []) if record else []
    return [dict(sku, full_name=full_sku_name(project.name, sku['name'])) for sku in skus]


def plan_sku(session, plan):
    link = session.get(PlanSKU, plan.id)
    if link:
        return link.sku_id
    project = require(session, Project, plan.project_id)
    # Only unambiguous exact historical names may be inferred. Custom names need an explicit association.
    matches = [s['id'] for s in skus_for(session, project)
               if plan.name.casefold() in (s['name'].casefold(), s['full_name'].casefold())]
    return matches[0] if len(matches) == 1 else None


def bind_plan_sku(session, plan, sku_id):
    project = require(session, Project, plan.project_id)
    skus = skus_for(session, project)
    if skus and not any(s['id'] == sku_id for s in skus):
        raise StateError('Choose a SKU from this Project.')
    if not skus and sku_id:
        raise StateError('This Project has no SKUs.')
    if sku_id:
        session.add(PlanSKU(plan_id=plan.id, sku_id=sku_id))


def options(session):
    locked = {t.plan_id for t in session.query(Task).filter_by(execution_active=True)}
    return [dict(id=p.id, name=p.name, skus=skus_for(session, p),
                 plans=[dict(id=plan.id, name=plan.name, sku_id=plan_sku(session, plan),
                             locked=plan.id in locked)
                        for plan in session.query(ProjectPlan).filter_by(project_id=p.id).order_by(ProjectPlan.name)])
            for p in session.query(Project).order_by(Project.name)]


def resolve_choice(session, data):
    kind = data.get('task_type', 'Test')
    if kind not in ('Plan', 'Test'):
        raise StateError('Choose Task Type: Plan or Test.')
    plan = require(session, ProjectPlan, data.get('plan_id')) if kind == 'Test' else None
    if kind == 'Plan' and data.get('plan_id'):
        raise StateError('Plan Tasks do not select a Plan.')
    project = require(session, Project, data.get('project_id') or (plan.project_id if plan else None))
    if plan and plan.project_id != project.id:
        raise StateError('Plan belongs to another Project.')
    sku_id = data.get('sku_id') or None
    skus = skus_for(session, project)
    sku = next((s for s in skus if s['id'] == sku_id), None)
    if skus and not sku:
        raise StateError('Choose a SKU from this Project.')
    if not skus and sku_id:
        raise StateError('This Project has no SKUs.')
    if plan:
        unlocked(session, plan.id)
        if skus and plan_sku(session, plan) != sku_id:
            raise StateError('Plan belongs to another SKU or has no SKU association.')
    base = plan.name if plan else (sku['full_name'] if sku else project.name)
    prefix = compact_name(base)
    if not prefix:
        raise StateError('The source name must contain letters or numbers.')
    prefix = f'{kind}-{prefix}'
    if len(prefix) > 251:
        raise StateError('The source name is too long for a Task name.')
    scope = json.dumps([kind, project.id, plan.id if plan else sku_id], ensure_ascii=False)
    return kind, project, plan, sku, prefix, scope


def name_key(name):
    return unicodedata.normalize('NFKC', name).strip().casefold()


def reserved_names(session):
    names = {key for (key,) in session.query(GlobalTaskName.name_key)}
    for model in (TaskNameReservation, Task, PlanningTask):
        names.update(name_key(name) for (name,) in session.query(model.name))
    return names


def ensure_global_names(session):
    """Adopt prior names and repair later duplicates without changing any ownership ID."""
    from sqlalchemy import text
    begin_write(session)
    if session.query(Task).filter_by(execution_active=True).first():
        raise StateError('Finish active Tasks before migrating Task names.', 409)
    issued = {r.task_id: r for r in session.query(TaskNameReservation)}
    order = [tid for (tid,) in session.execute(text('SELECT task_id FROM task_name_reservations ORDER BY rowid'))]
    rank = {tid: i for i, tid in enumerate(order)}
    claims = {r.name_key: r for r in session.query(GlobalTaskName)}
    # Deleted and live issued names both stay reserved. Earliest issued owner keeps a duplicate name.
    def claim(name, identity):
        key = name_key(name)
        if key not in claims:
            row = GlobalTaskName(name_key=key, name=name, task_id=identity)
            session.add(row)
            claims[key] = row
        return claims[key]
    for tid in order:
        row = issued[tid]
        claim(row.name, tid)
    rows = list(session.query(Task)) + list(session.query(PlanningTask))
    rows.sort(key=lambda row: (rank.get(row.id, len(rank)), row.id))
    for row in rows:
        claim(row.name, row.id)
    changes = []
    for row in rows:
        if claims[name_key(row.name)].task_id == row.id:
            continue
        identity = issued.get(row.id)
        kind = 'Plan' if isinstance(row, PlanningTask) else 'Test'
        project_id = row.project_id if kind == 'Plan' else require(session, ProjectPlan, row.plan_id).project_id
        sku_id = identity.sku_id if identity else (row.sku_id if kind == 'Plan' else plan_sku(session, require(session, ProjectPlan, row.plan_id)))
        scope = json.dumps([kind, project_id, row.plan_id if kind == 'Test' else sku_id], ensure_ascii=False)
        counter = session.get(TaskNameSeries, scope)
        match = re.fullmatch(r'(.+)-([0-9]{3})', row.name)
        prefix = match.group(1) if match else compact_name(row.name)
        number = max((int(match.group(2)) + 1) if match else 1, (counter.last_number if counter else 0) + 1)
        if not prefix or len(prefix) > 251:
            raise StateError('A conflicting legacy Task name cannot be converted automatically.', 409)
        while number <= 999 and name_key(f'{prefix}-{number:03d}') in claims:
            number += 1
        if number > 999:
            raise StateError('A conflicting Task series has reached 999.', 409)
        old = row.name
        row.name = f'{prefix}-{number:03d}'
        claim(row.name, row.id)
        if identity:
            identity.name = row.name
        else:
            session.add(TaskNameReservation(task_id=row.id, project_id=project_id, task_type=kind,
                                           sku_id=sku_id, sku_name=row.sku_name if kind == 'Plan' else '',
                                           plan_id=row.plan_id if kind == 'Test' else None, name=row.name))
        if counter:
            counter.last_number = number
        else:
            session.add(TaskNameSeries(scope=scope, last_number=number))
        changes.append(dict(task_id=row.id, task_type=kind, old_name=old, new_name=row.name))
    session.flush()
    return changes


def next_name(session, choice):
    kind, project, plan, sku, prefix, scope = choice
    counter = session.get(TaskNameSeries, scope)
    number = (counter.last_number if counter else 0) + 1
    reserved = reserved_names(session)
    while number <= 999 and name_key(f'{prefix}-{number:03d}') in reserved:
        number += 1
    if number > 999:
        raise StateError('This Task series has reached 999. No more Tasks can be created in this series.', 409)
    return f'{prefix}-{number:03d}', number


def create(session, data):
    choice = resolve_choice(session, data)
    kind, project, plan, sku, prefix, scope = choice
    setup = merge_setup(None, data.get('setup', data.get('task_metadata', {})), kind)
    setup.setdefault('owner', 'TBD')
    submitted = data.get('setup', data.get('task_metadata', {})).get('task_status', 'New')
    if submitted not in ('New', 'Not Scheduled'):
        raise StateError('New Tasks must start with Status New or Not Scheduled.')
    name, number = next_name(session, choice)
    identity = str(uuid.uuid4())
    if kind == 'Plan':
        if 'environment_config' in data:
            raise StateError('Plan Tasks do not have execution connections.')
        task = PlanningTask(id=identity, project_id=project.id, sku_id=sku['id'] if sku else None,
                            sku_name=sku['full_name'] if sku else '', name=name,
                            task_metadata=json.dumps(setup, ensure_ascii=False))
    else:
        task = Task(id=identity, plan_id=plan.id, name=name, task_metadata=json.dumps(setup, ensure_ascii=False))
        if 'environment_config' in data:
            import task_environment as te
            te.save(task, data['environment_config'], session)
    counter = session.get(TaskNameSeries, scope)
    if counter:
        counter.last_number = number
    else:
        session.add(TaskNameSeries(scope=scope, last_number=number))
    session.add(TaskNameReservation(task_id=identity, project_id=project.id, task_type=kind,
                                   sku_id=sku['id'] if sku else None, sku_name=sku['full_name'] if sku else '',
                                   plan_id=plan.id if plan else None, name=name))
    session.add(GlobalTaskName(name_key=name_key(name), name=name, task_id=identity))
    session.add(task)
    session.flush()
    return dict(status='ok', id=identity, task_id=identity, name=name, task_type=kind)


def immutable_name(task, value):
    if value != task.name:
        raise StateError('Task names are generated automatically and cannot be changed.')


def manage(session, task_id, data, delete=False):
    if {'history_list', 'schedule_history'} & data.keys():
        raise StateError('History is read-only.')
    if 'history' in data and not ('setup' in data or 'task_metadata' in data):
        raise StateError('History is read-only.')
    task = session.get(Task, task_id) or session.get(PlanningTask, task_id)
    if task is None:
        raise StateError('Task not found.', 404)
    planning = isinstance(task, PlanningTask)
    if not planning:
        unlocked(session, task.plan_id)
    if delete:
        session.delete(task)
        return
    if 'name' in data:
        immutable_name(task, data['name'])
    identity = session.get(TaskNameReservation, task_id)
    fixed = dict(task_type='Plan' if planning else 'Test',
                 project_id=task.project_id if planning else require(session, ProjectPlan, task.plan_id).project_id,
                 sku_id=identity.sku_id if identity else (task.sku_id if planning else plan_sku(session, require(session, ProjectPlan, task.plan_id))),
                 plan_id=None if planning else task.plan_id)
    for key, value in fixed.items():
        if key in data and (data[key] or None) != value:
            raise StateError('Task Type, Project, SKU and Plan stay fixed. Create another Task to change them.')
    if 'setup' in data or 'task_metadata' in data:
        current = json.loads(task.task_metadata or '{}')
        updated = merge_setup(task.task_metadata, data.get('setup', data.get('task_metadata')), 'Plan' if planning else 'Test')
        for field, default in (('idesign', {}), ('fw_package', [])):
            previous, value = current.get(field, default), updated.get(field, default)
            expected = 'expected_' + field
            if (previous != value or expected in data) and data.get(expected) != previous:
                raise StateError(f'The Task {"iDesign ID" if field == "idesign" else "FW Package"} changed. Reload and try again.', 409)
        previous_owner, owner = current.get('owner') or 'TBD', updated.get('owner') or 'TBD'
        if 'expected_owner' in data and data['expected_owner'] != previous_owner:
            raise StateError('The Task Assignee changed. Reload and try again.', 409)
        previous_status, task_status = effective_status(current), effective_status(updated)
        status_changed = previous_status != task_status
        if ('expected_task_status' in data or status_changed) and data.get('expected_task_status') != previous_status:
            raise StateError('The Task Status changed. Reload and try again.', 409)
        original_dates = [current.get('start_date') or '', current.get('end_date') or '']
        new_dates = [updated['start_date'], updated['end_date']]
        original_actual = [current.get('actual_start_date') or '', current.get('actual_end_date') or '']
        new_actual = [updated.get('actual_start_date') or '', updated.get('actual_end_date') or '']
        actual_changed = original_actual != new_actual
        if actual_changed or 'expected_actual_start_date' in data or 'expected_actual_end_date' in data:
            if [data.get('expected_actual_start_date'), data.get('expected_actual_end_date')] != original_actual:
                raise StateError('The Task actual dates changed. Reload and try again.', 409)
        if ('expected_start_date' in data or 'expected_end_date' in data) and [data.get('expected_start_date'), data.get('expected_end_date')] != original_dates:
            raise StateError('The Task schedule changed. Reload and try again.', 409)
        if original_dates != new_dates:
            append_schedule_history(session, task, original_dates, new_dates, data)
        elif 'history' in data and not status_changed and not actual_changed:
            raise StateError('Change the start or end date before saving.')
        if actual_changed:
            append_actual_history(session, task, new_dates, original_actual, new_actual, data)
        if status_changed:
            append_status_history(session, task, new_dates, previous_status, task_status, data)
        if previous_owner != owner:
            append_owner_history(session, task, new_dates, previous_owner, owner)
        task.task_metadata = json.dumps(updated, ensure_ascii=False)
    if 'environment_config' in data:
        if planning:
            raise StateError('Plan Tasks do not have execution connections.')
        import task_environment as te
        te.save(task, data['environment_config'], session)


def append_schedule_history(session, task, original, new_dates, data):
    history = data.get('history')
    if not isinstance(history, str) or not history.strip() or len(history.strip()) > 4000:
        raise StateError('Enter History explaining the schedule change (1 to 4000 characters).')
    if [data.get('expected_start_date'), data.get('expected_end_date')] != original:
        raise StateError('The Task schedule changed. Reload and try again.', 409)
    session.add(TaskScheduleHistory(task_id=task.id,
        task_type='Plan' if isinstance(task, PlanningTask) else 'Test', task_name=task.name,
        created_at=datetime.now(timezone.utc).isoformat(timespec='microseconds'),
        previous_start_date=original[0], previous_end_date=original[1],
        start_date=new_dates[0], end_date=new_dates[1], history=history.strip()))


def append_actual_history(session, task, dates, previous, actual, data):
    reason = data.get('history')
    if not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 4000:
        raise StateError('Enter History explaining the date or status change (1 to 4000 characters).')
    period = lambda values: ' ~ '.join(value or '—' for value in values)
    session.add(TaskScheduleHistory(task_id=task.id,
        task_type='Plan' if isinstance(task, PlanningTask) else 'Test', task_name=task.name,
        created_at=datetime.now(timezone.utc).isoformat(timespec='microseconds'),
        previous_start_date=dates[0], previous_end_date=dates[1],
        start_date=dates[0], end_date=dates[1],
        history=f'Actual dates: {period(previous)} → {period(actual)}\n{reason.strip()}'))


def append_status_history(session, task, dates, previous, status, data):
    reason = data.get('history')
    if not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 4000:
        raise StateError('Enter History explaining the status change (1 to 4000 characters).')
    session.add(TaskScheduleHistory(task_id=task.id,
        task_type='Plan' if isinstance(task, PlanningTask) else 'Test', task_name=task.name,
        created_at=datetime.now(timezone.utc).isoformat(timespec='microseconds'),
        previous_start_date=dates[0], previous_end_date=dates[1],
        start_date=dates[0], end_date=dates[1],
        history=f'Status: {previous} → {status}\n{reason.strip()}'))


def append_owner_history(session, task, dates, previous_owner, owner):
    session.add(TaskScheduleHistory(task_id=task.id,
        task_type='Plan' if isinstance(task, PlanningTask) else 'Test', task_name=task.name,
        created_at=datetime.now(timezone.utc).isoformat(timespec='microseconds'),
        previous_start_date=dates[0], previous_end_date=dates[1],
        start_date=dates[0], end_date=dates[1],
        history=f'Assignee: {previous_owner} → {owner}'))


def reschedule(session, task_id, data):
    task = session.get(Task, task_id) or session.get(PlanningTask, task_id)
    if task is None:
        raise StateError('Task not found.', 404)
    if isinstance(task, Task):
        unlocked(session, task.plan_id)
    if not isinstance(data, dict):
        raise StateError('Schedule information must be an object.')
    current = json.loads(task.task_metadata or '{}')
    original = [current.get('start_date') or '', current.get('end_date') or '']
    if [data.get('expected_start_date'), data.get('expected_end_date')] != original:
        raise StateError('The Task schedule changed. Reload and try again.', 409)
    incoming = dict(start_date=data.get('start_date'), end_date=data.get('end_date'))
    if 'task_status' in data: incoming['task_status'] = data['task_status']
    updated = merge_setup(task.task_metadata, incoming)
    previous_status, task_status = effective_status(current), effective_status(updated)
    status_changed = previous_status != task_status
    if ('expected_task_status' in data or status_changed) and data.get('expected_task_status') != previous_status:
        raise StateError('The Task Status changed. Reload and try again.', 409)
    new_dates = [updated['start_date'], updated['end_date']]
    if original == new_dates and not status_changed:
        raise StateError('Change the start or end date before saving.')
    if original != new_dates:
        append_schedule_history(session, task, original, new_dates, data)
    if status_changed:
        append_status_history(session, task, new_dates, previous_status, task_status, data)
    task.task_metadata = json.dumps(updated, ensure_ascii=False)
    session.flush()
    return dict(status='ok', task_id=task.id, setup=updated)


def history_list(session, task_id):
    rows=session.query(TaskScheduleHistory).filter_by(task_id=task_id).order_by(TaskScheduleHistory.created_at.desc(), literal_column('task_schedule_history.rowid').desc()).all()
    if not rows and session.get(Task, task_id) is None and session.get(PlanningTask, task_id) is None:
        raise StateError('Task not found.', 404)
    fields=('id','task_id','task_type','task_name','created_at','previous_start_date','previous_end_date','start_date','end_date','history')
    return [dict((field, getattr(row, field)) for field in fields) for row in rows]


def register(app, runtime):
    from flask import request, jsonify
    from plan_state import request_session

    # Additive adoption of unambiguous historical SKU Plans; customized unknown names remain unassigned.
    with runtime['DbSession']() as session:
        changes = ensure_global_names(session)
        for plan in session.query(ProjectPlan):
            if session.get(PlanSKU, plan.id) is None:
                sku_id = plan_sku(session, plan)
                if sku_id:
                    session.add(PlanSKU(plan_id=plan.id, sku_id=sku_id))
        session.commit()
    if changes:
        from pathlib import Path
        path = Path(runtime['WORKSPACE_DIR']) / 'task-name-migration.json'
        path.write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding='utf-8')

    @app.route('/api/tasks/options')
    def task_options():
        with runtime['DbSession']() as session:
            return jsonify(projects=options(session), owners=owner_options())

    @app.route('/api/tasks/name-preview')
    def task_name_preview():
        with runtime['DbSession']() as session:
            try:
                choice = resolve_choice(session, request.args)
                return jsonify(name=next_name(session, choice)[0])
            except StateError as exc:
                return jsonify(error=str(exc)), exc.code
