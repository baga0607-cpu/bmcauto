"""Supervise a killable case process while the server owns logs and Task state."""
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import uuid


class WindowsJob:
    """A named job includes helpers started by the case, including ipmitool."""
    def __init__(self, name, create):
        from ctypes import wintypes
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        for name_, args, result in [
            ('CreateJobObjectW', [wintypes.LPVOID, wintypes.LPCWSTR], wintypes.HANDLE),
            ('OpenJobObjectW', [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
            ('AssignProcessToJobObject', [wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            ('TerminateJobObject', [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            ('CloseHandle', [wintypes.HANDLE], wintypes.BOOL),
        ]:
            fn = getattr(self.api, name_)
            fn.argtypes, fn.restype = args, result
        self.handle = (self.api.CreateJobObjectW(None, name) if create
                       else self.api.OpenJobObjectW(1, False, name))
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def join_current_process(self):
        if not self.api.AssignProcessToJobObject(self.handle, -1):
            raise ctypes.WinError(ctypes.get_last_error())

    def terminate(self):
        if not self.api.TerminateJobObject(self.handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        self.api.CloseHandle(self.handle)


def run_case_worker(config, run, emit):
    if run['stop_requested']:
        return 'stopped', None
    job = None
    if os.name == 'nt':
        config['job_name'] = 'BMCAgent-' + uuid.uuid4().hex
        job = WindowsJob(config['job_name'], True)
    try:
        with subprocess.Popen([sys.executable, '-u', str(Path(__file__).with_name('case_worker.py'))],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                              start_new_session=os.name != 'nt') as process:
            done = threading.Event()

            def terminate():
                if job:
                    job.terminate()
                    if process.poll() is None:
                        process.kill()  # Also covers startup before joining the job.
                else:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

            def watch_stop():
                run['cancel_event'].wait()
                if not done.is_set():
                    terminate()

            def send(value):
                process.stdin.write((json.dumps(value) + '\n').encode('ascii'))
                process.stdin.flush()

            watcher = threading.Thread(target=watch_stop, daemon=True)
            watcher.start()
            outcome = None
            try:
                send(config)
                for line in process.stdout:
                    event = json.loads(line)
                    kind = event['type']
                    if kind == 'worker_ready':
                        if not run['stop_requested']:
                            send(True)
                        continue
                    if kind == 'worker_exit':
                        outcome = event['state'], event['verdict']
                        break
                    if kind == 'input_required':
                        run['input_prompt'] = event['text']
                    emit(event)
                    if kind == 'input_required':
                        value = run['input_queue'].get()
                        run['input_prompt'] = None
                        if not run['stop_requested']:
                            send(value)
                if run['stop_requested']:
                    return 'stopped', None
                if outcome is None:
                    raise RuntimeError('Case worker exited without a result')
                return outcome
            finally:
                done.set()
                run['cancel_event'].set()
                watcher.join()
                terminate()
                process.wait()
                run['input_prompt'] = None
    finally:
        if job:
            job.close()
