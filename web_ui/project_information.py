"""Project requirements, independent of executable Plan/Task definitions.

The versioned document is also the future workbook import boundary. Preserve
source wording, item order and per-SKU values; never infer test parameters.
"""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from flask import jsonify, request
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from models import Project, ProjectInformation
from plan_state import request_session

TEMPLATE = json.loads(Path(__file__).with_name('project_information_template.json').read_text(encoding='utf-8'))
METADATA = ('product_name', 'author', 'document_title', 'document_version', 'description')
SOURCE = ('filename', 'requirement_sheet', 'comparison_sheet', 'imported_at', 'sha256')


def blank_information():
    result = copy.deepcopy(TEMPLATE)
    result.update(metadata={key: '' for key in METADATA},
                  source={key: '' for key in SOURCE}, skus=[])
    return result


def validate_document(doc):
    def text(value, limit=12000):
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError('Information fields must be text within the allowed length.')
        return value

    if not isinstance(doc, dict) or doc.get('schema_version') != 1:
        raise ValueError('Unsupported project information schema.')
    result = {'schema_version': 1}
    for key, fields in [('metadata', METADATA), ('source', SOURCE)]:
        obj = doc.get(key, {})
        if not isinstance(obj, dict) or set(obj) - set(fields):
            raise ValueError('Invalid project information fields.')
        result[key] = {field: text(obj.get(field, '')) for field in fields}
    skus = doc.get('skus', [])
    if not isinstance(skus, list) or len(skus) > 32:
        raise ValueError('At most 32 SKUs are supported.')
    result['skus'] = []
    sku_ids, sku_names = set(), set()
    for sku in skus:
        if not isinstance(sku, dict):
            raise ValueError('Invalid SKU.')
        sid, name = text(sku.get('id'), 100), text(sku.get('name'), 200).strip()
        if not sid or not name or sid in sku_ids or name.casefold() in sku_names:
            raise ValueError('SKU IDs and names must be nonempty and unique.')
        sku_ids.add(sid); sku_names.add(name.casefold())
        result['skus'].append({'id': sid, 'name': name})
    categories = doc.get('categories')
    if not isinstance(categories, list) or not 1 <= len(categories) <= 100:
        raise ValueError('Provide between 1 and 100 requirement categories.')
    result['categories'] = []
    category_ids, item_ids = set(), set()
    for category in categories:
        if not isinstance(category, dict):
            raise ValueError('Invalid category.')
        cid, name = text(category.get('id'), 100), text(category.get('name'), 300)
        if not cid or not name.strip() or cid in category_ids:
            raise ValueError('Category IDs must be unique and names must be nonempty.')
        category_ids.add(cid)
        items = category.get('items')
        if not isinstance(items, list):
            raise ValueError('Category items must be a list.')
        clean = {'id': cid, 'name': name, 'items': []}
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Invalid requirement item.')
            iid = text(item.get('id'), 100)
            if not iid or iid in item_ids or len(item_ids) >= 2000:
                raise ValueError('Requirement item IDs must be unique; at most 2000 items are supported.')
            item_ids.add(iid)
            entry = {key: text(item.get(key, '')) for key in ('name', 'guidance', 'target', 'remarks', 'source_ref')}
            if not entry['name'].strip() or not isinstance(item.get('heading', False), bool):
                raise ValueError('Invalid requirement name or heading.')
            entry.update(id=iid, heading=item.get('heading', False))
            values = item.get('sku_values', {})
            if not isinstance(values, dict) or set(values) - sku_ids:
                raise ValueError('Requirement references an unknown SKU.')
            entry['sku_values'] = {sid: text(value) for sid, value in values.items()}
            clean['items'].append(entry)
        result['categories'].append(clean)
    return result


def register(app, runtime):
    @app.route('/api/projects/import/preview', methods=['POST'])
    @app.route('/api/projects/import', methods=['POST'])
    def import_project():
        from project_requirement_import import parse_workbook
        session = request_session(runtime['DbSession'])
        try:
            if request.content_length and request.content_length > 11_000_000:
                raise ValueError('Choose an .xlsx workbook no larger than 10 MB.')
            upload = request.files.get('file')
            if upload is None:
                raise ValueError('Choose a requirements workbook.')
            filename = (upload.filename or '').replace('\\', '/').split('/')[-1]
            suggested, document = parse_workbook(upload.stream.read(10_000_001), filename)
            if request.path.endswith('/preview'):
                return jsonify(name=suggested, categories=len(document['categories']),
                               items=sum(len(c['items']) for c in document['categories']),
                               skus=len(document['skus']), columns=document['skus'], specifications=document['categories'], source_sha256=document['source']['sha256'], sheets=[v for k,v in document['source'].items() if k.endswith('_sheet') and v])
            name = request.form.get('name', suggested).strip()
            if not name or len(name)>100:
                raise ValueError('Enter a Project name of 1 to 100 characters.')
            try:
                choices = json.loads(request.form.get('classifications', '[]'))
            except (TypeError, ValueError):
                raise ValueError('Invalid comparison column classification.')
            if document['skus'] and request.form.get('review_confirmed') != 'true':
                raise ValueError('Confirm the SKU or Project classification before creating Projects.')
            if document['skus'] and request.form.get('source_sha256') != document['source']['sha256']:
                raise ValueError('The workbook changed. Preview and classify it again.')
            from project_import_review import split_projects
            candidates = split_projects(name, document, choices)
            existing = {p.name.casefold() for p in session.query(Project)}
            conflicts = [n for n, _ in candidates if n.casefold() in existing]
            if conflicts:
                return jsonify(error='Project names already exist: ' + ', '.join(conflicts) + '. No Projects were created.'), 409
            stamp = datetime.now(timezone.utc).isoformat()
            result = []
            for project_name, project_doc in candidates:
                project_doc['source']['imported_at'] = stamp
                encoded = json.dumps(project_doc, ensure_ascii=False)
                if len(encoded.encode('utf-8')) > 2_000_000:
                    raise ValueError('Project information exceeds 2 MB.')
                project = Project(name=project_name)
                session.add(project)
                session.flush()
                session.add(ProjectInformation(project_id=project.id, document=encoded, revision=1, updated_at=stamp))
                result.append(dict(id=project.id, name=project_name, skus=len(project_doc['skus'])))
            session.commit()
            return jsonify(id=result[0]['id'], name=result[0]['name'], projects=result), 201
        except ValueError as exc:
            session.rollback()
            return jsonify(error=str(exc)),400
        except IntegrityError:
            session.rollback()
            return jsonify(error='A Project with this name already exists.'),409
        finally:
            session.close()

    @app.route('/api/projects/<project_id>/information', methods=['GET', 'PUT'])
    def project_information(project_id):
        session = request_session(runtime['DbSession'])
        try:
            project = session.get(Project, project_id)
            if project is None:
                return jsonify(error='Project not found.'), 404
            record = session.get(ProjectInformation, project_id)
            if request.method == 'GET':
                return jsonify(project_id=project.id, project_name=project.name,
                               revision=record.revision if record else 0,
                               updated_at=record.updated_at if record else '',
                               document=json.loads(record.document) if record else blank_information())
            data = request.get_json(silent=True)
            if not isinstance(data, dict) or type(data.get('revision')) is not int:
                return jsonify(error='A revision is required.'), 400
            if data['revision'] != (record.revision if record else 0):
                return jsonify(error='Project information changed. Reload before saving.'), 409
            document = validate_document(data.get('document'))
            encoded = json.dumps(document, ensure_ascii=False)
            if len(encoded.encode('utf-8')) > 2_000_000:
                return jsonify(error='Project information exceeds 2 MB.'), 400
            stamp = datetime.now(timezone.utc).isoformat()
            if record:
                changed = session.execute(update(ProjectInformation).where(
                    ProjectInformation.project_id == project_id,
                    ProjectInformation.revision == data['revision']).values(
                        document=encoded, revision=data['revision'] + 1, updated_at=stamp))
                if changed.rowcount != 1:
                    session.rollback()
                    return jsonify(error='Project information changed. Reload before saving.'), 409
            else:
                session.add(ProjectInformation(project_id=project_id, document=encoded, revision=1, updated_at=stamp))
            session.commit()
            return jsonify(revision=data['revision'] + 1, updated_at=stamp, document=document)
        except ValueError as exc:
            session.rollback()
            return jsonify(error=str(exc)), 400
        except IntegrityError:
            session.rollback()
            return jsonify(error='Project information changed. Reload before saving.'), 409
        finally:
            session.close()
