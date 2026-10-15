from pathlib import Path
import hashlib,json,subprocess
root=Path('D:/Pytest_redfish/v4.0');base=json.loads(Path('verification/main-file-hashes-before.json').read_text(encoding='utf-8-sig'))
changes=[]
for name,expected in base.items():
 p=root/name
 actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
 if actual!=expected: changes.append(name)
status=subprocess.check_output(['git','status','--short'],cwd=root).decode('utf-8')
Path('verification/main-status-after.txt').write_text(status,encoding='utf-8')
old=Path('verification/main-status-before.txt').read_text(encoding='utf-8-sig')
result={'compared_source_files':len(base),'changed_source_files':changes,'status_identical':old.splitlines()==status.splitlines(),'pristine_copy_sha256':hashlib.sha256(Path('verification/baseline-workspace/testcase_meta.db').read_bytes()).hexdigest()}
Path('verification/main-preservation.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
