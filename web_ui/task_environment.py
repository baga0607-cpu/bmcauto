"""Task-owned connection environment; never reads the global config.yaml."""
import json
from urllib.parse import urlparse

FIELDS = {
    'redfish': {'host': '', 'username': '', 'password': '', 'verify_ssl': False},
    'console_server': {'host': '', 'port': 22, 'protocol': 'ssh', 'username': '', 'password': ''},
    'dut_console': {'connect_cmd': '', 'exit_cmd': '', 'force_connect_cmd': ''},
    'dut_os': {'os_type': 'linux', 'host_ip': '', 'ssh_port': 22, 'username': '', 'password': '', 'prompt_regex': '.*# '},
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
            elif (group, key) in (('console_server','port'), ('dut_os','ssh_port')):
                if isinstance(item, bool): raise ValueError('SSH port must be between 1 and 65535.')
                try: item = int(item) if item != '' else 22
                except (ValueError, TypeError): raise ValueError('SSH port must be between 1 and 65535.')
                if not 1 <= item <= 65535: raise ValueError('SSH port must be between 1 and 65535.')
            elif not isinstance(item, str): raise ValueError('Connection fields must be strings.')
            result[name] = item
    if result['cs_protocol'] not in ('ssh', 'telnet'): raise ValueError('Console protocol must be ssh or telnet.')
    ports = value.get('lan_ports', value.get('redfish', {}).get('lan_ports'))
    if ports is None:
        ports = [{'ip': result['host'], 'ipmi_channel': None}] if result['host'] else []
    if not isinstance(ports, list) or len(ports) > 16:
        raise ValueError('Supply up to 16 BMC LAN ports.')
    channels = set()
    result['lan_ports'] = []
    for port in ports:
        if not isinstance(port, dict) or not isinstance(port.get('ip'), str) or not port['ip'].strip():
            raise ValueError('Each BMC LAN port needs an address.')
        channel = port.get('ipmi_channel')
        if channel is not None:
            if type(channel) is not int or not 0 <= channel <= 15 or channel in channels:
                raise ValueError('IPMI channels must be unique integers from 0 to 15 or empty.')
            channels.add(channel)
        result['lan_ports'].append({'ip': port['ip'].strip(), 'ipmi_channel': channel})
    if ports:
        ip = result['lan_ports'][0]['ip']
        result['host'] = ip if '://' in ip else 'https://' + ip
    else:
        result['host'] = ''
    return result

def configuration(value, require_host=False):
    settings = normalize(value)
    if require_host:
        url = urlparse(settings['host'])
        if url.scheme not in ('http', 'https') or not url.hostname:
            raise ValueError('Configure this Task’s BMC URL (http:// or https://) in Connection settings before execution.')
    config = {group: {key: settings[flat_key(group, key)] for key in fields} for group, fields in FIELDS.items()}
    config['redfish']['lan_ports'] = settings['lan_ports']
    return config

def save(task, value, session):
    from models import TaskTestCase
    from plan_state import StateError
    if json.loads(task.task_metadata or '{}').get('task_status') == 'Deleted':
        raise StateError('This Task is Deleted and cannot be edited.', 409)
    if task.execution_active: raise StateError('This Task is executing. Connection settings are locked.', 409)
    previous = normalize(task.environment_config)
    if isinstance(value, dict) and 'lan_ports' not in value and 'redfish' not in value:
        value = dict(value)
        ports = list(previous['lan_ports'])
        if ports and value.get('host'):
            ports[0] = {**ports[0], 'ip': value['host']}
            value['lan_ports'] = ports
        value.setdefault('dut_os_ssh_port', previous['dut_os_ssh_port'])
    try: settings = normalize(value)
    except ValueError as error: raise StateError(str(error))
    if normalize(task.environment_config) != settings:
        for row in session.query(TaskTestCase).filter_by(task_id=task.id):
            if row.result_json or row.executed_at: row.mark_for_retest('Connection Modified')
    task.environment_config = json.dumps(settings, ensure_ascii=False)
    return settings
