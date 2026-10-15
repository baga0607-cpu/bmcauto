"""Repository imports and independent Plan scripts. Reading metadata never runs code."""
import ast
import inspect
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
                    return jsonify(error=str(error)), getattr(error, 'code', 500)
                finally:
                    session.close()
            app.add_url_rule(rule, fn.__name__, handle, methods=methods)
            return fn
        return decorate

    @route('/api/repository/testcases', ['GET'])
    def repository_list(s, data):
        return jsonify([dict(id=row.id, name=row.name, source_version=row.source_version,
                             folder_id=(s.get(RepositoryFolderCase,row.id).folder_id if s.get(RepositoryFolderCase,row.id) else None), metadata=metadata(row.source_text))
                        for row in s.query(RepositoryCase).order_by(RepositoryCase.source_version.desc())])

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

    @route('/api/repository/testcases/<repository_id>/folder', ['PUT'])
    def repository_case_move(s,data,repository_id):
        ps.require(s,RepositoryCase,repository_id)
        member=s.get(RepositoryFolderCase,repository_id)
        if data.get('folder_id'):
            f=ps.require(s,RepositoryFolder,data['folder_id'])
            if member:member.folder_id=f.id
            else:s.add(RepositoryFolderCase(repository_id=repository_id,folder_id=f.id))
        elif member:member.folder_id=rt.ROOT
        s.commit();return jsonify(status='ok')

    def copy_case(s,row,plan_id,folder,paths):
        identity=str(uuid.uuid4());meta=metadata(row.source_text)
        tc=TestCase(system_id=identity,family_id=row.id,display_name=row.name,plan_id=plan_id,
                    script_path=f'testcase_database.scripts.{identity}',script_kind='single',repository_id=row.id,
                    source_version=row.source_version,settings_json=json.dumps({k:v['default'] for k,v in meta.get('parameters',{}).items()}),settings_revision=0)
        s.add(tc);s.flush();ps.assign_folder(s,tc,folder)
        path=script_file(runtime['MAIN_PROGRAM_DIR'],tc)
        path.parent.mkdir(parents=True,exist_ok=False);paths.append(path)
        path.write_text(row.source_text,encoding='utf-8')
        return tc

    def remove_copies(paths):
        for path in reversed(paths):
            path.unlink(missing_ok=True);path.parent.rmdir()

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
