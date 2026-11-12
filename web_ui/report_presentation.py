"""Read-only presentation adapters; never alter execution evidence or verdicts."""
import re

from report_case import display


def note_text(result):
    """Consume the execution pipeline's canonical note, without re-deriving it."""
    value = result.get('note')
    if isinstance(value, list):
        return '\n'.join(display(item) for item in value if item is not None and str(item).strip()) or '—'
    return display(value) if value is not None and str(value).strip() else '—'


def specification_reference(result, metadata, suite_path=''):
    """Use recorded declarations first; never infer compliance from case names.

    Legacy criteria with an explicit numbered standard are shown verbatim, not
    parsed into invented references. An execution definition is authoritative.
    """
    definition = result.get('report_definition')
    definition = definition if isinstance(definition, dict) else metadata
    refs = []
    explicit = definition.get('spec_ref')
    if explicit:
        refs.extend(explicit if isinstance(explicit, list) else [explicit])
    methods = definition.get('test_method', [])
    for method in methods if isinstance(methods, list) else []:
        if not isinstance(method, dict):
            continue
        ref = method.get('spec_ref')
        if ref:
            refs.extend(ref if isinstance(ref, list) else [ref])
        elif isinstance(method.get('criteria'), str) and re.search(
                r'\b(?:DSP\d{4}|RFC\s*\d{3,5}|ISO(?:/IEC)?\s*\d+|IEEE\s*\d+)', method['criteria']):
            refs.append(method['criteria'])
    texts = list(dict.fromkeys(display(ref) for ref in refs if ref))
    if texts:
        return '\n\n'.join(texts)
    compliance_suite = any(part.strip().casefold() in ('compliance', 'compliance test', 'compliance tests')
                           for part in suite_path.split('/'))
    if definition.get('test_type') == 'compliance' or definition.get('compliance') is True or compliance_suite:
        return '—'
    return None
