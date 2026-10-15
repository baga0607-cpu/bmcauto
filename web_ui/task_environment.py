"""Task-owned connection environment; never reads the global config.yaml."""
import json
from urllib.parse import urlparse

FIELDS = {
    'redfish': {'host': '', 'username': '', 'password': '', 'verify_ssl': False},
    'console_server': {'host': '', 'port': 22, 'protocol': 'ssh', 'username': '', 'password': ''},
    'dut_console': {'connect_cmd': '', 'exit_cmd': '', 'force_connect_cmd': ''},
    'dut_os': {'os_type': 'linux', 'host_ip': '', 'username': '', 'password': '', 'prompt_regex': '.*# '},
}
PREFIX = {'redfish': '', 'console_server': 'cs_', 'dut_console': 'dut_', 'dut_os': 'dut_os_'}

def flat_key(group, key):
    return 'dut_os_type' if group == 'dut_os' and key == 'os_type' else PREFIX[group] + key

def normalize(value):
    if isinstance(value, str):
        try: value = json.loads(value)
        except ValueError: raise ValueError('Task connection settings must be a JSON object.')
    if value is None: value = {}
    if not isinstance(value, dict): raise ValueError('Task connection settings must be an object.')
    result = {}
    for group, fields in FIELDS.items():
        nested = value.get(group, {})
        if not isinstance(nested, dict): raise ValueError('Invalid connection settings group: ' + group)
        for key, default in fields.items():
            name = flat_key(group, key)
            item = value.get(name, nested.get(key, default))
            if key == 'verify_ssl':
                if not isinstance(item, bool): raise ValueError('Verify TLS certificate must be a boolean.')
            elif group == 'console_server' and key == 'port':
                if isinstance(item, bool): raise ValueError('Console port must be between 1 and 65535.')
                try: item = int(item) if item != '' else 22
                except (ValueError, TypeError): raise ValueError('Console port must be between 1 and 65535.')
                if not 1 <= item <= 65535: raise ValueError('Console port must be between 1 and 65535.')
            elif not isinstance(item, str): raise ValueError('Connection fields must be strings.')
            result[name] = item
    if result['cs_protocol'] not in ('ssh', 'telnet'): raise ValueError('Console protocol must be ssh or telnet.')
    return result

def configuration(value, require_host=False):
    settings = normalize(value)
    if require_host:
        url = urlparse(settings['host'])
        if url.scheme not in ('http', 'https') or not url.hostname:
            raise ValueError('Configure this Task’s BMC URL (http:// or https://) in Connection settings before execution.')
    return {group: {key: settings[flat_key(group, key)] for key in fields} for group, fields in FIELDS.items()}

def save(task, value, session):
    from models import TaskTestCase
    from plan_state import StateError
    if task.execution_active: raise StateError('This Task is executing. Connection settings are locked.', 409)
    try: settings = normalize(value)
    except ValueError as error: raise StateError(str(error))
    if normalize(task.environment_config) != settings:
        for row in session.query(TaskTestCase).filter_by(task_id=task.id):
            if row.result_json or row.executed_at: row.needs_retest = True
    task.environment_config = json.dumps(settings, ensure_ascii=False)
    return settings
