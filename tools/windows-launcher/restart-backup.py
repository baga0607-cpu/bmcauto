from contextlib import closing
"""Consistent pre-restart backup and read-only post-restart evidence verification."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys


def fingerprint(conn):
    result = {}
    for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        quoted = '"' + table.replace('"', '""') + '"'
        rows = sorted(repr(row) for row in conn.execute('SELECT * FROM ' + quoted))
        result[table] = {'count': len(rows), 'sha256': hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
    return result


def main():
    operation, database, directory = sys.argv[1:]
    target = Path(directory)
    with closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)) as conn, conn:
        conn.execute('BEGIN')
        active = conn.execute('SELECT count(*) FROM tasks WHERE execution_active=1').fetchone()[0]
        if active:
            raise SystemExit('Active Tasks found; restart/verification cancelled.')
        integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]
        foreign_keys = list(conn.execute('PRAGMA foreign_key_check'))
        if integrity != 'ok' or foreign_keys:
            raise SystemExit('Database integrity checks failed.')
        current = fingerprint(conn)
        if operation == 'before':
            target.mkdir(parents=True, exist_ok=False)
            with closing(sqlite3.connect(target / 'testcase_meta-before.db')) as destination, destination:
                conn.backup(destination)
            (target / 'before-fingerprints.json').write_text(json.dumps(current), encoding='utf-8')
            print(json.dumps({'backup': str(target), 'tables': len(current), 'active_tasks': active}))
        elif operation == 'after':
            before = json.loads((target / 'before-fingerprints.json').read_text(encoding='utf-8'))
            changed = [key for key in before.keys() | current.keys() if before.get(key) != current.get(key)]
            ddl = conn.execute("SELECT sql FROM sqlite_master WHERE name='task_testcases'").fetchone()[0]
            result = dict(integrity=integrity, foreign_key_errors=len(foreign_keys), changed_tables=changed,
                          cp_schema="'CP'" in ddl, tables=len(current))
            (target / 'after-verification.json').write_text(json.dumps(result), encoding='utf-8')
            print(json.dumps(result))
            if changed:
                raise SystemExit('Stored data changed during restart; inspect the backup and verification report.')
        else:
            raise SystemExit('Operation must be before or after')


if __name__ == '__main__':
    main()
