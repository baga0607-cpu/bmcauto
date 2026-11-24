"""Run one Plan case. The web server retains Task admission and evidence ownership."""
import builtins
import json
import os
import sys
from contextlib import redirect_stdout
from types import SimpleNamespace

from case_log import CaseLog, PrintLogWriter


def execute(config, emit, receive):
    import redfish
    import single_case as sc
    import urllib3
    from case_client import WebLoggingRedfishClient

    environment = config['environment']
    conf = environment['redfish']
    settings = config['settings']
    name = config['name']
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def prompt(text=''):
        emit({'type': 'input_required', 'text': text})
        value = receive()
        emit({'type': 'input_resolved'})
        return value

    with open(config['log_path'], 'a', encoding='utf-8') as output:
        writer = PrintLogWriter(output, emit)
        log = CaseLog(output, emit)
        log.section('Platform connection')
        original_input = builtins.input
        client = None
        reason = 'Execution finished'
        verdict = None
        with redirect_stdout(writer):
            builtins.input = prompt
            try:
                emit({'type': 'status', 'text': f"Connecting to BMC: {conf['host']}..."})
                client = redfish.redfish_client(base_url=conf['host'], username=conf['username'],
                    password=conf['password'], default_prefix='/redfish/v1',
                    cafile=True if conf.get('verify_ssl') else None, timeout=15, max_retry=3)
                client.login(auth='basic')
                emit({'type': 'status', 'text': f"[OK] Connected to BMC: {conf['host']}"})
                client = WebLoggingRedfishClient(client, api_file=output,
                    msg_queue=SimpleNamespace(put=emit), environment=environment)
                context = dict(environment, _session_id=config['session_id'], _tc_status='PASS',
                               log=log, case_settings=settings)
                emit({'type': 'case_start', 'case_name': name})
                try:
                    sc.execute_script(config['root'], config['module'], client, context, settings.get('preset'))
                    verdict = {'PASS':'PASS', 'BLOCK':'BLOCK', 'CP':'C-PASS', 'C-PASS':'C-PASS'}.get(context.get('_tc_status'), 'FAIL')
                    emit({'type': 'case_done', 'case_name': name, 'result': verdict})
                except Exception as error:
                    verdict, reason = 'FAIL', str(error)
                    emit({'type': 'case_done', 'case_name': name, 'result': verdict, 'error': reason})
                emit({'type': 'done', 'text': 'Test Case execution finished.'})
                return 'done', verdict
            except Exception as error:
                reason = f'[FAIL] Connection failed: {error}'
                emit({'type': 'error', 'text': reason})
                return 'error', None
            finally:
                try:
                    if client is not None:
                        print('  [Console] Logging out and closing connections...')
                        client.logout()
                except Exception:
                    pass
                finally:
                    builtins.input = original_input
                    writer.flush()
                    log.finish({'PASS':'Pass','BLOCK':'Block','CP':'C-PASS','C-PASS':'C-PASS'}.get(verdict,'Fail'), reason)


if __name__ == '__main__':
    config = json.loads(sys.stdin.buffer.readline())
    if 'job_name' in config:
        from case_process import WindowsJob
        job = WindowsJob(config['job_name'], False)
        try:
            job.join_current_process()
        finally:
            job.close()
    # Reserve a non-inheritable protocol pipe. Native tools and case subprocesses
    # may write to stdout without corrupting the supervisor's event stream.
    output = os.fdopen(os.dup(sys.stdout.fileno()), 'wb', buffering=0)
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    if os.name == 'nt':
        import ctypes
        import msvcrt
        from ctypes import wintypes
        set_handle = ctypes.windll.kernel32.SetStdHandle
        set_handle.argtypes = [wintypes.DWORD, wintypes.HANDLE]
        set_handle(-11 & 0xffffffff, msvcrt.get_osfhandle(sys.stdout.fileno()))
    output.write(b'{"type":"worker_ready"}\n')
    if sys.stdin.buffer.readline() != b'true\n':
        sys.exit(1)
    sys.path.insert(0, config['root'])
    sys.path.append(config['framework_root'])

    def emit(event):
        output.write((json.dumps(event) + '\n').encode('ascii'))
        output.flush()

    state, verdict = execute(config, emit, lambda: json.loads(sys.stdin.buffer.readline()))
    emit({'type': 'worker_exit', 'state': state, 'verdict': verdict})
