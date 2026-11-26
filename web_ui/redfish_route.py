"""Authenticated, same-origin Redfish GET traversal with synchronous per-response inspection."""
from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests



def _origin(url):
    parts = urlsplit(url)
    if (parts.scheme not in ('http', 'https') or not parts.hostname
            or parts.username is not None or parts.password is not None
            or any(c.isspace() or ord(c) < 32 or c == '\\' for c in url)):
        raise ValueError('Invalid HTTP resource URI')
    return parts.scheme, parts.hostname, parts.port or (443 if parts.scheme == 'https' else 80)


@dataclass
class RedfishHop:
    uri: str
    status: int
    headers: dict
    text: str
    evidence_id: int


class RedfishRoute:
    def __init__(self, context, declaration):
        conf = context.get('redfish') or {}
        if (declaration['from'], declaration['to'], declaration['method']) != ('bmcagent', 'bmc', 'redfish'):
            raise ValueError('Unsupported Redfish route')
        if (declaration['username'], declaration['password']) != ('task.bmc.username', 'task.bmc.password'):
            raise ValueError('Unsupported Redfish credential reference')
        prefix = 'task.bmc.lan_ports.port'
        reference = declaration['lan_port']
        if not reference.startswith(prefix):
            raise ValueError('Invalid Redfish LAN port reference')
        port = reference[len(prefix):]
        if not port.isdecimal() or int(port) < 1:
            raise ValueError('Invalid Redfish LAN port reference')
        ports = conf.get('lan_ports')
        if ports is None and port == '1':
            self.host = conf.get('host') or ''
        elif ports and int(port) <= len(ports):
            address = ports[int(port) - 1]['ip']
            self.host = address if '://' in address else 'https://' + address
        else:
            raise ValueError('Missing configured BMC LAN port')
        self.origin = _origin(self.host)
        self._auth = (conf.get('username', ''), conf.get('password', ''))
        self._verify = conf.get('verify_ssl', False)
        self._log = context['log']

    @contextmanager
    def traversal(self, *, redirect_statuses, max_redirects, allow_target, inspect_hop):
        """Cache repeated resources within this traversal, including redirect aliases."""
        cache = {}
        with requests.Session() as session:
            session.trust_env = False
            session.auth = self._auth

            def get(uri):
                current = uri
                chain = []
                try:
                    while True:
                        if _origin(current) != self.origin:
                            raise ValueError('Target outside the allowed traversal scope: different origin')
                        if not allow_target(current):
                            raise ValueError('Target outside the allowed traversal scope')
                        if current in chain:
                            raise ValueError('Redirect loop detected')
                        if current in cache:
                            result = cache[current]
                            if isinstance(result, Exception):
                                raise result
                            break
                        chain.append(current)
                        headers = {'Accept': 'application/json'}
                        try:
                            response = session.get(current, headers=headers, verify=self._verify,
                                                   timeout=15, allow_redirects=False)
                        except requests.RequestException as error:
                            raise ValueError(f'HTTP request could not complete ({type(error).__name__})') from error
                        raw = getattr(getattr(response, 'raw', None), 'headers', None)
                        fields = {}
                        for key, value in response.headers.items():
                            name = key.lower()
                            if name in ('link', 'location', 'content-location'):
                                fields[name] = raw.getlist(key) if hasattr(raw, 'getlist') else [value]
                        evidence_id = self._log.http(
                            'GET', current, response.status_code, response.headers, response.text,
                            request_headers=headers, link_values=fields.get('link'))
                        result = RedfishHop(current, response.status_code, fields, response.text, evidence_id)
                        # The case can report observations or veto this hop before any follow-up GET.
                        inspect_hop(result)
                        if result.status not in redirect_statuses:
                            break
                        locations = fields.get('location', [])
                        if len(locations) != 1 or not locations[0]:
                            raise ValueError('Redirect must contain exactly one nonempty Location')
                        if len(chain) > max_redirects:
                            raise ValueError(f'Redirect limit exceeded ({max_redirects} redirects)')
                        target = urlsplit(urljoin(current, locations[0]))
                        current = urlunsplit(target._replace(fragment=''))
                    for alias in chain:
                        cache[alias] = result
                    return result
                except Exception as error:
                    for alias in chain:
                        cache[alias] = error
                    raise
            yield get
