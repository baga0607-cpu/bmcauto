"""Repository imports and independent Plan scripts. Reading metadata never runs code."""
import ast
import inspect
import hashlib
import json
import math
import sys
import uuid
from types import ModuleType
from datetime import datetime, timezone, timedelta
from pathlib import Path
from flask import jsonify, request
from models import RepositoryCase, RepositoryFolder, RepositoryFolderCase, TestCase, TaskTestCase
import plan_state as ps
import repository_tree as rt
import case_order as co


def metadata(source):
    tree = ast.parse(source)
    declarations = [node for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'TEST_CASE' for t in node.targets)]
    if len(declarations) != 1:
        raise ps.StateError('Declare one literal TEST_CASE dictionary')
    try:
        meta = ast.literal_eval(declarations[0].value)
        json.dumps(meta, allow_nan=False)
    except (ValueError, TypeError) as error:
        raise ps.StateError('TEST_CASE must contain literal JSON-compatible values') from error
    if not isinstance(meta, dict) or not isinstance(meta.get('name'), str) or not meta['name'].strip():
        raise ps.StateError('TEST_CASE.name must be nonempty text')
    if len(meta['name']) > 255:
        raise ps.StateError('Test Case name is too long')
    if not isinstance(meta.get('description', ''), str):
        raise ps.StateError('TEST_CASE.description must be text')
    if 'automation' in meta and meta['automation'] not in ('automatic','semi_automatic'):
        raise ps.StateError('TEST_CASE.automation must be automatic or semi_automatic.')
    meta.setdefault('automation','unclassified')
    parameters = meta.get('parameters', {})
    if not isinstance(parameters, dict):
        raise ps.StateError('TEST_CASE.parameters must be a dictionary')
    for key, spec in parameters.items():
        if not isinstance(key, str) or not isinstance(spec, dict) or spec.get('type') not in ('string', 'integer', 'number', 'boolean'):
            raise ps.StateError('Each parameter needs a string key and a supported type')
        if 'default' not in spec or not isinstance(spec.get('label', key), str):
            raise ps.StateError(f'Parameter {key} needs a default value and text label')
    validate_settings(meta, {key: spec['default'] for key, spec in parameters.items()})
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'execute']
    if len(functions) != 1:
        raise ps.StateError('Define one synchronous execute(client, context=None, preset=None) function')
    args = functions[0].args
    names = [arg.arg for arg in args.posonlyargs + args.args]
    if not names or names[0] != 'client' or 'context' not in names or 'preset' not in names:
        raise ps.StateError('execute must accept client, context and preset')
    # Required extra arguments would make the declared runtime interface unusable.
    required = names[:len(names) - len(args.defaults)]
    if any(name not in ('client', 'context', 'preset') for name in required) or any(default is None for default in args.kw_defaults):
        raise ps.StateError('execute has unsupported required arguments')
    return meta


def validate_settings(meta, settings):
    specs = meta.get('parameters', {})
    if not isinstance(settings, dict) or set(settings) != set(specs):
        raise ps.StateError('Supply exactly the declared editable parameters')
    for key, value in settings.items():
        kind = specs[key]['type']
        valid = (kind == 'string' and isinstance(value, str) or
                 kind == 'boolean' and isinstance(value, bool) or
                 kind == 'integer' and type(value) is int or
                 kind == 'number' and type(value) in (int, float) and math.isfinite(value))
        if not valid:
            raise ps.StateError(f'Invalid value for parameter {key}: expected {kind}')
    return settings


def script_file(root, tc):
    base = Path(root).resolve()
    path = base.joinpath(*tc.script_path.split('.'), 'case.py').resolve()
    if not path.is_relative_to(base):
        raise ps.StateError('Invalid Plan script path')
    return path


def automation_for_case(root, tc):
    if not root or tc.script_kind != 'single': return 'unclassified'
    try: return metadata(script_file(root,tc).read_text(encoding='utf-8'))['automation']
    except (OSError, UnicodeError, SyntaxError, ps.StateError): return 'unclassified'

def parameter_count_for_case(root, tc):
    if not root or tc.script_kind != 'single': return 0
    try: return len(metadata(script_file(root,tc).read_text(encoding='utf-8')).get('parameters',{}))
    except (OSError, UnicodeError, SyntaxError, ps.StateError): return 0

def definition(root, tc):
    source = script_file(root, tc).read_text(encoding='utf-8')
    meta = metadata(source)
    return dict(**tc.to_dict(), source=source, metadata=meta, settings=json.loads(tc.settings_json or '{}'))


def execute_script(root, module_path, client, context, preset):
    path = Path(root).joinpath(*module_path.split('.')).with_suffix('.py').resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ps.StateError('Invalid script path')
    # Read current source on every execution; import caches cannot hide a Plan edit.
    module = ModuleType(module_path)
    module.__file__ = str(path)
    module.__package__ = module_path.rsplit('.', 1)[0]
    previous = sys.modules.get(module_path)
    sys.modules[module_path] = module
    try:
        exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), module.__dict__)
        inspect.signature(module.execute).bind(client, context=context, preset=preset)
        module.execute(client, context=context, preset=preset)
    finally:
        if previous is None:
            sys.modules.pop(module_path, None)
        else:
            sys.modules[module_path] = previous


def register(app, runtime):
    def route(rule, methods):
        def decorate(fn):
            def handle(**kwargs):
                session = ps.request_session(runtime['DbSession'])
                try:
                    if fn.__name__.startswith('repository_'):
                        ps.begin_write(session);rt.ensure(session)
                    result=fn(session, request.get_json(silent=True) or {}, **kwargs)
                    session.commit()
                    return result
                except (SyntaxError, UnicodeError) as error:
                    session.rollback()
                    return jsonify(error=f'Invalid Python source: {error}'), 400
                except Exception as error:
                    session.rollback()
                    return jsonify(error=str(error)), error.code if isinstance(error, ps.StateError) else 500
                finally:
                    session.close()
            app.add_url_rule(rule, fn.__name__, handle, methods=methods)
            return fn
        return decorate

    @route('/api/repository/testcases', ['GET'])
    def repository_list(s, data):
        return jsonify(co.arrange(s,'repository',[dict(id=row.id, name=row.name, source_version=row.source_version,
                             folder_id=(s.get(RepositoryFolderCase,row.id).folder_id if s.get(RepositoryFolderCase,row.id) else None), metadata=metadata(row.source_text))
                        for row in s.query(RepositoryCase).order_by(RepositoryCase.source_version.desc())]))

    @route('/api/repository/testcases', ['POST'])
    def repository_import(s, data):
        source = data.get('source')
        if not isinstance(source, str) or not source.strip():
            raise ps.StateError('Provide Python source from a .py file')
        meta = metadata(source)
        imported_at = datetime.now(timezone.utc)
        version = imported_at.isoformat(timespec='microseconds')
        while s.query(RepositoryCase).filter_by(source_version=version).first():
            imported_at += timedelta(microseconds=1)
            version = imported_at.isoformat(timespec='microseconds')
        row = RepositoryCase(id=str(uuid.uuid4()), name=meta['name'].strip(), source_version=version, source_text=source)
        s.add(row); s.flush()
        folder=ps.require(s,RepositoryFolder,data.get('folder_id') or rt.ROOT)
        s.add(RepositoryFolderCase(repository_id=row.id,folder_id=folder.id))
        s.commit()
        return jsonify(id=row.id, name=row.name, source_version=row.source_version), 201

    @route('/api/repository/testcases/<repository_id>', ['GET'])
    def repository_read(s, data, repository_id):
        row=ps.require(s,RepositoryCase,repository_id)
        return jsonify(id=row.id,name=row.name,source_version=row.source_version,source=row.source_text,metadata=metadata(row.source_text))

    @route('/api/repository/testcases/<repository_id>', ['DELETE'])
    def repository_remove(s, data, repository_id):
        row = ps.require(s, RepositoryCase, repository_id)
        if data.get('confirm') is not True:
            raise ps.StateError('Confirm removal of this Repository Test Case.')
        # Plan files/settings are independent copies, not children of this row.
        s.query(RepositoryFolderCase).filter_by(repository_id=row.id).delete()
        s.delete(row)
        s.commit()
        return jsonify(status='ok', id=repository_id)

    @route('/api/repository/inspect', ['POST'])
    def repository_inspect(s, data):
        if not isinstance(data.get('source'), str):
            raise ps.StateError('Provide Python source')
        return jsonify(metadata=metadata(data['source']))

    @route('/api/repository/folders', ['GET'])
    def repository_folders(s,data):return jsonify(rt.records(s))

    @route('/api/repository/folders', ['POST'])
    def repository_folder_create(s,data):return jsonify(rt.create(s,data)),201

    @route('/api/repository/folders/<folder_id>', ['PATCH','DELETE'])
    def repository_folder_modify(s,data,folder_id):
        if request.method=='DELETE':return jsonify(rt.remove(s,folder_id,data))
        return jsonify(rt.change(s,folder_id,data))

    @route('/api/repository/batch', ['POST'])
    def repository_batch(s,data):return jsonify(rt.batch(s,data))

    @route('/api/repository/folders/<folder_id>/resort', ['POST'])
    def repository_resort(s,data,folder_id):
        ps.require(s,RepositoryFolder,folder_id)
        co.reset(s,'repository',folder_id)
        return jsonify(status='ok')

    @route('/api/repository/testcases/<repository_id>/folder', ['PUT'])
    def repository_case_move(s,data,repository_id):
        rt.move_cases(s,[repository_id],data)
        s.commit();return jsonify(status='ok')

    def copy_case(s,row,plan_id,folder,paths):
        identity=str(uuid.uuid4());meta=metadata(row.source_text)
        tc=TestCase(system_id=identity,family_id=row.id or str(uuid.uuid4()),display_name=row.name,plan_id=plan_id,
                    script_path=f'testcase_database.scripts.{identity}',script_kind='single',repository_id=row.id,
                    source_version=row.source_version,settings_json=json.dumps({k:v['default'] for k,v in meta.get('parameters',{}).items()}),settings_revision=0)
        if folder is None: tc.position=s.query(TestCase).filter_by(plan_id=plan_id,folder_id=None).count()
        s.add(tc);s.flush();ps.assign_folder(s,tc,folder)
        path=script_file(runtime['MAIN_PROGRAM_DIR'],tc)
        path.parent.mkdir(parents=True,exist_ok=False);paths.append(path)
        path.write_text(row.source_text,encoding='utf-8')
        return tc

    def remove_copies(paths):
        for path in reversed(paths):
            path.unlink(missing_ok=True);path.parent.rmdir()

    @route('/api/plans/<plan_id>/testcases/import-python', ['POST'])
    def plan_import_python(s,data,plan_id):
        ps.unlocked(s,plan_id)
        ps.require(s,ps.ProjectPlan,plan_id).folders_migrated=True
        source=data.get('source')
        if not isinstance(source,str) or not source.strip(): raise ps.StateError('Provide Python source from a .py file')
        meta=metadata(source); name=meta['name'].strip()
        if s.query(TestCase).filter_by(plan_id=plan_id,normalized_name=name.casefold()).first():
            raise ps.StateError('A Test Case with this name already exists in the Plan',409)
        folder=ps.resolve_folder(s,plan_id,data) if data.get('folder_id') else None
        row=RepositoryCase(name=name,source_text=source,source_version=datetime.now(timezone.utc).isoformat(timespec='microseconds'))
        paths=[]
        try:
            tc=copy_case(s,row,plan_id,folder,paths);s.commit()
        except Exception:
            s.rollback();remove_copies(paths);raise
        return jsonify(tc.to_dict()),201

    @route('/api/plans/<plan_id>/repository/testcases', ['POST'])
    def repository_add_to_plan(s,data,plan_id):
        ps.unlocked(s,plan_id);row=ps.require(s,RepositoryCase,data.get('repository_id'))
        if s.query(TestCase).filter_by(plan_id=plan_id,normalized_name=row.name.casefold()).first():
            raise ps.StateError('A Test Case with this name already exists in the Plan',409)
        folder=ps.resolve_folder(s,plan_id,data);paths=[]
        try:
            tc=copy_case(s,row,plan_id,folder,paths);s.commit()
        except Exception:
            s.rollback();remove_copies(paths);raise
        return jsonify(tc.to_dict()),201

    @route('/api/plans/<plan_id>/repository/folders/<folder_id>', ['POST'])
    def repository_folder_add_to_plan(s,data,plan_id,folder_id):
        ps.unlocked(s,plan_id);source_folder=ps.require(s,RepositoryFolder,folder_id)
        rows=s.query(RepositoryCase).join(RepositoryFolderCase,RepositoryFolderCase.repository_id==RepositoryCase.id).filter(RepositoryFolderCase.folder_id.in_(rt.subtree(s,folder_id))).order_by(RepositoryCase.source_version.desc()).all()
        names={tc.normalized_name for tc in s.query(TestCase).filter_by(plan_id=plan_id)}
        added=[];skipped=[];paths=[]
        try:
            destinations={}
            base=rt.path(s,folder_id)
            for identity in rt.subtree(s,folder_id):
                segments=rt.path(s,identity)[len(base)-1:]
                destinations[identity]=ps.resolve_folder(s,plan_id,{'folder_path':segments})
            folder=destinations[folder_id]
            for row in rows:
                if row.name.casefold() in names:
                    skipped.append(dict(id=row.id,name=row.name));continue
                names.add(row.name.casefold());added.append(copy_case(s,row,plan_id,destinations[s.get(RepositoryFolderCase,row.id).folder_id],paths))
            s.commit()
        except Exception:
            s.rollback();remove_copies(paths);raise
        return jsonify(folder_id=folder.id,folder_name=folder.name,added=[tc.to_dict() for tc in added],skipped=skipped),201

    @route('/api/plans/<plan_id>/import-cases', ['POST'])
    def import_cases(s,data,plan_id):
        ps.unlocked(s,plan_id)
        destination=ps.require(s,ps.ProjectPlan,plan_id)
        target=ps.require(s,ps.PlanFolder,data['target_folder_id']) if data.get('target_folder_id') else None
        if target and target.plan_id!=plan_id: raise ps.StateError('Destination belongs to another Plan')
        kind=data.get('kind'); source_type=data.get('source_type'); identity=data.get('id')
        if kind not in ('case','folder') or source_type not in ('repository','plan'):
            raise ps.StateError('Choose a case or folder source')
        anchor=None
        if 'relative_to' in data or 'insertion' in data:
            anchor=ps.require(s,TestCase,data.get('relative_to'))
            if kind!='case' or data.get('insertion') not in ('before','after') or anchor.plan_id!=plan_id or anchor.folder_id!=(target.id if target else None):
                raise ps.StateError('Choose a Test Case in the destination folder and before/after insertion.')
        source_plan=data.get('source_plan_id')
        if source_type=='plan':
            ps.require(s,ps.ProjectPlan,source_plan)
            if source_plan==plan_id: raise ps.StateError('Choose another Plan as the source')
        decisions=data.get('decisions') or {}
        if not isinstance(decisions,dict): raise ps.StateError('Invalid conflict decisions')
        incoming=[]
        def read_item(row):
            if source_type=='repository':
                meta=metadata(row.source_text)
                item=dict(id=row.id,name=row.name,source=row.source_text,version=row.source_version,
                          settings={k:v['default'] for k,v in meta.get('parameters',{}).items()},repository_id=row.id,family_id=row.id)
            else:
                if row.plan_id!=source_plan: raise ps.StateError('Case belongs to another source Plan')
                if row.script_kind!='single': raise ps.StateError('Only single-file Test Cases can be imported')
                definition_data=definition(runtime['MAIN_PROGRAM_DIR'],row);meta=definition_data['metadata']
                item=dict(id=row.system_id,name=row.display_name,source=definition_data['source'],version=row.source_version,
                          settings=validate_settings(meta,definition_data['settings']),repository_id=row.repository_id,family_id=row.family_id)
            item['canonical']=meta['name'].strip().casefold();incoming.append(item);return item
        def read_folder(identity):
            if source_type=='repository':
                folder=ps.require(s,RepositoryFolder,identity)
                children=[n.folder_id for n in rt.siblings(s,identity)]
                rows=s.query(RepositoryCase).join(RepositoryFolderCase,RepositoryFolderCase.repository_id==RepositoryCase.id).filter(RepositoryFolderCase.folder_id==identity).order_by(RepositoryCase.source_version.desc(),RepositoryCase.id).all()
            else:
                folder=ps.require(s,ps.PlanFolder,identity)
                if folder.plan_id!=source_plan: raise ps.StateError('Folder belongs to another source Plan')
                children=[f.id for f in ps.siblings(s,source_plan,identity)]
                rows=s.query(TestCase).filter_by(plan_id=source_plan,folder_id=identity).order_by(TestCase.position,TestCase.system_id).all()
            return dict(name=folder.name,items=[read_item(row) for row in rows],children=[read_folder(child) for child in children])
        tree=read_folder(identity) if kind=='folder' else None
        if kind=='case':read_item(ps.require(s,RepositoryCase if source_type=='repository' else TestCase,identity))
        def fingerprint(source,settings,version):
            return hashlib.sha256(json.dumps([source,settings,version],sort_keys=True).encode()).hexdigest()
        existing=[];actual={}
        for tc in s.query(TestCase).filter_by(plan_id=plan_id).order_by(TestCase.system_id):
            try: source=script_file(runtime['MAIN_PROGRAM_DIR'],tc).read_text(encoding='utf-8');canonical=metadata(source)['name'].strip().casefold()
            except (OSError,UnicodeError,SyntaxError,ps.StateError): source='';canonical=tc.normalized_name
            existing.append(dict(id=tc.system_id,name=tc.display_name,canonical=canonical,source_version=tc.source_version,
                                 token=fingerprint(source,json.loads(tc.settings_json or '{}'),tc.source_version)))
            actual[tc.system_id]=tc
        conflicts=[];used_names={x['name'].casefold() for x in existing}
        for item in incoming:
            matches=[x for x in existing if x['canonical']==item['canonical'] or x['name'].casefold()==item['name'].casefold()]
            same=[x for x in matches if x['source_version']==item['version']]
            candidates=same or matches;decision=decisions.get(item['id'],{})
            item['action']='new'
            if candidates:
                valid_target=next((x for x in candidates if x['id']==decision.get('target_id') and x['token']==decision.get('target_token')),None)
                valid=valid_target and decision.get('action') in (('overwrite','skip') if same else ('overwrite','coexist','skip'))
                if not valid:
                    conflicts.append(dict(id=item['id'],name=item['name'],source_version=item['version'],same_version=bool(same),targets=candidates));continue
                item['action']=decision['action'];item['target_id']=valid_target['id']
                if item['action']=='skip':continue
            if item['action']=='overwrite':
                descriptor=next(x for x in existing if x['id']==item['target_id'])
            else:
                name=item['name'];item['display_name']=name
                descriptor=dict(id='incoming:'+item['id'],name=name);existing.append(descriptor)
            descriptor.update(canonical=item['canonical'],source_version=item['version'],token=fingerprint(item['source'],item['settings'],item['version']))
        if conflicts:return jsonify(error='Resolve Test Case conflicts before importing.',conflicts=conflicts),409
        paths=[];originals={};added=[];updated=[];skipped=[]
        def apply_item(item,folder):
            if item['action']=='skip':skipped.append(item['name']);return
            if item['action']=='overwrite':
                tc=actual[item['target_id']];path=script_file(runtime['MAIN_PROGRAM_DIR'],tc)
                originals.setdefault(path,path.read_text(encoding='utf-8'))
                tc.settings_revision=(tc.settings_revision or 0)+1
                for membership in s.query(TaskTestCase).filter_by(testcase_id=tc.system_id):
                    if membership.executed_at or membership.result_json or membership.manual_override_json or membership.status in ('Passed','Failed','Block'):
                        membership.needs_retest=True
                path.write_text(item['source'],encoding='utf-8');updated.append(tc)
            else:
                row=RepositoryCase(name=item['display_name'],source_text=item['source'],source_version=item['version'])
                tc=copy_case(s,row,plan_id,folder,paths);actual['incoming:'+item['id']]=tc;added.append(tc)
            tc.repository_id=item['repository_id'];tc.family_id=item['family_id'];tc.source_version=item['version']
            tc.settings_json=json.dumps(item['settings'],ensure_ascii=False)
        def apply_folder(node,parent):
            parent_id=parent.id if parent else None
            folder=next((f for f in ps.siblings(s,plan_id,parent_id) if f.normalized_name==node['name'].casefold()),None)
            if folder is None:folder=ps.create_folder(s,plan_id,node['name'],parent_id)
            for item in node['items']:apply_item(item,folder)
            for child in node['children']:apply_folder(child,folder)
        try:
            destination.folders_migrated=True
            if tree:apply_folder(tree,target)
            else:apply_item(incoming[0],target)
            if anchor and added:
                added_ids=[tc.system_id for tc in added]
                ordered=co.plan_rows(s,plan_id,s.query(TestCase).filter(TestCase.plan_id==plan_id,TestCase.folder_id==anchor.folder_id,TestCase.system_id.notin_(added_ids)).all())
                index=next(i for i,tc in enumerate(ordered) if tc.system_id==anchor.system_id)+(data['insertion']=='after')
                ordered[index:index]=added
                ps.normalize(ordered);co.save(s,'plan:'+plan_id,anchor.folder_id,[tc.system_id for tc in ordered])
            s.commit()
        except Exception:
            s.rollback()
            for path,source in originals.items():path.write_text(source,encoding='utf-8')
            remove_copies(paths);raise
        return jsonify(added=[tc.to_dict() for tc in added],updated=[tc.to_dict() for tc in updated],skipped=skipped),201

    @route('/api/plans/<plan_id>/testcases/<tc_id>/definition', ['GET'])
    def single_definition(s, data, plan_id, tc_id):
        tc = ps.require(s, TestCase, tc_id)
        if tc.plan_id != plan_id or tc.script_kind != 'single':
            raise ps.StateError('Single-file Plan Test Case not found', 404)
        result = definition(runtime['MAIN_PROGRAM_DIR'], tc)
        result['editing_locked'] = bool(s.query(TaskTestCase).filter_by(testcase_id=tc_id, status='Running').first())
        return jsonify(result)

    @route('/api/plans/<plan_id>/testcases/<tc_id>/definition', ['PUT'])
    def single_update(s, data, plan_id, tc_id):
        tc = ps.require(s, TestCase, tc_id)
        if tc.plan_id != plan_id or tc.script_kind != 'single':
            raise ps.StateError('Single-file Plan Test Case not found', 404)
        if s.query(TaskTestCase).filter_by(testcase_id=tc_id, status='Running').first():
            raise ps.StateError('This Test Case is running. Stop or finish execution before editing.', 409)
        if data.get('settings_revision') != (tc.settings_revision or 0):
            raise ps.StateError('The Plan Test Case changed. Reload before saving.', 409)
        path = script_file(runtime['MAIN_PROGRAM_DIR'], tc)
        original = path.read_text(encoding='utf-8')
        source = data.get('source', original)
        if not isinstance(source, str):
            raise ps.StateError('Python source must be text')
        meta = metadata(source)
        if meta['automation'] != metadata(original)['automation']:
            raise ps.StateError('Automation classification belongs to the source method. Import a new Repository version to change it.')
        settings = validate_settings(meta, data.get('settings', json.loads(tc.settings_json or '{}')))
        changed = source != original or settings != json.loads(tc.settings_json or '{}')
        if changed:
            tc.settings_json = json.dumps(settings, ensure_ascii=False)
            tc.settings_revision = (tc.settings_revision or 0) + 1
            for membership in s.query(TaskTestCase).filter_by(testcase_id=tc_id):
                if membership.executed_at or membership.result_json or membership.manual_override_json or membership.status in ('Passed', 'Failed'):
                    membership.needs_retest = True
            try:
                path.write_text(source, encoding='utf-8')
                s.commit()
            except Exception:
                path.write_text(original, encoding='utf-8')
                raise
        return jsonify(definition(runtime['MAIN_PROGRAM_DIR'], tc))
