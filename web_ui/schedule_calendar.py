"""Shared planning calendar: official Taiwan office days plus explicit user overrides."""
import json
import re
from datetime import date, timedelta
from pathlib import Path
from models import ScheduleDayOverride
from plan_state import StateError

OFFICIAL = json.loads(Path(__file__).with_name('taiwan_calendar.json').read_text(encoding='utf-8'))

def parse_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise StateError('Calendar dates must be valid YYYY-MM-DD dates.')
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise StateError('Calendar dates must be valid YYYY-MM-DD dates.')

def overrides(session):
    return {row.date: bool(row.is_working) for row in session.query(ScheduleDayOverride)}

def day_info(value, changes):
    key = value.isoformat()
    official = OFFICIAL['days'].get(key)
    default = official['is_working'] if official else value.weekday() < 5
    custom = key in changes
    return dict(date=key, is_working=changes.get(key, default), default_is_working=default,
                overridden=custom, source='manual' if custom else 'official' if official else 'weekend',
                name=official['name'] if official else '', covered=bool(official))

def working_days(start, end, changes):
    """Inclusive count; arithmetic baseline keeps even long historical ranges bounded."""
    first, last = parse_date(start), parse_date(end)
    if last < first:
        raise StateError('End date must be on or after start date.')
    full, rest = divmod((last-first).days+1, 7)
    count = full*5 + sum((first.weekday()+i)%7 < 5 for i in range(rest))
    for key, entry in OFFICIAL['days'].items():
        if start <= key <= end:
            count += int(entry['is_working'])-int(date.fromisoformat(key).weekday()<5)
    for key, working in changes.items():
        if start <= key <= end:
            count += int(working)-int(day_info(date.fromisoformat(key), {})['is_working'])
    complete = all(year in OFFICIAL['years'] for year in range(first.year, last.year+1))
    return count, complete

def range_info(start, end, changes):
    first, last = parse_date(start), parse_date(end)
    length = (last-first).days+1
    if not 1 <= length <= 366:
        raise StateError('Calendar range must contain 1 to 366 days.')
    return dict(start=start, end=end, years=OFFICIAL['years'], source_url=OFFICIAL['url'],
                days=[day_info(first+timedelta(days=i), changes) for i in range(length)])

def set_day(session, key, data):
    value = parse_date(key)
    if not isinstance(data, dict) or 'is_working' not in data or (data['is_working'] is not None and type(data['is_working']) is not bool):
        raise StateError('Choose a working day, non-working day or calendar default.')
    expected = data.get('expected_is_working')
    if type(expected) is not bool:
        raise StateError('Reload the calendar before changing a day.')
    current = day_info(value, overrides(session))
    if current['is_working'] != expected:
        raise StateError('This calendar day changed. Reload and try again.', 409)
    row = session.get(ScheduleDayOverride, key)
    if data['is_working'] is None:
        if row: session.delete(row)
    elif row:
        row.is_working = data['is_working']
    else:
        session.add(ScheduleDayOverride(date=key, is_working=data['is_working']))
    session.flush()
    return day_info(value, overrides(session))
