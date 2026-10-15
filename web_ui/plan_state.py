"""Transactional Plan structure and live Task state.

Every write starts with SQLite BEGIN IMMEDIATE before reading lock state. A Plan
is locked by a Task row, so independent processes observe the same lock.
"""
import json
import task_environment as te
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session
from models import Base, PlanFolder, ProjectPlan, TestCase, Task, TaskTestCase, Category, PlanSubfolder, RepositoryCase

class StateError(ValueError):
    def __init__(self, message, code=400):
        super().__init__(message); self.code = code

def begin_write(session):
    if not session.in_transaction():
        session.execute(text('BEGIN IMMEDIATE'))

def require(session, model, identity):
    if not identity: raise StateError(f"Missing {model.__name__} identity",400)
    row=session.get(model, identity)
    if row is None: raise StateError(f'{model.__name__} not found',404)
    return row

def unlocked(session, plan_id):
    require(session, ProjectPlan, plan_id)
    if session.query(Task).filter_by(plan_id=plan_id,execution_active=True).first():
        raise StateError('Plan is locked by execution',409)

def siblings(session,plan_id,parent_id):
    return session.query(PlanFolder).filter_by(plan_id=plan_id,parent_id=parent_id).order_by(PlanFolder.position,PlanFolder.id).all()

def normalize(rows):
    for position,row in enumerate(rows): row.position=position

def validate_folder(session,plan_id,name,parent_id,identity=None):
    name=(name or '').strip()
    if not name or '/' in name or '\\' in name: raise StateError('Folder name must be nonempty and cannot contain a path separator')
    if parent_id:
        parent=require(session,PlanFolder,parent_id)
        if parent.plan_id != plan_id: raise StateError('Folder belongs to another Plan')
        cursor=parent
        while cursor:
            if cursor.id==identity:raise StateError('A folder cannot become its own descendant')
            cursor=cursor.parent
    if any(f.id!=identity and f.normalized_name==name.casefold() for f in siblings(session,plan_id,parent_id)):
        raise StateError('A sibling folder already has this name',409)
    return name

def create_folder(session,plan_id,name,parent_id=None):
    unlocked(session,plan_id)
    name=validate_folder(session,plan_id,name,parent_id)
    f=PlanFolder(id=str(uuid.uuid4()),plan_id=plan_id,parent_id=parent_id,name=name,normalized_name=name.casefold(),position=len(siblings(session,plan_id,parent_id)))
    require(session,ProjectPlan,plan_id).folders_migrated=True
    session.add(f); session.flush(); return f

def change_folder(session,folder_id,data):
    f=require(session,PlanFolder,folder_id); unlocked(session,f.plan_id)
    old_parent=f.parent_id; parent=data.get('parent_id',old_parent)
    name=validate_folder(session,f.plan_id,data.get('name',f.name),parent,f.id)
    relative=None
    if 'relative_to' in data or 'insertion' in data:
        if not isinstance(data.get('relative_to'),str) or data.get('insertion') not in ('before','after'):
            raise StateError('Supply a relative folder and before/after insertion')
        relative=require(session,PlanFolder,data['relative_to'])
        if relative.id==f.id or relative.plan_id!=f.plan_id or relative.parent_id!=parent:
            raise StateError('Relative folder must be another sibling in the destination Plan and parent')
    destination=[row for row in siblings(session,f.plan_id,parent) if row.id!=f.id]
    f.name=name; f.normalized_name=name.casefold()
    if parent!=old_parent:
        f.position=len(destination); f.parent_id=parent
        session.flush(); normalize(siblings(session,f.plan_id,old_parent))
        session.expire(f,['parent'])
    if relative:
        position=next(i for i,row in enumerate(destination) if row.id==relative.id)
        destination.insert(position+(data['insertion']=='after'),f)
        normalize(destination)
    session.flush(); return f

def resolve_folder(session,plan_id,data,default='Custom'):
    if data.get('folder_id'):
        f=require(session,PlanFolder,data['folder_id'])
        if f.plan_id!=plan_id: raise StateError('Destination belongs to another Plan')
        return f
    path=data.get('folder_path',data.get('FOLDER_PATH'))
    if path is None:
        path=data.get('category',data.get('CATEGORY')) or default
        if data.get('custom_subfolder'): path='Custom/'+data['custom_subfolder']
    parts=path if isinstance(path,list) else str(path).split('/')
    parts=[str(p).strip() for p in parts]
    if not parts or any(not p for p in parts): parts=['Custom']
    parent=None
    for name in parts:
        match=next((f for f in siblings(session,plan_id,parent) if f.normalized_name==name.casefold()),None)
        if match is None: match=create_folder(session,plan_id,name,parent)
        parent=match.id
    return match

def assign_folder(session,tc,folder):
    if tc.plan_id!=folder.plan_id: raise StateError('Destination belongs to another Plan')
    old=tc.folder_id
    if old==folder.id: return
    tc.folder_id=folder.id
    tc.position=session.query(TestCase).filter(TestCase.folder_id==folder.id,TestCase.system_id!=tc.system_id).count()
    # Compatibility strings are derived from current placement for old import clients.
    root=folder.parent or folder
    category=session.query(Category).filter_by(name=root.name).first()
    if category is None:
        category=Category(name=root.name); session.add(category); session.flush()
    tc.category_id=category.id; tc.subfolder_id=None
    session.flush()
    if old: normalize(session.query(TestCase).filter_by(folder_id=old).order_by(TestCase.position,TestCase.system_id).all())
    session.expire(tc,['folder_obj'])

def replace_scope(session,task_id,items):
    task=require(session,Task,task_id); unlocked(session,task.plan_id)
    ids=[i['id'] if isinstance(i,dict) else i for i in items]
    if len(ids)!=len(set(ids)): raise StateError('Duplicate Task testcase membership',409)
    for identity in ids:
        tc=require(session,TestCase,identity)
        if tc.plan_id!=task.plan_id: raise StateError('Task scope must belong to its own Plan')
    existing={r.testcase_id:r for r in session.query(TaskTestCase).filter_by(task_id=task_id)}
    for identity,row in existing.items():
        if identity not in ids: session.delete(row)
    for position,item in enumerate(items):
        identity=ids[position]; row=existing.get(identity)
        if row is None:
            row=TaskTestCase(task_id=task_id,testcase_id=identity,status='TBD'); session.add(row)
        row.position=position
        if isinstance(item,dict): row.selected=item.get('selected',True)
    session.flush()

def task_case_dict(row,tc):
    case=tc.to_dict()
    case.update(status=row.status,selected=bool(row.selected),position=row.position,
                bug_id=row.bug_id or '',executed_at=row.executed_at,
                result=json.loads(row.result_json) if row.result_json else None,
                log_text=row.log_text or '',api_log_text=row.api_log_text or '',
                manual_override=json.loads(row.manual_override_json) if row.manual_override_json else None,
                needs_retest=bool(row.needs_retest),
                retest_message='Plan test conditions or Task connection settings changed; rerun this Test Case.' if row.needs_retest else '')
    return case


def live_task_case(session,task_id,tc_id):
    task=require(session,Task,task_id)
    match=session.query(TaskTestCase,TestCase).join(TestCase,TaskTestCase.testcase_id==TestCase.system_id).filter(
        TaskTestCase.task_id==task_id,TaskTestCase.testcase_id==tc_id,TestCase.plan_id==task.plan_id).first()
    if match is None: raise StateError('Task testcase not found',404)
    return task,match[0],match[1]


def set_manual_status(session,task_id,tc_id,data):
    task,row,tc=live_task_case(session,task_id,tc_id)
    unlocked(session,task.plan_id)
    status=data.get('status'); reason=data.get('reason','')
    if status not in ('TBD','Passed','Failed'): raise StateError('Manual status must be TBD, Passed, or Failed')
    if not isinstance(reason,str): raise StateError('Manual reason must be text')
    row.status=status
    row.manual_override_json=json.dumps(dict(status=status,reason=reason.strip(),modified_at=datetime.now(timezone.utc).isoformat()),ensure_ascii=False)
    session.flush()
    return task_case_dict(row,tc)


def summary(session,task_id,root=None):
    task=require(session,Task,task_id)
    cases=[]; counts={'Passed':0,'Failed':0,'TBD':0}
    for row,tc in session.query(TaskTestCase,TestCase).join(TestCase,TaskTestCase.testcase_id==TestCase.system_id).filter(TaskTestCase.task_id==task_id,TestCase.plan_id==task.plan_id).order_by(TaskTestCase.position):
        case=task_case_dict(row,tc)
        import single_case
        case['automation']=single_case.automation_for_case(root,tc)
        cases.append(case); counts[row.status if row.status in ('Passed','Failed') else 'TBD']+=1
    return dict(id=task.id,task_id=task.id,name=task.name,plan_id=task.plan_id,execution_active=bool(task.execution_active),setup=json.loads(task.task_metadata or '{}'),connection_configured=bool(te.normalize(task.environment_config)["host"]),testcases=cases,counts=counts)

def start_execution(session,task_id,ids):
    task=require(session,Task,task_id); unlocked(session,task.plan_id)
    if not isinstance(ids,list) or not ids: raise StateError('Select at least one existing Task testcase')
    if len(ids)!=len(set(ids)): raise StateError('Duplicate selection',409)
    rows={r.testcase_id:r for r in session.query(TaskTestCase).filter_by(task_id=task_id)}
    if any(i not in rows for i in ids): raise StateError('Execution cannot add Task scope')
    for i in ids:
        row=rows[i]; row.manual_override_json=None; row.status='TBD'; row.result_json=None; row.log_text=None; row.api_log_text=None; row.executed_at=None
    task.execution_active=True; task.execution_selection=json.dumps(ids); task.execution_token=str(uuid.uuid4())
    task.execution_worker_id=None; task.execution_stop_requested=False
    return task.execution_token

def canonical_status(status):
    value=str(status or '').casefold()
    return {'pass':'Passed','passed':'Passed','fail':'Failed','failed':'Failed','running':'Running','tbd':'TBD','pending':'TBD','tdb':'TBD','interrupted':'TBD'}.get(value,'Failed')

def check_execution_token(task, token):
    if not task.execution_active or not token or token != task.execution_token: raise StateError('Stale or inactive execution',409)

def save_result(session,task_id,data):
    task=require(session,Task,task_id)
    check_execution_token(task,data.get('execution_token'))
    row=session.query(TaskTestCase).filter_by(task_id=task_id,testcase_id=data.get('id') or data.get('testcase_id')).first()
    if row is None: raise StateError('Execution cannot add Task scope',400)
    if not task.execution_active: raise StateError('Task execution is not active',409)
    if row.testcase_id not in json.loads(task.execution_selection or '[]'): raise StateError('Testcase is not selected for this execution')
    row.status=canonical_status(data.get('status'))
    row.result_json=json.dumps(data.get('result',data),ensure_ascii=False)
    row.log_text=data.get('log_text',data.get('log','')); row.api_log_text=data.get('api_log_text','')
    row.executed_at=data.get('executed_at'); row.bug_id=data.get('bug_id',row.bug_id)
    if row.status in ('Passed','Failed'):
        row.needs_retest=False
    session.flush()

def finish_execution(session,task_id,execution_token):
    task=require(session,Task,task_id)
    check_execution_token(task,execution_token)
    if task.execution_worker_id: raise StateError('Execution worker is still stopping',409)
    for row in session.query(TaskTestCase).filter_by(task_id=task_id,status='Running'):
        row.status='TBD'; row.result_json=None; row.log_text=None; row.api_log_text=None; row.executed_at=None
    task.execution_active=False; task.execution_selection=None; task.execution_token=None; task.execution_stop_requested=False

def folder_descendants(session,folder):
    result=[];pending=[folder.id]
    while pending:
        children=session.query(PlanFolder).filter_by(parent_id=pending.pop()).all()
        result.extend(children);pending.extend(f.id for f in children)
    return result

def impact(session,folder=None,testcases=None):
    descendants=[]
    if folder:
        descendants=folder_descendants(session,folder)
        testcases=session.query(TestCase).filter(TestCase.folder_id.in_([folder.id]+[f.id for f in descendants])).all()
    testcases=testcases or []
    ids=[t.system_id for t in testcases]
    rows=session.query(TaskTestCase).filter(TaskTestCase.testcase_id.in_(ids)).all() if ids else []
    plan=require(session,ProjectPlan,folder.plan_id if folder else testcases[0].plan_id)
    return dict(name=folder.name if folder else testcases[0].display_name,names=[t.display_name for t in testcases],descendant_folder_count=len(descendants),testcase_count=len(testcases),affected_task_count=len({r.task_id for r in rows}),task_testcase_count=len(rows),requires_acknowledgement=bool(folder and (testcases or descendants)))

def delete_content(session,main_program_dir,data,folder=None,testcases=None):
    preview=impact(session,folder,testcases)
    if data.get('confirm') is not True: raise StateError('Impact confirmation is required')
    if preview['requires_acknowledgement'] and data.get('acknowledgement') is not True: raise StateError('I understand acknowledgement is required')
    descendants=folder_descendants(session,folder) if folder else []
    if folder: testcases=session.query(TestCase).filter(TestCase.folder_id.in_([folder.id]+[f.id for f in descendants])).all()
    unlocked(session,folder.plan_id if folder else testcases[0].plan_id)
    root=(Path(main_program_dir)/'testcase_database'/'scripts').resolve()
    recovery=root/'.delete-recovery'/str(uuid.uuid4()); staged=[]
    try:
        for tc in testcases:
            source=(root/tc.script_path.split('.')[-1]).resolve()
            if source.parent!=root: raise StateError('Invalid executable directory')
            if source.exists():
                recovery.mkdir(parents=True,exist_ok=True)
                target=recovery/source.name; shutil.move(str(source),str(target)); staged.append((source,target))
        ids=[tc.system_id for tc in testcases]
        deleted_folder_ids={folder.id, *(child.id for child in descendants)} if folder else set()
        surviving_folder_ids={tc.folder_id for tc in testcases if tc.folder_id} - deleted_folder_ids
        session.query(TaskTestCase).filter(TaskTestCase.testcase_id.in_(ids)).delete(synchronize_session=False)
        for tc in testcases: session.delete(tc)
        session.flush()
        for folder_id in sorted(surviving_folder_ids):
            normalize(session.query(TestCase).filter_by(folder_id=folder_id).order_by(TestCase.position,TestCase.system_id).all())
        for child in reversed(descendants): session.delete(child)
        session.flush()
        if folder:
            old_parent=folder.parent_id; plan_id=folder.plan_id; session.delete(folder); session.flush(); normalize(siblings(session,plan_id,old_parent))
        session.commit()
    except Exception as error:
        session.rollback(); restore_errors=[]
        for source,target in reversed(staged):
            try: shutil.move(str(target),str(source))
            except Exception as restoration:
                try: target.replace(source)
                except OSError:
                    # Preserve recoverable data when the filesystem itself is unavailable.
                    restore_errors.append(f'{target}: {restoration}')
        if restore_errors: raise RuntimeError('Deletion rolled back; file recovery required: '+'; '.join(restore_errors)) from error
        raise
    if recovery.exists():
        try: shutil.rmtree(recovery)
        except OSError:
            import logging
            logging.exception('Committed deletion recovery cleanup pending: %s',recovery)
    return preview

def migrate_current_state(engine,log_path):
    """Atomic SQLite schema/data migration; no writes outside this engine's DB."""
    messages=[]
    with engine.connect() as conn:
        conn.exec_driver_sql('BEGIN IMMEDIATE')
        try:
            columns={'project_plans':{'folders_migrated':'BOOLEAN NOT NULL DEFAULT 0'},'testcases':{'folder_id':'TEXT'},'tasks':{'execution_active':'BOOLEAN NOT NULL DEFAULT 0','execution_selection':'TEXT','execution_token':'TEXT','execution_worker_id':'TEXT','execution_stop_requested':'BOOLEAN NOT NULL DEFAULT 0'},'task_testcases':{'manual_override_json':'TEXT','result_json':'TEXT','log_text':'TEXT','api_log_text':'TEXT'}}
            for table, additions in columns.items():
                present={r[1] for r in conn.exec_driver_sql(f'PRAGMA table_info({table})')}
                for name,kind in additions.items():
                    if name not in present: conn.exec_driver_sql(f'ALTER TABLE {table} ADD COLUMN {name} {kind}')
            for table, additions in {
                'testcases': {'script_kind': "TEXT NOT NULL DEFAULT 'steps'", 'source_version': 'TEXT',
                              'repository_id': 'TEXT', 'settings_json': "TEXT NOT NULL DEFAULT '{}'",
                              'settings_revision': 'INTEGER NOT NULL DEFAULT 0'},
                'task_testcases': {'needs_retest': 'BOOLEAN NOT NULL DEFAULT 0'},
            }.items():
                present={r[1] for r in conn.exec_driver_sql(f'PRAGMA table_info({table})')}
                for name,kind in additions.items():
                    if name not in present: conn.exec_driver_sql(f'ALTER TABLE {table} ADD COLUMN {name} {kind}')
            RepositoryCase.__table__.create(conn, checkfirst=True)
            PlanFolder.__table__.create(conn,checkfirst=True)
            with Session(bind=conn,join_transaction_mode='rollback_only') as session:
                original_count=session.query(TestCase).count()
                for plan in session.query(ProjectPlan).all():
                    try: order=json.loads(plan.category_order or '[]')
                    except (ValueError,TypeError): order=[]
                    if not isinstance(order,list): order=[]
                    def root(name):
                        existing=next((f for f in siblings(session,plan.id,None) if f.normalized_name==name.strip().casefold()),None)
                        if existing: return existing
                        f=create_folder(session,plan.id,name); messages.append(f'created folder {plan.id} {f.path}'); return f
                    # Existing migrated rows keep placement. Legacy structures are read only on first migration.
                    pending=session.query(TestCase).filter_by(plan_id=plan.id,folder_id=None).order_by(TestCase.position,TestCase.system_id).all()
                    convert_legacy_structure=not plan.folders_migrated
                    if convert_legacy_structure or pending:
                        for name in order if convert_legacy_structure else []:
                            if isinstance(name,str) and name.strip() and '/' not in name and '\\' not in name: root(name)
                        for tc in pending:
                            name=tc.category_obj.name.strip() if tc.category_obj and tc.category_obj.name else ''
                            if name and '/' not in name and '\\' not in name: root(name)
                        legacy=session.query(PlanSubfolder).filter_by(plan_id=plan.id).order_by(PlanSubfolder.position,PlanSubfolder.id).all() if convert_legacy_structure else []
                        mapping={}; ambiguous=set()
                        for sub in legacy:
                            custom=root('Custom'); key=(sub.subfolder_name or '').strip().casefold()
                            if not key or '/' in key or '\\' in key: ambiguous.add(sub.id); continue
                            matches=[x for x in legacy if (x.subfolder_name or '').strip().casefold()==key]
                            folder=next((f for f in siblings(session,plan.id,custom.id) if f.normalized_name==key),None)
                            if folder is None:
                                folder=create_folder(session,plan.id,sub.subfolder_name,custom.id); messages.append(f'created folder {plan.id} {folder.path}')
                            if len(matches)>1: ambiguous.update(x.id for x in matches)
                            mapping[sub.id]=folder
                        for tc in pending:
                            category=tc.category_obj.name.strip() if tc.category_obj and tc.category_obj.name else ''
                            invalid=not category or '/' in category or '\\' in category
                            if tc.subfolder_id:
                                invalid=category.casefold()!='custom' or tc.subfolder_id not in mapping or tc.subfolder_id in ambiguous
                                folder=root('Custom') if invalid else mapping[tc.subfolder_id]
                            else: folder=root('Custom') if invalid else root(category)
                            tc.folder_id=folder.id
                            messages.append(f'{"redirected" if invalid else "moved"} testcase {plan.id}/{tc.system_id} -> {folder.path}')
                        session.flush()
                        for f in session.query(PlanFolder).filter_by(plan_id=plan.id):
                            normalize(session.query(TestCase).filter_by(folder_id=f.id).order_by(TestCase.position,TestCase.system_id).all())
                    plan.folders_migrated=True
                for row in session.query(TaskTestCase):
                    row.status=canonical_status(row.status)
                    if row.status=='Running': row.status='TBD'
                    task=session.get(Task,row.task_id); tc=session.get(TestCase,row.testcase_id)
                    if not task or not tc or task.plan_id!=tc.plan_id: raise ValueError(f'Invalid Task ownership {row.task_id}/{row.testcase_id}')
                session.flush()
                for tc in session.query(TestCase):
                    if not tc.folder_obj or tc.folder_obj.plan_id!=tc.plan_id: raise ValueError(f'Invalid testcase ownership {tc.plan_id}/{tc.system_id}')
                sibling_keys=set()
                for f in session.query(PlanFolder):
                    key=(f.plan_id,f.parent_id,f.name.strip().casefold())
                    if key in sibling_keys or f.normalized_name!=key[2]: raise ValueError(f'Invalid folder name {f.plan_id}/{f.id}')
                    sibling_keys.add(key)
                    if f.parent and f.parent.plan_id!=f.plan_id: raise ValueError(f'Invalid folder ownership {f.plan_id}/{f.id}')
                    ancestors=set();cursor=f
                    while cursor:
                        if cursor.id in ancestors:raise ValueError('Folder cycle detected')
                        ancestors.add(cursor.id);cursor=cursor.parent
                if session.query(TestCase).count()!=original_count: raise ValueError('Testcase count changed during migration')
                for task in session.query(Task):
                    task.execution_active=False; task.execution_selection=None; task.execution_token=None; task.execution_stop_requested=False; task.execution_worker_id=None
                session.flush()
            conn.exec_driver_sql('CREATE UNIQUE INDEX IF NOT EXISTS uq_task_scope ON task_testcases(task_id,testcase_id)')
            conn.exec_driver_sql('DROP TABLE IF EXISTS task_execution_attempts')
            conn.commit()
        except Exception:
            conn.rollback(); raise
    path=Path(log_path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as log:
        log.write('\n'.join(messages)+('\n' if messages else 'migration validated; no placement changes\n'))

def request_session(factory):
    from flask import g, has_request_context
    return g.plan_write_session if has_request_context() and hasattr(g,'plan_write_session') else factory()

def install_routes(app, runtime):
    from flask import request, jsonify, g
    from functools import wraps

    @app.before_request
    def reserve_plan_write():
        if request.method not in ('POST','PUT','PATCH','DELETE'): return
        if request.endpoint in ('handle_input','stop_testcase','manage_settings'): return
        session=runtime['DbSession'](); g.plan_write_session=session
        try:
            begin_write(session)
            data=request.get_json(silent=True) or {}; args=request.view_args or {}; plans=set()
            for source in (data,args):
                if source.get('plan_id'): plans.add(source['plan_id'])
                if source.get('task_id'): plans.add(require(session,Task,source['task_id']).plan_id)
                for key in ('tc_id','system_id','original_id','testcase_id'):
                    if source.get(key): plans.add(require(session,TestCase,source[key]).plan_id)
                if source.get('folder_id') and request.endpoint not in ('repository_import','repository_case_move','repository_folder_add_to_plan','repository_folder_modify','repository_batch'): plans.add(require(session,PlanFolder,source['folder_id']).plan_id)
            if request.endpoint=='save_projects':
                for project in data.get('projects',[]):
                    for plan in project.get('plans',[]):
                        if session.get(ProjectPlan,plan.get('id')): plans.add(plan['id'])
            if request.endpoint in ('delete_project','rename_project','rename_plan'):
                project_id=data.get('project_id') or data.get('id')
                if not project_id and (data.get('project') or data.get('old_name')):
                    from models import Project
                    project=session.query(Project).filter_by(name=data.get('project') or data.get('old_name')).first()
                    project_id=project.id if project else None
                plans.update(p.id for p in session.query(ProjectPlan).filter_by(project_id=project_id))
            if request.endpoint=='run_testcase' and not data.get('task_id'):
                for plan_id in plans: unlocked(session,plan_id)
            execution={'current_start','current_finish','current_stop','current_result','save_results','annotate_task_tc','run_testcase','single_update','current_task_settings'}
            if request.endpoint not in execution:
                for plan_id in plans: unlocked(session,plan_id)
        except Exception as e:
            session.rollback(); return jsonify(error=str(e)),getattr(e,'code',500)

    @app.teardown_request
    def release_plan_write(error):
        session=g.pop('plan_write_session',None)
        if session: session.close()

    def route(rule,methods,endpoint=None):
        def decorate(fn):
            @wraps(fn)
            def handle(**kwargs):
                session=request_session(runtime['DbSession'])
                try: return fn(session,request.get_json(silent=True) or {},**kwargs)
                except Exception as e:
                    session.rollback(); return jsonify(error=str(e)),getattr(e,'code',500)
                finally: session.close()
            name=endpoint or fn.__name__
            if name in app.view_functions: app.view_functions[name]=handle
            else: app.add_url_rule(rule,name,handle,methods=methods)
            return handle
        return decorate

    @route('/api/plans/<plan_id>/folders',['GET','POST'])
    def current_folders(s,data,plan_id):
        require(s,ProjectPlan,plan_id)
        if request.method=='GET': return jsonify([f.to_dict() for f in s.query(PlanFolder).filter_by(plan_id=plan_id).order_by(PlanFolder.position,PlanFolder.id)])
        f=create_folder(s,plan_id,data.get('name'),data.get('parent_id')); result=f.to_dict(); s.commit(); return jsonify(result),201

    @route('/api/folders/<folder_id>',['PATCH','DELETE'])
    def current_folder(s,data,folder_id):
        if request.method=='DELETE': return jsonify(status='ok',impact=delete_content(s,runtime['MAIN_PROGRAM_DIR'],data,folder=require(s,PlanFolder,folder_id)))
        result=change_folder(s,folder_id,data).to_dict(); s.commit(); return jsonify(result)

    @route('/api/plans/<plan_id>/folders/reorder',['POST'])
    def current_folder_reorder(s,data,plan_id):
        unlocked(s,plan_id); rows=siblings(s,plan_id,data.get('parent_id')); ids=data.get('folder_ids',data.get('ids',[]))
        if len(ids)!=len(set(ids)) or set(ids)!={f.id for f in rows}: raise StateError('Supply exactly the complete sibling collection')
        by_id={f.id:f for f in rows}; normalize([by_id[i] for i in ids]); s.commit(); return jsonify(status='ok')

    @route('/api/folders/<folder_id>/impact',['GET'])
    def current_folder_impact(s,data,folder_id): return jsonify(impact(s,folder=require(s,PlanFolder,folder_id)))

    @route('/api/testcases/<tc_id>/impact',['GET'])
    def current_testcase_impact(s,data,tc_id): return jsonify(impact(s,testcases=[require(s,TestCase,tc_id)]))

    @route('/api/testcases/<tc_id>',['DELETE'])
    def current_testcase_delete(s,data,tc_id): return jsonify(status='ok',impact=delete_content(s,runtime['MAIN_PROGRAM_DIR'],data,testcases=[require(s,TestCase,tc_id)]))

    @route('/api/testcases/<tc_id>',['PATCH'],endpoint='patch_testcase')
    def current_testcase_patch(s,data,tc_id):
        tc=require(s,TestCase,tc_id); unlocked(s,tc.plan_id)
        if 'tc_name' in data or 'display_name' in data:
            name=str(data.get('tc_name',data.get('display_name'))).strip()
            if not name: raise StateError('Testcase name is required')
            duplicate=s.query(TestCase).filter_by(plan_id=tc.plan_id,normalized_name=name.casefold()).first()
            if duplicate and duplicate.system_id!=tc_id: raise StateError('TC already exists',409)
            tc.display_name=name
        if any(k in data for k in ('folder_id','folder_path','category','custom_subfolder')): assign_folder(s,tc,resolve_folder(s,tc.plan_id,data))
        if 'selected' in data: tc.selected=bool(data['selected'])
        s.flush(); result=tc.to_dict(); s.commit(); return jsonify(result)

    @route('/api/plans/<plan_id>/testcases/move',['POST'],endpoint='move_plan_testcases')
    def current_move(s,data,plan_id):
        unlocked(s,plan_id); ids=data.get('testcase_ids',data.get('ids',[]))
        if not isinstance(ids,list) or not ids or len(ids)!=len(set(ids)): raise StateError('Select unique testcase IDs')
        rows=[require(s,TestCase,i) for i in ids]
        if any(t.plan_id!=plan_id for t in rows): raise StateError('Testcase belongs to another Plan')
        destination=dict(data)
        if not any(k in destination for k in ('folder_id','folder_path')): destination['folder_path']=data.get('target_key','Custom').replace('custom:','Custom/').replace('category:','')
        f=resolve_folder(s,plan_id,destination)
        relative=None
        if 'relative_to' in data or 'insertion' in data:
            if not isinstance(data.get('relative_to'),str) or data.get('insertion') not in ('before','after'):
                raise StateError('Supply a relative testcase and before/after insertion')
            relative=require(s,TestCase,data['relative_to'])
            if relative.system_id in ids or relative.plan_id!=plan_id or relative.folder_id!=f.id:
                raise StateError('Relative testcase must be another testcase in the destination Plan and folder')
        for tc in rows: assign_folder(s,tc,f)
        if relative:
            ordered=s.query(TestCase).filter(TestCase.plan_id==plan_id,TestCase.folder_id==f.id,TestCase.system_id.notin_(ids)).order_by(TestCase.position,TestCase.system_id).all()
            position=next(i for i,tc in enumerate(ordered) if tc.system_id==relative.system_id)+(data['insertion']=='after')
            ordered[position:position]=rows
            normalize(ordered)
        result=dict(status='ok',folder_id=f.id,moved=len(rows)); s.commit(); return jsonify(result)

    @route('/api/plans/<plan_id>/testcases/reorder',['POST'],endpoint='reorder_plan_testcases')
    def current_case_reorder(s,data,plan_id):
        unlocked(s,plan_id); folder=resolve_folder(s,plan_id,data)
        rows=s.query(TestCase).filter_by(plan_id=plan_id,folder_id=folder.id).all(); ids=data.get('testcase_ids',data.get('ids',data.get('order')))
        if not isinstance(ids,list): raise StateError('Supply testcase IDs as a list')
        if len(ids)!=len(set(ids)) or set(ids)!={r.system_id for r in rows}: raise StateError('Supply exactly the folder testcase collection')
        by_id={r.system_id:r for r in rows}; normalize([by_id[i] for i in ids]); s.commit(); return jsonify(status='ok')

    @route('/api/tasks/<task_id>/testcases/import',['POST'],endpoint='import_task_testcases')
    def current_scope(s,data,task_id):
        replace_scope(s,task_id,data.get('testcases',[])); s.commit(); return jsonify(status='ok')

    @route('/api/task_testcases/<task_id>/<tc_id>',['PATCH'],endpoint='patch_task_testcase')
    def current_scope_patch(s,data,task_id,tc_id):
        task=require(s,Task,task_id); unlocked(s,task.plan_id)
        row=s.query(TaskTestCase).filter_by(task_id=task_id,testcase_id=tc_id).first()
        if row is None: raise StateError('Task testcase not found',404)
        if 'selected' in data: row.selected=bool(data['selected'])
        s.commit(); return jsonify(status='ok')

    @route('/api/tasks/<task_id>/testcases/<tc_id>/status',['PATCH'])
    def current_manual_status(s,data,task_id,tc_id):
        result=set_manual_status(s,task_id,tc_id,data); s.commit(); return jsonify(result)

    @route('/api/tasks/<task_id>/testcases/<tc_id>/logs',['GET'])
    def current_case_logs(s,data,task_id,tc_id):
        task,row,tc=live_task_case(s,task_id,tc_id)
        return jsonify(task_case_dict(row,tc))

    @route('/api/tasks/<task_id>/summary',['GET'])
    def current_summary(s,data,task_id): return jsonify(summary(s,task_id,runtime['MAIN_PROGRAM_DIR']))

    @route('/api/tasks/<task_id>/results',['GET'],endpoint='load_task_results')
    def current_results(s,data,task_id): return jsonify(summary(s,task_id,runtime['MAIN_PROGRAM_DIR']))

    @route('/api/tasks/<task_id>/execution',['GET'])
    def current_execution(s,data,task_id):
        task=require(s,Task,task_id)
        require(s,ProjectPlan,task.plan_id)
        active=bool(task.execution_active)
        session_id=next((sid for sid,run in runtime['run_sessions'].items() if run.get('task_id')==task_id and run.get('thread') and run['thread'].is_alive()),None) if active else None
        return jsonify(task_id=task.id,execution_active=active,execution_token=task.execution_token if active else None,session_id=session_id,
                       testcase_ids=json.loads(task.execution_selection or '[]'),stop_requested=bool(task.execution_stop_requested))

    @route('/api/tasks/<task_id>/settings',['GET','PUT','POST'])
    def current_task_settings(s,data,task_id):
        task=require(s,Task,task_id)
        if request.method=='GET': return jsonify(te.normalize(task.environment_config))
        settings=te.save(task,data,s); s.commit(); return jsonify(settings)

    @route('/api/tasks/<task_id>/execution/start',['POST'])
    def current_start(s,data,task_id):
        if s.query(Task).filter_by(execution_active=True).first():
            raise StateError('Another Task is executing. Finish or stop it before starting a new Task.',409)
        ids=data.get('selected_testcase_ids',data.get('testcase_ids'))
        if isinstance(ids,list):
            for identity in ids:
                tc=require(s,TestCase,identity)
                if tc.script_kind!='single': raise StateError('Step-based Test Cases are retired. Import a single .py through the Repository.',410)
                import single_case
                definition=single_case.definition(runtime['MAIN_PROGRAM_DIR'],tc)
                single_case.validate_settings(definition['metadata'],definition['settings'])
        try: te.configuration(require(s,Task,task_id).environment_config,require_host=True)
        except ValueError as error: raise StateError(str(error))
        token=start_execution(s,task_id,data.get('selected_testcase_ids',data.get('testcase_ids'))); s.commit(); return jsonify(status='ok',task_id=task_id,execution_token=token)

    @route('/api/tasks/<task_id>/execution/result',['POST'])
    def current_result(s,data,task_id):
        save_result(s,task_id,data); s.commit(); return jsonify(status='ok')

    def terminal(s,task_id,data):
        check_execution_token(require(s,Task,task_id),data.get('execution_token'))
        finish_execution(s,task_id,data.get('execution_token')); s.commit(); return jsonify(status='ok')

    @route('/api/tasks/<task_id>/execution/finish',['POST'])
    def current_finish(s,data,task_id): return terminal(s,task_id,data)

    @route('/api/tasks/<task_id>/execution/stop',['POST'])
    def current_stop(s,data,task_id):
        task=require(s,Task,task_id)
        check_execution_token(task,data.get('execution_token'))
        task.execution_stop_requested=True
        active=[r for r in runtime['run_sessions'].values() if r.get('task_id')==task_id and r.get('thread') and r['thread'].is_alive()]
        for run in active:
            run['stop_requested']=True; run['input_queue'].put('__STOP__')
        if task.execution_worker_id:
            s.commit(); return jsonify(status='stopping')
        return terminal(s,task_id,data)

    @route('/api/results/save',['POST'],endpoint='save_results')
    def current_save(s,data):
        task_id=data.get('task_id'); require(s,Task,task_id)
        for case in data.get('testcases',[]): save_result(s,task_id,dict(case,execution_token=data.get('execution_token')))
        s.commit(); return jsonify(status='ok')

    @route('/api/task_tc/annotate',['POST'],endpoint='annotate_task_tc')
    def current_annotate(s,data):
        task=require(s,Task,data.get('task_id'))
        row=s.query(TaskTestCase).filter_by(task_id=task.id,testcase_id=data.get('testcase_id')).first()
        if row is None: raise StateError('Task testcase not found',404)
        if 'status' in data: save_result(s,task.id,data)
        if 'bug_id' in data: row.bug_id=data['bug_id']
        s.commit(); return jsonify(status='ok')

    @route('/api/delete_tc',['POST'],endpoint='delete_tc')
    def current_legacy_delete(s,data):
        plan_id=data.get('plan_id'); unlocked(s,plan_id); rows=[]
        for item in data.get('tcs',[]):
            tc=s.get(TestCase,item['id']) if item.get('id') else s.query(TestCase).filter_by(plan_id=plan_id,normalized_name=str(item.get('testcase','')).strip().casefold()).first()
            if tc is None: raise StateError('Testcase not found',404)
            if tc.plan_id!=plan_id: raise StateError('Testcase belongs to another Plan')
            rows.append(tc)
        if not rows: raise StateError('Select at least one testcase')
        return jsonify(status='ok',impact=delete_content(s,runtime['MAIN_PROGRAM_DIR'],data,testcases=rows))

    @route('/api/projects',['POST'],endpoint='save_projects')
    def current_bulk_projects(s,data):
        for project in data.get('projects',[]):
            for plan_data in project.get('plans',[]):
                plan=s.get(ProjectPlan,plan_data.get('id'))
                if plan is None:
                    from models import Project
                    owner=require(s,Project,project.get('id'))
                    plan=ProjectPlan(id=plan_data.get('id') or str(uuid.uuid4()),project_id=owner.id,name=plan_data.get('name','Plan')); s.add(plan); s.flush()
                unlocked(s,plan.id)
                for name in plan_data.get('custom_subfolders',[]): resolve_folder(s,plan.id,{'folder_path':'Custom/'+name})
                if project.get('id') and plan.project_id!=project['id']: raise StateError('Plan belongs to another Project')
                for item in plan_data.get('testcases',[]):
                    tc=require(s,TestCase,item.get('id'))
                    if tc.plan_id!=plan.id: raise StateError('Testcase belongs to another Plan')
                    if 'selected' in item: tc.selected=bool(item['selected'])
                    if item.get('folder_id'): assign_folder(s,tc,resolve_folder(s,plan.id,item))
                    elif 'custom_subfolder' in item and item.get('custom_subfolder'): assign_folder(s,tc,resolve_folder(s,plan.id,{'folder_path':'Custom/'+item['custom_subfolder']}))
                for item in plan_data.get('tasks',[]):
                    task=s.get(Task,item.get('id'))
                    if task is None:
                        task=Task(id=item.get('id') or str(uuid.uuid4()),plan_id=plan.id,name=item.get('name','Task')); s.add(task); s.flush()
                    if task.plan_id!=plan.id: raise StateError('Task belongs to another Plan')
                    if 'testcases' in item: replace_scope(s,task.id,item['testcases'])
                    import task_management
                    if 'name' in item: task.name=task_management.validate_name(item['name'])
                    if 'setup' in item: task.task_metadata=json.dumps(task_management.merge_setup(task.task_metadata,item['setup']))
                    if 'environment_config' in item: te.save(task,item['environment_config'],s)
        s.commit(); return jsonify(status='ok')
