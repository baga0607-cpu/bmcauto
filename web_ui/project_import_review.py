"""Resolve explicit workbook-column classifications into independent Project documents."""
import copy
from project_information import validate_document


def split_projects(name, document, classifications):
    if not isinstance(classifications, list):
        raise ValueError('Classify every comparison column as SKU or Project.')
    columns = {sku['id']: sku for sku in document['skus']}
    choices = {}
    for choice in classifications:
        if not isinstance(choice, dict) or set(choice) != {'id', 'kind'}:
            raise ValueError('Invalid comparison column classification.')
        identity, kind = choice['id'], choice['kind']
        if not isinstance(identity, str) or identity not in columns or identity in choices or kind not in ('sku', 'project', 'skip'):
            raise ValueError('Classify each comparison column exactly once as SKU or Project.')
        choices[identity] = kind
    if set(choices) != set(columns):
        raise ValueError('Classify every comparison column as SKU or Project.')
    main = copy.deepcopy(document)
    main['skus'] = [sku for sku in main['skus'] if choices[sku['id']] == 'sku']
    retained = {sku['id'] for sku in main['skus']}
    for category in main['categories']:
        for item in category['items']:
            item['sku_values'] = {sid: value for sid, value in item['sku_values'].items() if sid in retained}
    projects = [(name, validate_document(main))] if retained or not columns else []
    for sku in document['skus']:
        if choices[sku['id']] != 'project':
            continue
        separate = copy.deepcopy(document)
        separate['skus'] = []
        separate['metadata']['product_name'] = sku['name']
        for category in separate['categories']:
            for item in category['items']:
                # Preserve this column's exact value, including blanks/No/N/A. Never fall back to aggregate prose.
                item['target'] = item['sku_values'].get(sku['id'], '')
                item['sku_values'] = {}
                item['source_ref'] += '; column ' + sku['id']
        projects.append((sku['name'], validate_document(separate)))
    if not projects:
        raise ValueError('No Projects selected. All SKUs are skipped.')
    names = [project_name.casefold() for project_name, _ in projects]
    if len(names) != len(set(names)):
        raise ValueError('Resulting Project names conflict. Correct the workbook column names.')
    if any(not project_name.strip() or len(project_name) > 100 for project_name, _ in projects):
        raise ValueError('Every Project name must contain 1 to 100 characters.')
    return projects
