"""Taipei civil time used for BMCAgent timestamp presentation."""
from datetime import datetime, timedelta, timezone

TAIPEI = timezone(timedelta(hours=8))


def format_timestamp(value):
    if not value:
        return '—'
    try:
        stamp = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return '—'
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=TAIPEI)
    return stamp.astimezone(TAIPEI).strftime('%Y-%m-%d %H:%M:%S')
