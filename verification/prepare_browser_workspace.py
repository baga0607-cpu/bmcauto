"""Prepare isolated browser assets; never open the live database for writes."""
from pathlib import Path
import json
import shutil
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('D:/Pytest_redfish/v4.0')
DEST = ROOT / 'verification' / 'browser-main'
WORKSPACE = ROOT / 'verification' / 'browser-workspace'

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    target = WORKSPACE / 'testcase_meta.db'
    if target.exists():
        raise SystemExit('Browser database already exists; preserve it or choose a new verification directory.')
    source = ROOT / 'verification' / 'baseline-workspace' / 'testcase_meta.db'
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
        cases = dst.execute('select system_id, script_path from testcases').fetchall()
    database = DEST / 'testcase_database'
    database.mkdir(exist_ok=True)
    (database / '__init__.py').touch()
    (database / 'scripts').mkdir(exist_ok=True)
    (database / 'scripts' / '__init__.py').touch()
    missing = []
    copied = []
    for case_id, script_path in cases:
        relative = Path(*script_path.split('.'))
        origin = (SOURCE / 'main_program' / relative).resolve()
        allowed = (SOURCE / 'main_program' / 'testcase_database').resolve()
        if not origin.is_relative_to(allowed):
            raise RuntimeError(f'Executable outside allowed source tree: {case_id}')
        destination = DEST / relative
        if origin.is_dir():
            shutil.copytree(origin, destination)
            copied.append(case_id)
        else:
            missing.append(case_id)
    for name in ('console_helper.py',):
        shutil.copy2(ROOT / 'main_program' / name, DEST / name)
    steps = SOURCE / 'main_program' / 'testcase_database' / 'steps'
    if steps.is_dir():
        shutil.copytree(steps, database / 'steps', ignore=shutil.ignore_patterns('__pycache__'))
    (DEST / 'config.yaml').write_text('redfish:\n  host: https://sandbox.invalid\n  username: sandbox\n  password: sandbox\n  verify_ssl: false\n', encoding='utf-8')
    result = {'copied_scripts': len(copied), 'missing_script_ids': missing, 'testcase_count': len(cases), 'workspace': str(WORKSPACE)}
    (ROOT / 'verification' / 'browser-assets.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
