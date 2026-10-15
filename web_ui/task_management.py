"""Task information and planned dates, independent of execution scheduling."""
import json
import re
from datetime import date
from models import Task, TaskTestCase, ProjectPlan, Project
from plan_state import StateError

def validate_name(value):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 255:
        raise StateError('Task name must contain 1 to 255 characters.')
    return value.strip()

def merge_setup(current, incoming):
    if not isinstance(incoming, dict): raise StateError('Task information must be an object.')
    result = dict(json.loads(current or '{}'))
    result.update(incoming)
    dates = [result.get('start_date'), result.get('end_date')]
    if any(v is not None and not isinstance(v,str) for v in dates): raise StateError('Task dates must be valid YYYY-MM-DD dates.')
    start, end = [v or '' for v in dates]
    if bool(start) != bool(end): raise StateError('Supply both start and end dates, or leave both empty.')
    if start:
        try:
            if not all(isinstance(v, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', v) for v in (start, end)):
                raise ValueError()
            first, last = date.fromisoformat(start), date.fromisoformat(end)
        except (TypeError, ValueError): raise StateError('Task dates must be valid YYYY-MM-DD dates.')
        if last < first: raise StateError('End date must be on or after start date.')
    result['start_date'], result['end_date'] = start, end
    return result

def task_list(session):
    rows = session.query(Task, ProjectPlan, Project).join(ProjectPlan, Task.plan_id == ProjectPlan.id).join(Project, ProjectPlan.project_id == Project.id).order_by(Project.name, ProjectPlan.name, Task.name, Task.id).all()
    scope_counts = {}
    for (task_id,) in session.query(TaskTestCase.task_id): scope_counts[task_id] = scope_counts.get(task_id, 0) + 1
    locked_plans = {task.plan_id for task, _, _ in rows if task.execution_active}
    return [dict(id=task.id, name=task.name, project_id=project.id, project_name=project.name,
                 plan_id=plan.id, plan_name=plan.name, setup=json.loads(task.task_metadata or '{}'),
                 execution_active=bool(task.execution_active), locked=plan.id in locked_plans,
                 scope_count=scope_counts.get(task.id, 0)) for task, plan, project in rows]
