"""Shared folder-local ordering for Repository, Plan and Task views.

Only manual moves store an override. New cases follow the saved selection in
natural order; stale IDs are ignored. Resorting returns a folder to automatic
number ordering without touching definitions or execution evidence.
"""
import json
import re
from models import CaseListOrder


def natural_key(name):
    return tuple((1, int(part)) if part.isdigit() else (0, part.casefold())
                 for part in re.split(r'(\d+)', name or ''))


def arrange(session, scope, records):
    groups = {}
    for record in records:
        groups.setdefault(record.get('folder_id') or '', []).append(record)
    orders = {row.folder: json.loads(row.case_ids)
              for row in session.query(CaseListOrder).filter_by(scope=scope)}
    result = []
    for folder, rows in groups.items():
        rank = {identity: n for n, identity in enumerate(orders.get(folder, []))}
        rows.sort(key=lambda r: (rank.get(r['id'], len(rank)),
                                natural_key(r.get('tc_name', r.get('name', ''))),
                                r.get('source_version') or '', r['id']))
        result.extend(rows)
    return result


def save(session, scope, folder, ids):
    key = (scope, folder or '')
    row = session.get(CaseListOrder, key)
    if row is None:
        row = CaseListOrder(scope=scope, folder=folder or '')
        session.add(row)
    row.case_ids = json.dumps(ids)


def reset(session, scope, folder):
    row = session.get(CaseListOrder, (scope, folder or ''))
    if row is not None:
        session.delete(row)
        session.flush()


def forget(session, scope, folder, ids):
    row = session.get(CaseListOrder, (scope, folder or ''))
    if row:
        row.case_ids = json.dumps([i for i in json.loads(row.case_ids) if i not in ids])


def plan_rows(session, plan_id, rows):
    rows = list(rows)
    by_id = {row.system_id: row for row in rows}
    return [by_id[r['id']] for r in arrange(session, 'plan:'+plan_id,
            [dict(id=r.system_id, tc_name=r.display_name, folder_id=r.folder_id,
                  source_version=r.source_version) for r in rows])]
