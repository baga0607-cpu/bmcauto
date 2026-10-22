"""Shared names for saved SKU labels, Plan suggestions and Task numbering."""
import unicodedata


def compact_name(value):
    return ''.join(c for c in unicodedata.normalize('NFKC', value) if c.isalnum())


def full_sku_name(project_name, sku_name):
    project_key, sku_key = compact_name(project_name).casefold(), compact_name(sku_name).casefold()
    return sku_name if project_key and sku_key.startswith(project_key) else f'{project_name} {sku_name}'
