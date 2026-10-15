"""Verify the final backend startup against a fresh copy, without a server."""
from pathlib import Path
import hashlib,json,os,sqlite3,subprocess,sys
from contextlib import closing
root=Path(__file__).resolve().parents[1]
source=root/'verification/baseline-workspace/testcase_meta.db'
workspace=root/'verification'/('migration-final-workspace' if '--final' in sys.argv else 'migration-workspace')
workspace.mkdir(exist_ok=True)
target=workspace/'testcase_meta.db'
if target.exists(): raise SystemExit('Preserving existing verification database; choose a new directory')
before_hash=hashlib.sha256(source.read_bytes()).hexdigest()
with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src, closing(sqlite3.connect(target)) as dst:
    src.backup(dst)
    before_count=src.execute('select count(*) from testcases').fetchone()[0]
def snapshot():
    with closing(sqlite3.connect(target.as_uri()+'?mode=ro',uri=True)) as c:
        return {'folders':c.execute('select id,plan_id,parent_id,name,position from plan_folders order by id').fetchall(),'testcases':c.execute('select system_id,plan_id,folder_id,position from testcases order by system_id').fetchall(),'integrity':c.execute('pragma integrity_check').fetchall(),'foreign_keys':c.execute('pragma foreign_key_check').fetchall()}
env=os.environ.copy()
env['BMC_WEB_UI_WORKSPACE_DIR']=str(workspace)
env['BMC_MAIN_PROGRAM_DIR']=str(root/'verification/browser-main')
env['PYTHONIOENCODING']='utf-8'
outputs=[];states=[]
for number in (1,2):
    run=subprocess.run([sys.executable,'-B','-c','import app; app.engine.dispose()'],cwd=root/'web_ui',env=env,capture_output=True,text=True,encoding='utf-8')
    outputs.append({'startup':number,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
    if run.returncode: raise RuntimeError(outputs[-1])
    states.append(snapshot())
result={'source_testcases':before_count,'after_testcases':len(states[1]['testcases']),'folders':len(states[1]['folders']),'startup_snapshots_identical':states[0]==states[1],'integrity':states[1]['integrity'],'foreign_keys':states[1]['foreign_keys'],'source_hash_unchanged':before_hash==hashlib.sha256(source.read_bytes()).hexdigest(),'startups':outputs}
assert result['source_testcases']==result['after_testcases']==17,result
assert result['startup_snapshots_identical'] and result['source_hash_unchanged'],result
assert result['integrity']==[('ok',)] and result['foreign_keys']==[],result
(root/'verification/migration-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='startups'},indent=2))
