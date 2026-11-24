"""Record one Plan operation in the same transaction as its changes."""
import json
from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from flask import request
from sqlalchemy import event

import case_order
from models import PlanFolder, PlanHistory, PlanSKU, ProjectPlan, TestCase


OPERATIONS = {
    'patch_plan': 'Update Plan', 'current_folders': 'Create folder',
    'current_folder': 'Update folder', 'current_folder_reorder': 'Reorder folders',
    'current_testcase_delete': 'Remove Test Case', 'patch_testcase': 'Update Test Case',
    'current_delete_selection': 'Remove items', 'remove_with_folder_policy': 'Remove items',
    'current_move_selection': 'Move items', 'move_plan_testcases': 'Move Test Cases',
    'reorder_plan_testcases': 'Reorder Test Cases', 'current_case_resort': 'Sort Test Cases',
    'plan_import_python': 'Import Test Cases', 'repository_add_to_plan': 'Import Test Cases',
    'repository_folder_add_to_plan': 'Import Test Cases', 'import_cases': 'Import Test Cases',
    'import_tc': 'Import Test Cases', 'delete_tc': 'Remove Test Cases',
    'single_update': 'Update parameters',
}


def snapshot(session, plan_id, order):
    items = {}
    name = session.query(ProjectPlan.name).filter_by(id=plan_id).scalar()
    if name is None:
        return items
    items['Plan', plan_id] = {'name': name}
    sku = session.get(PlanSKU, plan_id)
    if sku:
        items['Plan', plan_id]['SKU'] = sku.sku_id
    folders = {f.id: f for f in session.query(PlanFolder.id, PlanFolder.parent_id,
               PlanFolder.name, PlanFolder.position).filter_by(plan_id=plan_id)}
    paths = {None: 'BMC'}

    def path(identity):
        if identity not in paths:
            folder = folders[identity]
            paths[identity] = path(folder.parent_id) + '/' + folder.name
        return paths[identity]

    for folder in folders.values():
        items['Folder', folder.id] = dict(path=path(folder.id), position=folder.position + 1)
    cases = session.query(TestCase.system_id, TestCase.display_name, TestCase.folder_id,
                          TestCase.source_version, TestCase.settings_json).filter_by(plan_id=plan_id)
    records = []
    for case in cases:
        items['Test Case', case.system_id] = dict(name=case.display_name, folder=path(case.folder_id),
            version=case.source_version, parameters=json.loads(case.settings_json or '{}'))
        if order:
            records.append(dict(id=case.system_id, name=case.display_name, folder_id=case.folder_id,
                                source_version=case.source_version))
    positions = Counter()
    ordered = case_order.arrange(session, 'plan:'+plan_id, records) if records else ()
    for case in ordered:
        positions[case['folder_id']] += 1
        items['Test Case', case['id']]['position'] = positions[case['folder_id']]
    return items


def differences(before, after):
    changes = []
    for key in sorted(before.keys() | after.keys()):
        old, new = before.get(key, {}), after.get(key, {})
        if old == new:
            continue
        item = new or old
        fields = [k for k in dict.fromkeys([*old, *new]) if k != 'parameters' and old.get(k) != new.get(k)]
        previous = {k: old[k] for k in fields if k in old}
        current = {k: new[k] for k in fields if k in new}
        if old and new and old.get('parameters') != new.get('parameters'):
            a, b = old['parameters'], new['parameters']
            names = sorted(k for k in a.keys() | b.keys() if k not in a or k not in b or a[k] != b[k])
            previous['parameters'] = {k: a[k] for k in names if k in a}
            current['parameters'] = {k: b[k] for k in names if k in b}
        changes.append(dict(kind=key[0], item=item.get('name') or item['path'],
                            before=previous, after=current))
    return changes


def watch(session, plan_id, operation):
    # Some handlers commit internally to coordinate their filesystem changes.
    # Attach to that first commit, before the database transaction is finalized.
    watched = session.info.setdefault('history_plans', set())
    if plan_id in watched:
        return
    watched.add(plan_id)
    order = operation in ('Move items', 'Move Test Cases', 'Reorder Test Cases', 'Sort Test Cases')
    before = snapshot(session, plan_id, order)
    operator = request.environ.get('REMOTE_USER')
    batch_id = None
    if request.endpoint == 'plan_import_python':
        value = (request.get_json(silent=True) or {}).get('history_batch')
        if isinstance(value, str):
            try:
                batch_id = str(UUID(value))
            except ValueError:
                pass

    @event.listens_for(session, 'before_commit', once=True)
    def record(transaction):
        transaction.flush()
        changes = differences(before, snapshot(transaction, plan_id, order))
        changes.extend(session.info.get('plan_source_changes', []))
        if changes:
            transaction.add(PlanHistory(plan_id=plan_id, recorded_at=datetime.now(timezone.utc).isoformat(),
                operator=operator, operation=operation, batch_id=batch_id, changes=json.dumps(changes, ensure_ascii=False)))


def entries(session, plan_id):
    rows = session.query(PlanHistory).filter_by(plan_id=plan_id).order_by(PlanHistory.id.desc())
    result, batches = [], {}
    for row in rows:
        key = (row.batch_id, row.operator)
        changes = json.loads(row.changes)
        if row.batch_id and key in batches:
            batches[key]['changes'].extend(changes)
            continue
        entry = dict(time=row.recorded_at, operator=row.operator, operation=row.operation, changes=changes)
        result.append(entry)
        if row.batch_id:
            batches[key] = entry
    return result
