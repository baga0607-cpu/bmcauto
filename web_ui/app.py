"""
Redfish Test Manager - Flask Backend
=====================================
橋接 Web UI 與現有 Redfish 自動化框架的 API 伺服器。
Runs independent single-file Plan Test Cases through Task scope.
"""

from pathlib import Path
import sys
import os
import json
import queue
import threading
import time
import datetime
import yaml

import uuid
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from models import Base, TestCase, PlanSubfolder, Task, TaskTestCase, Project, ProjectPlan, Category, PlanningTask
import sqlite3
import plan_state as ps
import single_case as sc
from case_log import CaseLog, PrintLogWriter, open_log_files


def _normalized_tc_name_for_schema(value):
    return (value or "").strip().casefold()


import subprocess
from flask import Flask, jsonify, request, Response, send_from_directory, send_file
from flask_cors import CORS

# ── 路徑設定：讓 Flask 可以 import main_program 下的模組 ──────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PROGRAM_DIR = os.environ.get("BMC_MAIN_PROGRAM_DIR", os.path.join(BASE_DIR, "..", "main_program"))
sys.path.insert(0, MAIN_PROGRAM_DIR)

try:
    from console_helper import ConsoleClient
except ModuleNotFoundError:
    from main_program.console_helper import ConsoleClient

class TestInterrupted(Exception):
    """Custom exception raised when test run is stopped or interrupted by the user."""
    pass

# 確保 workspace 存在
WORKSPACE_DIR = os.environ.get(
    "BMC_WEB_UI_WORKSPACE_DIR",
    os.path.join(BASE_DIR, "workspace"),
)
os.makedirs(WORKSPACE_DIR, exist_ok=True)
PROJECTS_FILE = os.path.join(WORKSPACE_DIR, "projects.json")

# Initialize SQLAlchemy
DB_PATH = os.path.join(WORKSPACE_DIR, "testcase_meta.db")

# Schema maintenance for the current Task database.
try:
    database_is_fresh = not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0
    if database_is_fresh:
        bootstrap_engine = create_engine(
            f"sqlite:///{DB_PATH}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bootstrap_engine)
        bootstrap_engine.dispose()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        try: cursor.execute("ALTER TABLE testcases ADD COLUMN selected TEXT DEFAULT '1'")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE testcases ADD COLUMN position INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE testcases ADD COLUMN normalized_name TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE testcases ADD COLUMN source_version TEXT")
        except sqlite3.OperationalError: pass
        cursor.execute("DROP INDEX IF EXISTS uq_testcases_plan_normalized_name")
        rows = cursor.execute(
            "SELECT system_id, plan_id, display_name, source_version FROM testcases ORDER BY rowid"
        ).fetchall()
        seen_normalized_names = set()
        for system_id, existing_plan_id, display_name, source_version in rows:
            normalized_name = _normalized_tc_name_for_schema(display_name)
            unique_key = (existing_plan_id, normalized_name, source_version or "")
            if unique_key in seen_normalized_names:
                normalized_name = f"{normalized_name}::legacy::{system_id}"
            seen_normalized_names.add(unique_key)
            cursor.execute(
                "UPDATE testcases SET normalized_name = ? WHERE system_id = ?",
                (normalized_name, system_id),
            )
        try: cursor.execute("ALTER TABLE project_plans ADD COLUMN category_order TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE plan_subfolders ADD COLUMN position INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass
        
        try: cursor.execute("ALTER TABLE tasks ADD COLUMN environment_config TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE tasks ADD COLUMN task_metadata TEXT")
        except sqlite3.OperationalError: pass
        
        try: cursor.execute("ALTER TABLE task_testcases ADD COLUMN status TEXT DEFAULT 'tbd'")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE task_testcases ADD COLUMN bug_id TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE task_testcases ADD COLUMN executed_at TEXT")
        except sqlite3.OperationalError: pass
        try:
            cursor.execute("UPDATE task_testcases SET status = 'tbd' WHERE status = 'pending' OR status = 'tdb' OR status IS NULL OR status = ''")
            cursor.execute("UPDATE task_testcases SET status = 'passed' WHERE status = 'pass'")
            cursor.execute("UPDATE task_testcases SET status = 'failed' WHERE status = 'fail'")
        except Exception: pass
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plan_subfolders (
                id TEXT PRIMARY KEY,
                project TEXT NOT NULL,
                plan_id TEXT NOT NULL,
                subfolder_name TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                name TEXT NOT NULL,
                environment_config TEXT,
                task_metadata TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_testcases (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                testcase_id TEXT NOT NULL,
                position TEXT DEFAULT '0',
                selected TEXT DEFAULT '1',
                subfolder_id TEXT,
                status TEXT DEFAULT 'tbd',
                bug_id TEXT,
                executed_at TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                name TEXT PRIMARY KEY
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_plans (
                id TEXT PRIMARY KEY,
                project TEXT NOT NULL,
                name TEXT NOT NULL
            )
        ''')
        # Seed projects/project_plans from existing testcases data
        # Legacy seed runs only when the old schema still exists.
        cursor.execute("PRAGMA table_info(projects)")
        proj_cols = {row[1] for row in cursor.fetchall()}
        cursor.execute("PRAGMA table_info(project_plans)")
        pp_cols = {row[1] for row in cursor.fetchall()}
        cursor.execute("PRAGMA table_info(testcases)")
        tc_cols = {row[1] for row in cursor.fetchall()}
        v9_schema = 'id' in proj_cols and 'project_id' in pp_cols
        legacy_seed_schema = {'project', 'plan_id'}.issubset(tc_cols) and 'project' in pp_cols and 'name' in proj_cols

        if not v9_schema and legacy_seed_schema:
            # Legacy seed logic for pre-V9 databases.
            cursor.execute("SELECT DISTINCT project FROM testcases")
            for (proj_name,) in cursor.fetchall():
                cursor.execute("INSERT OR IGNORE INTO projects (name) VALUES (?)", (proj_name,))
            cursor.execute("SELECT DISTINCT project, plan_id FROM testcases")
            for (proj_name, plan_id) in cursor.fetchall():
                cursor.execute("INSERT OR IGNORE INTO project_plans (id, project, name) VALUES (?, ?, ?)",
                               (plan_id, proj_name, plan_id))
        # V9 databases use UUID relationships and skip legacy seeding.

        conn.commit()
except Exception as e:
    raise RuntimeError(f"Migration failed: {e}") from e

engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={"check_same_thread": False})

# V9: 啟用 SQLite 外鍵約束（每次連線時執行 PRAGMA foreign_keys=ON）
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

DbSession = sessionmaker(bind=engine)

# V9: 確保新 Schema 的欄位存在（冪等，安全可重複執行）
try:
    Base.metadata.create_all(engine)
except Exception as _e:
    raise

ps.migrate_current_state(engine, os.path.join(WORKSPACE_DIR, "migration-current-state.log"))

RESULTS_DIR = os.path.join(WORKSPACE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

# ── 全域執行狀態管理 ─────────────────────────────────────────────────────────
run_sessions = {}  # session_id -> { "queue": Queue, "status": str, "thread": Thread }


# ── 身分：API 透明代理 (輕量版 LoggingRedfishClient) ───────────────────
class IpmiResponse:
    def __init__(self, stdout, stderr, returncode, data=None):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.status = returncode
        self.data = data or []
        self.completion_code = 0x00 if returncode == 0 else None
        self.dict = {
            "stdout": stdout, 
            "stderr": stderr, 
            "returncode": returncode, 
            "data": self.data,
            "completion_code": self.completion_code
        }

import task_environment as te
import task_management as tm
import schedule_calendar as calendar

class WebLoggingRedfishClient:
    """API 透明代理：
    - 摘要與完整 response 共用 Test log，並推送 SSE
    - 完整 Response Body 直接寫入同一檔案，不經過 stdout
    """
    def __init__(self, client, api_file=None, msg_queue=None, environment=None):
        self._environment = environment or {}
        self._c       = client
        self._api_f   = api_file
        self._mq      = msg_queue   # SSE 佇列，用來推送完整 api_body 事件
        self._console_client = None

    def _get_console_client(self):
        if self._console_client is None:
            config = self._environment
            cs = config.get("console_server", {})
            if cs.get("host"):
                print("  [Console] Console Server configured; establishing connection...")
                self._console_client = ConsoleClient(config)
                self._console_client.connect()
                print("  [Console] Connected to Console Server.")
        return self._console_client

    def run_ipmitool(self, command_args, interface_options=None, ipmitool_args=None, **kwargs):
        """實作非 raw 的 ipmitool 執行代理，供步驟呼叫"""
        if ipmitool_args is None and interface_options:
            ipmitool_args = interface_options.get("ipmitool_args", [])
        if ipmitool_args is None:
            ipmitool_args = []
            
        interface_type = interface_options.get("type", "iol") if interface_options else "iol"
        
        # 決定是否走 Console Server 遠端執行
        use_remote = False
        if self._environment.get("console_server", {}).get("host") and interface_type in ("kcs", "serial"):
            use_remote = True

        cmd = ["ipmitool"] + ipmitool_args + command_args
        cmd_str = " ".join(cmd)

        if use_remote:
            print(f"  [Console][IPMI] Executing remote command: {cmd_str}")
            if self._api_f:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                self._api_f.write(f"{now_str} - DEBUG - [IPMI  ] [Console] {cmd_str}\n")
                self._api_f.flush()
            if self._mq is not None:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                header_line = f"{now_str} - DEBUG - [IPMI  ] [Console] {cmd_str}"
                self._mq.put({"type": "api_body", "text": header_line})

            try:
                console = self._get_console_client()
                if console:
                    if interface_type == "kcs":
                        remote_cmd = " ".join(["ipmitool"] + command_args)
                    else:
                        remote_cmd = " ".join(["ipmitool"] + ipmitool_args + command_args)
                        
                    stdout_str = console.exec_command(remote_cmd)
                    return {
                        "stdout": stdout_str,
                        "stderr": "",
                        "returncode": 0
                    }
            except Exception as e:
                print(f"         Remote IPMI execution failed: {e}")
                if self._api_f:
                    self._api_f.write(f"  Remote IPMI execution failed, error: {e}\n\n")
                    self._api_f.flush()
                if self._mq is not None:
                    self._mq.put({"type": "api_body", "text": f"  Remote IPMI execution failed, error: {e}"})
                return {
                    "stdout": "",
                    "stderr": str(e),
                    "returncode": 1
                }
        else:
            print(f"  [IPMI] Executing local command: {cmd_str}")
            if self._api_f:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                self._api_f.write(f"{now_str} - DEBUG - [IPMI  ] {cmd_str}\n")
                self._api_f.flush()
            if self._mq is not None:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                header_line = f"{now_str} - DEBUG - [IPMI  ] {cmd_str}"
                self._mq.put({"type": "api_body", "text": header_line})

            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                return {
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "returncode": res.returncode
                }
            except Exception as e:
                print(f"         Local IPMI execution failed: {e}")
                if self._api_f:
                    self._api_f.write(f"  Local IPMI execution failed, error: {e}\n\n")
                    self._api_f.flush()
                if self._mq is not None:
                    self._mq.put({"type": "api_body", "text": f"  Local IPMI execution failed, error: {e}"})
                return {
                    "stdout": "",
                    "stderr": str(e),
                    "returncode": 1
                }

    def raw(self, netfn, command, data=None, interface_options=None, ipmitool_args=None, **kwargs):
        """實作 IPMI raw 指令的代理，供積木呼叫 ipmitool"""
        if data is None:
            data = []
        
        if ipmitool_args is None and interface_options:
            ipmitool_args = interface_options.get("ipmitool_args", [])
        if ipmitool_args is None:
            ipmitool_args = []

        interface_type = interface_options.get("type", "iol") if interface_options else "iol"
        
        # 決定是否走 Console Server 遠端執行
        use_remote = False
        if self._environment.get("console_server", {}).get("host") and interface_type in ("kcs", "serial"):
            use_remote = True

        raw_args = ["raw", f"0x{netfn:02X}", f"0x{command:02X}"] + [f"0x{b:02X}" for b in data]
        cmd = ["ipmitool"] + ipmitool_args + raw_args
        cmd_str = " ".join(cmd)

        if use_remote:
            print(f"  [Console][IPMI] Executing remote command: {cmd_str}")
            if self._api_f:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                self._api_f.write(f"{now_str} - DEBUG - [IPMI  ] [Console] {cmd_str}\n")
                self._api_f.flush()
            if self._mq is not None:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                header_line = f"{now_str} - DEBUG - [IPMI  ] [Console] {cmd_str}"
                self._mq.put({"type": "api_body", "text": header_line})

            try:
                console = self._get_console_client()
                if console:
                    if interface_type == "kcs":
                        remote_cmd = " ".join(["ipmitool"] + raw_args)
                    else:
                        remote_cmd = " ".join(["ipmitool"] + ipmitool_args + raw_args)
                        
                    stdout_str = console.exec_command(remote_cmd)
                    
                    parsed_data = []
                    if stdout_str:
                        for token in stdout_str.strip().split():
                            try:
                                parsed_data.append(int(token, 16))
                            except ValueError:
                                pass
                    print(f"         IPMI succeeded: {parsed_data}")
                    if self._api_f:
                        self._api_f.write(f"  IPMI succeeded, response: {parsed_data}\n\n")
                        self._api_f.flush()
                    if self._mq is not None:
                        self._mq.put({"type": "api_body", "text": f"  IPMI succeeded, response: {parsed_data}"})
                    return IpmiResponse(stdout_str, "", 0, parsed_data)
            except Exception as e:
                print(f"         Remote IPMI execution failed: {e}")
                if self._api_f:
                    self._api_f.write(f"  Remote IPMI execution failed, error: {e}\n\n")
                    self._api_f.flush()
                if self._mq is not None:
                    self._mq.put({"type": "api_body", "text": f"  Remote IPMI execution failed, error: {e}"})
                return IpmiResponse("", str(e), 1, [])
        else:
            print(f"  [API][IPMI  ] {cmd_str}")
            if self._api_f:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                self._api_f.write(f"{now_str} - DEBUG - [IPMI  ] {cmd_str}\n")
                self._api_f.flush()
            if self._mq is not None:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                header_line = f"{now_str} - DEBUG - [IPMI  ] {cmd_str}"
                self._mq.put({"type": "api_body", "text": header_line})

            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                parsed_data = []
                if res.stdout and res.returncode == 0:
                    for token in res.stdout.strip().split():
                        try:
                            parsed_data.append(int(token, 16))
                        except ValueError:
                            pass
                resp = IpmiResponse(res.stdout, res.stderr, res.returncode, parsed_data)
                
                # Log output
                if res.returncode == 0:
                    print(f"         IPMI succeeded: {parsed_data}")
                    if self._api_f:
                        self._api_f.write(f"  IPMI succeeded, response: {parsed_data}\n\n")
                        self._api_f.flush()
                    if self._mq is not None:
                        self._mq.put({"type": "api_body", "text": f"  IPMI succeeded, response: {parsed_data}"})
                else:
                    print(f"         IPMI failed: {res.stderr.strip()}")
                    if self._api_f:
                        self._api_f.write(f"  IPMI failed, error: {res.stderr.strip()}\n\n")
                        self._api_f.flush()
                    if self._mq is not None:
                        self._mq.put({"type": "api_body", "text": f"  IPMI failed, error: {res.stderr.strip()}"})
                    
                return resp
            except Exception as e:
                print(f"         IPMI exception: {e}")
                if self._api_f:
                    self._api_f.write(f"  IPMI exception: {e}\n\n")
                    self._api_f.flush()
                if self._mq is not None:
                    self._mq.put({"type": "api_body", "text": f"  IPMI exception: {e}"})
                return IpmiResponse("", str(e), -1)

    def _log(self, method, uri, status, resp_dict=None):
        import datetime as _dt
        now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        icon = "[OK]" if status and str(status).isdigit() and int(status) < 300 else "[!!]"
        
        # 摘要行：透過 stdout 到 SSE + Test log
        print(f"  [API][{method:<6}] {uri} -> {status} {icon}")
        
        # 嘗試從 resp_dict 或 response 對象中提取 body
        body_to_log = resp_dict
        if not body_to_log:
            # 如果傳進來的是 None，嘗試從 context 獲取 (這取決於呼叫者，但這裡維持原樣)
            pass

        # 完整 body：直接寫入 Test log (只有首行帶時間戳記，Body 維持純淨縮排)
        if self._api_f:
            self._api_f.write(f"{now_str} - DEBUG - [{method:<6}] {uri} -> {status} {icon}\n")
            if body_to_log:
                import json as _json
                try:
                    body_str = _json.dumps(body_to_log, indent=2, ensure_ascii=False)
                    for line in body_str.splitlines():
                        self._api_f.write(f"  {line}\n")
                except:
                    self._api_f.write(f"  [Error serialization body]\n")
            self._api_f.write("\n")
            self._api_f.flush()
        # Push the full response body to SSE for task-side api_body events.
        if self._mq is not None:
            import json as _json
            header_line = f"{now_str} - DEBUG - [{method:<6}] {uri} -> {status} {icon}"
            body_lines = []
            if body_to_log:
                try:
                    body_str = _json.dumps(body_to_log, indent=2, ensure_ascii=False)
                    body_lines = [f"  {l}" for l in body_str.splitlines()]
                except:
                    body_lines = ["  [Error serialization body]"]
            full_text = "\n".join([header_line] + body_lines)
            self._mq.put({"type": "api_body", "text": full_text})

    def get(self, uri, **kw):
        r = self._c.get(uri, **kw)
        # 優先嘗試 .dict, 其次 .obj (有些版本 redfish 使用 .obj)
        body = getattr(r, "dict", None) or getattr(r, "obj", None)
        self._log("GET", uri, getattr(r, "status", "?"), body)
        return r

    def post(self, uri, **kw):
        r = self._c.post(uri, **kw)
        body = getattr(r, "dict", None) or getattr(r, "obj", None)
        self._log("POST", uri, getattr(r, "status", "?"), body)
        return r

    def patch(self, uri, **kw):
        r = self._c.patch(uri, **kw)
        body = getattr(r, "dict", None) or getattr(r, "obj", None)
        self._log("PATCH", uri, getattr(r, "status", "?"), body)
        return r

    def put(self, uri, **kw):
        r = self._c.put(uri, **kw)
        body = getattr(r, "dict", None) or getattr(r, "obj", None)
        self._log("PUT", uri, getattr(r, "status", "?"), body)
        return r

    def delete(self, uri, **kw):
        r = self._c.delete(uri, **kw)
        body = getattr(r, "dict", None) or getattr(r, "obj", None)
        self._log("DELETE", uri, getattr(r, "status", "?"), body)
        return r

    def head(self, uri, **kw):
        r = self._c.head(uri, **kw)
        body = getattr(r, "dict", None) or getattr(r, "obj", None)
        self._log("HEAD", uri, getattr(r, "status", "?"), body)
        return r

    def login(self, **kw): return self._c.login(**kw)
    def logout(self):
        if self._console_client:
            try:
                print("  [Console] Closing Console Server connection...")
                self._console_client.close()
            except Exception:
                pass
            self._console_client = None
        return self._c.logout()


# ============================================================================
# API 1: 掃描積木庫，回傳所有可用 Step 的 Metadata
# ============================================================================



# ============================================================================
# API 2: 載入所有的預設 TestCases (__testcase__.py)
# ============================================================================
@app.route('/api/testcases', methods=['GET'])
def get_testcases():
    with DbSession() as s:
        return jsonify([tc.to_dict() for tc in s.query(TestCase).order_by(TestCase.position)])
















@app.route('/api/plans/<plan_id>/testcases/<tc_id>/preview', methods=['GET'])
def get_testcase_preview(plan_id, tc_id):
    with DbSession() as s:
        tc = s.get(TestCase, tc_id)
        if not tc or tc.plan_id != plan_id: return jsonify(error='Test Case not found'), 404
        if tc.script_kind != 'single': return jsonify(error='Step-based Test Cases are retired. Import a single .py into the Repository.'), 410
        return jsonify(sc.definition(MAIN_PROGRAM_DIR, tc))



def _resolve_selected(val):
    """V9 相容層：統一將 selected 欄位值轉為 Python bool。"""
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val == 1
    return str(val) == '1'


def _json_loads_object(raw):
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _json_loads_list(raw):
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


@app.route('/api/projects', methods=['GET'])
def get_projects():
    with DbSession() as s:
        projects = []
        for project in s.query(Project).order_by(Project.name):
            plans = []
            for plan in project.plans:
                cases = [dict(tc.to_dict(), automation=sc.automation_for_case(MAIN_PROGRAM_DIR,tc), parameter_count=sc.parameter_count_for_case(MAIN_PROGRAM_DIR,tc)) for tc in ps.co.plan_rows(s,plan.id,plan.testcases)]
                tasks = [ps.summary(s, task.id, MAIN_PROGRAM_DIR) for task in plan.tasks]
                for task in tasks:
                    for case in task['testcases']:
                        case.pop('log_text', None); case.pop('api_log_text', None)
                plans.append(dict(id=plan.id, name=plan.name, testcases=cases, tasks=tasks,
                    folders=[f.to_dict() for f in s.query(ps.PlanFolder).filter_by(plan_id=plan.id).order_by(ps.PlanFolder.position)],
                    locked=any(task['execution_active'] for task in tasks)))
            projects.append(dict(id=project.id, name=project.name, plans=plans,
                                 planning_task_count=s.query(PlanningTask).filter_by(project_id=project.id).count()))
        return jsonify(projects=projects)


# The frontend save_projects API is a legacy from when projects.json was the source of truth.
# Now DB is the source of truth, so save_projects can just return OK or update selection state if needed.
# ============================================================================
# V9 新增：create_plan API（前端 newPlan() 呼叫此端點取得 UUID plan_id）
# ============================================================================
def validate_plan_name(session, project_id, name, exclude_id=None):
    name = (name or '').strip()
    if not name:
        raise ps.StateError('Enter a name.')
    duplicate = session.query(ProjectPlan).filter(ProjectPlan.project_id == project_id, ProjectPlan.name == name)
    if exclude_id:
        duplicate = duplicate.filter(ProjectPlan.id != exclude_id)
    if duplicate.first():
        raise ps.StateError('A Plan with this name already exists.', 409)
    return name


@app.route("/api/create_plan", methods=["POST"])
def create_plan():
    data = request.json
    project_name = data.get("project", "").strip()
    plan_name = data.get("plan_name", "").strip()
    if not project_name or not plan_name:
        return jsonify({"error": "Missing project or plan_name"}), 400
    session = ps.request_session(DbSession)
    try:
        proj = session.query(Project).filter_by(name=project_name).first()
        if not proj:
            return jsonify({"error": f"Project '{project_name}' not found"}), 404
        plan_name = validate_plan_name(session, proj.id, plan_name)
        new_plan_id = str(uuid.uuid4())
        new_plan = ProjectPlan(
            id=new_plan_id,
            project_id=proj.id,
            name=plan_name,
            folders_migrated=True
        )
        session.add(new_plan)
        session.flush()
        tm.bind_plan_sku(session, new_plan, data.get("sku_id"))
        paths = list(data.get("folder_paths", []))
        for path in paths: ps.resolve_folder(session, new_plan_id, {"folder_path": path})
        session.commit()
        return jsonify({"status": "ok", "plan_id": new_plan_id, "plan_name": plan_name})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), getattr(e, "code", 500)
    finally:
        session.close()



@app.route("/api/delete_project", methods=["POST"])
def delete_project():
    data = request.json
    project_name = data.get("project")
    if not project_name:
        return jsonify({"error": "Missing project"}), 400
    session = ps.request_session(DbSession)
    try:
        proj = session.query(Project).filter_by(name=project_name).first()
        if proj:
            session.delete(proj)
            session.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), getattr(e, "code", 500)
    finally:
        session.close()

@app.route("/api/delete_plan", methods=["POST"])
def delete_plan():
    data = request.json
    project_name = data.get("project")
    plan_id = data.get("plan_id")
    
    if not plan_id:
        return jsonify({"error": "Missing plan_id"}), 400
        
    session = ps.request_session(DbSession)
    try:
        plan = session.query(ProjectPlan).filter_by(id=plan_id).first()
        if plan:
            session.delete(plan)
            session.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), getattr(e, "code", 500)
    finally:
        session.close()

@app.route("/api/create_project", methods=["POST"])
def create_project():
    data = request.json
    project_name = data.get("project", "").strip()
    if not project_name:
        return jsonify({"error": "Missing project name"}), 400
    session = ps.request_session(DbSession)
    try:
        existing = session.query(Project).filter_by(name=project_name).first()
        if existing:
            return jsonify({"status": "ok", "note": "already exists"})
        session.add(Project(name=project_name))
        session.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), getattr(e, "code", 500)
    finally:
        session.close()

@app.route("/api/rename_project", methods=["POST"])
def rename_project():
    data = request.json
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    
    if not old_name or not new_name:
        return jsonify({"error": "Missing old_name or new_name"}), 400
        
    session = ps.request_session(DbSession)
    try:
        proj = session.query(Project).filter_by(name=old_name).first()
        if not proj:
            return jsonify({"error": f"Project '{old_name}' not found"}), 404
            
        proj.name = new_name
        session.commit()
        return jsonify({"status": "ok", "project_id": proj.id, "new_name": new_name})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), getattr(e, "code", 500)
    finally:
        session.close()


@app.route("/api/rename_plan", methods=["POST"])
def rename_plan():
    data = request.json
    project_name = data.get("project")
    old_plan_name = data.get("old_name")
    new_plan_name = data.get("new_name")
    
    if not project_name or not old_plan_name or not new_plan_name:
        return jsonify({"error": "Missing project, old_name, or new_name"}), 400
        
    session = ps.request_session(DbSession)
    try:
        proj = session.query(Project).filter_by(name=project_name).first()
        if not proj:
            return jsonify({"error": f"Project '{project_name}' not found"}), 404
            
        plan = session.query(ProjectPlan).filter_by(project_id=proj.id, name=old_plan_name).first()
        if not plan:
            return jsonify({"error": f"Plan '{old_plan_name}' not found in project '{project_name}'"}), 404
            
        plan.name = validate_plan_name(session, proj.id, new_plan_name, plan.id)
        session.commit()
        return jsonify({"status": "ok", "plan_id": plan.id, "new_name": new_plan_name})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), getattr(e, "code", 500)
    finally:
        session.close()

# ============================================================================
# V11 新增：增量更新 (PATCH / POST / DELETE) APIs 支援
# ============================================================================



@app.route("/api/plans/<plan_id>/testcases", methods=["PATCH"])
def patch_plan_testcases(plan_id):
    data = request.json
    session = ps.request_session(DbSession)
    try:
        tcs = session.query(TestCase).filter_by(plan_id=plan_id).all()
        if "selected" in data:
            val = bool(data["selected"])
            for tc in tcs:
                tc.selected = val
        session.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), getattr(e, "code", 500)
    finally:
        session.close()






@app.route("/api/tasks/<task_id>/testcases", methods=["PATCH"])
def patch_task_testcases(task_id):
    data = request.json
    session = ps.request_session(DbSession)
    try:
        task_tcs = session.query(TaskTestCase).filter_by(task_id=task_id).all()
        if "selected" in data:
            val = bool(data["selected"])
            for task_tc in task_tcs:
                task_tc.selected = val
        session.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), getattr(e, "code", 500)
    finally:
        session.close()


@app.route('/api/schedule/calendar', methods=['GET'])
def schedule_calendar_range():
    with DbSession() as session:
        try:
            return jsonify(calendar.range_info(request.args.get('start'), request.args.get('end'), calendar.overrides(session)))
        except ps.StateError as exc:
            return jsonify(error=str(exc)), exc.code


@app.route('/api/schedule/calendar/<day>', methods=['PATCH'])
def schedule_calendar_day(day):
    session = ps.request_session(DbSession)
    try:
        result = calendar.set_day(session, day, request.get_json(silent=True))
        session.commit()
        return jsonify(result)
    except Exception as exc:
        session.rollback()
        return jsonify(error=str(exc)), getattr(exc, 'code', 500)
    finally:
        session.close()


@app.route("/api/tasks", methods=["GET", "POST"])
def create_task():
    if request.method == 'GET':
        session = DbSession()
        try: return jsonify(tasks=tm.task_list(session))
        finally: session.close()
    session = ps.request_session(DbSession)
    try:
        result = tm.create(session, request.get_json(silent=True) or {})
        session.commit()
        return jsonify(result)
    except Exception as exc:
        session.rollback()
        return jsonify(error=str(exc)), getattr(exc, 'code', 500)
    finally:
        session.close()


@app.route('/api/tasks/<task_id>/history', methods=['GET'])
def task_schedule_history(task_id):
    with DbSession() as session:
        try:
            return jsonify(history=tm.history_list(session, task_id))
        except ps.StateError as exc:
            return jsonify(error=str(exc)), exc.code


@app.route('/api/tasks/<task_id>/schedule', methods=['PATCH'])
def update_task_schedule(task_id):
    session = ps.request_session(DbSession)
    try:
        result = tm.reschedule(session, task_id, request.get_json(silent=True))
        session.commit()
        return jsonify(result)
    except Exception as exc:
        session.rollback()
        code = getattr(exc, 'code', 500)
        return jsonify(error=str(exc)), code if isinstance(code, int) else 500
    finally:
        session.close()


@app.route("/api/tasks/<task_id>", methods=["PATCH", "DELETE"])
def handle_task(task_id, entity_label="Task"):
    session = ps.request_session(DbSession)
    try:
        tm.manage(session, task_id, request.get_json(silent=True) or {}, delete=request.method == 'DELETE')
        session.commit()
        return jsonify(status='ok')
    except Exception as exc:
        session.rollback()
        code = getattr(exc, 'code', 500)
        return jsonify(error=str(exc)), code if isinstance(code, int) else 500
    finally:
        session.close()


@app.route("/api/tasks/<task_id>/report", methods=["GET"])
def download_task_report(task_id):
    try:
        from report_generator import generate_task_pdf_report
        out_filename = f"report_{task_id}.pdf"
        out_path = os.path.join(WORKSPACE_DIR, "results", out_filename)
        generate_task_pdf_report(task_id, out_path, db_path=DB_PATH)
        return send_file(out_path, as_attachment=True, download_name=f"BMC_Test_Report_{task_id}.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), getattr(e, "code", 500)








@app.route("/api/tasks/<task_id>/testcases/reorder", methods=["POST"])
def reorder_task_testcases(task_id):
    data = request.json
    order = data.get("order", [])
    session = ps.request_session(DbSession)
    try:
        for idx, tc_id in enumerate(order):
            task_tc = session.query(TaskTestCase).filter_by(task_id=task_id, testcase_id=tc_id).first()
            if task_tc:
                task_tc.position = idx
        session.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), getattr(e, "code", 500)
    finally:
        session.close()




@app.route("/api/plans/<plan_id>", methods=["PATCH"])
def patch_plan(plan_id):
    data = request.json
    session = ps.request_session(DbSession)
    try:
        plan = session.query(ProjectPlan).filter_by(id=plan_id).first()
        if not plan:
            return jsonify({"error": "Plan not found"}), 404
            
        if "name" in data:
            plan.name = validate_plan_name(session, plan.project_id, data["name"], plan.id)

        if "category_order" in data:
            category_order = data["category_order"]
            if not isinstance(category_order, list):
                return jsonify({"error": "category_order must be a list"}), 400
            plan.category_order = json.dumps(
                [str(name).strip() for name in category_order if str(name).strip()],
                ensure_ascii=False
            )
            
        if "custom_subfolders" in data:
            subfolders_received = data["custom_subfolders"]
            current_subs = session.query(PlanSubfolder).filter_by(plan_id=plan_id).all()
            existing_sub_map = {s.subfolder_name: s.id for s in current_subs}
            
            for s in current_subs:
                if s.subfolder_name not in subfolders_received:
                    session.delete(s)
            
            for idx, s_name in enumerate(subfolders_received):
                folder = next((s for s in current_subs if s.subfolder_name == s_name), None)
                if folder is None:
                    folder = PlanSubfolder(plan_id=plan_id, subfolder_name=s_name)
                    session.add(folder)
                folder.position = idx
                    
        session.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), getattr(e, "code", 500)
    finally:
        session.close()


# ============================================================================
# API CRUD
# ============================================================================
def _normalized_tc_name(value):
    return _normalized_tc_name_for_schema(value)


def _find_normalized_name_duplicate(session, plan_id, display_name):
    wanted = _normalized_tc_name(display_name)
    return session.query(TestCase).filter_by(
        plan_id=plan_id, normalized_name=wanted
    ).first()








_testcase_name_write_lock = threading.RLock()




@app.route('/api/import_tc', methods=['POST'])
def import_tc():
    data = request.get_json(silent=True) or {}
    s = ps.request_session(DbSession)
    path = None
    try:
        plan = ps.require(s, ProjectPlan, data.get('plan_id'))
        ps.unlocked(s, plan.id)
        if data.get('system_id'):
            original = ps.require(s, TestCase, data['system_id'])
            if original.script_kind != 'single': raise ps.StateError('Step-based import is retired', 410)
            definition = sc.definition(MAIN_PROGRAM_DIR, original)
            source, version, settings = definition['source'], original.source_version, definition['settings']
            repository_id, family_id = original.repository_id, original.family_id
        else:
            if data.get('script_kind') != 'single' or not isinstance(data.get('source'), str):
                raise ps.StateError('Import a single .py through Test Case Repository; step import is retired', 410)
            source, version, settings = data['source'], data.get('source_version'), data.get('settings', {})
            if not version: raise ps.StateError('Source version is required')
            repository_id, family_id = None, str(uuid.uuid4())
        meta = sc.metadata(source)
        settings = sc.validate_settings(meta, settings)
        name = str(data.get('tc_name') or meta['name']).strip()
        if not name: raise ps.StateError('Test Case name is required')
        if s.query(TestCase).filter_by(plan_id=plan.id, normalized_name=name.casefold()).first():
            raise ps.StateError('A Test Case with this name already exists in the Plan', 409)
        folder = ps.resolve_folder(s, plan.id, data)
        identity = str(uuid.uuid4())
        tc = TestCase(system_id=identity, family_id=family_id, display_name=name, plan_id=plan.id,
            script_kind='single', script_path=f'testcase_database.scripts.{identity}',
            source_version=version, repository_id=repository_id, settings_json=json.dumps(settings))
        s.add(tc); s.flush(); ps.assign_folder(s, tc, folder)
        path = sc.script_file(MAIN_PROGRAM_DIR, tc)
        path.parent.mkdir(parents=True, exist_ok=False); path.write_text(source, encoding='utf-8')
        s.commit()
        return jsonify(tc.to_dict()), 201
    except Exception as error:
        s.rollback()
        if path:
            path.unlink(missing_ok=True); path.parent.rmdir()
        return jsonify(error=str(error)), getattr(error, 'code', 500)
    finally: s.close()








# ============================================================================
# API: 接收人工驗證輸入（Pass / Fail 或任意文字）
# 前端按下 PASS/FAIL 或提交文字輸入框後呼叫此 endpoint。
# 將值放入對應 session 的 input_queue，解除後端 input_queue.get() 的阻塞。
# ============================================================================
@app.route("/api/input", methods=["POST"])
def handle_input():
    data = request.json
    session_id = data.get("session_id")
    value = data.get("value", "")
    if session_id and session_id in run_sessions:
        if run_sessions[session_id].get('input_prompt') is None:
            return jsonify(error='This execution is not waiting for input.'), 409
        run_sessions[session_id]['input_prompt'] = None
        run_sessions[session_id]["input_queue"].put(value)
        return jsonify({"status": "ok"})
    return jsonify({"error": "session not found"}), 404

# ============================================================================
# API 4.9: 取得活動中的測試執行緒與專案鎖定名單
# ============================================================================
locked_project_ids = set()

@app.route("/api/run/active", methods=["GET"])
def get_active_runs():
    active_runs = []
    for sid, info in list(run_sessions.items()):
        t = info.get("thread")
        if t and t.is_alive():
            active_runs.append({
                "session_id": sid,
                "project_id": info.get("project_id"),
                "status": info.get("status"),
                "tc_name": info.get("tc_name"),
            })
    return jsonify({
        "active_runs": active_runs,
        "locked_project_ids": list(locked_project_ids)
    })


# ============================================================================
# API 5: 執行測試（接收步驟清單，啟動背景執行緒）
# ============================================================================
@app.route("/api/run", methods=["POST"])
def run_testcase():
    data = request.json
    session_id = data.get("session_id") or f"run_{uuid.uuid4()}"
    if session_id in run_sessions:
        return jsonify(error="Execution session ID has already been used"), 409
    tc_name = data.get("tc_name", "Custom_TestCase")
    project_id = data.get("project_id")
    task_id = data.get("task_id")
    testcase_id = data.get("testcase_id") or data.get("tc_id")
    execution_token = data.get("execution_token")
    single_execution = False
    case_settings = {}
    case_revision = None
    case_source_version = None
    if not task_id: return jsonify(error='Run Test Cases from a Task. Step execution is retired.'), 400
    if task_id:
        session = ps.request_session(DbSession)
        try:
            task = ps.require(session, Task, task_id)
            task_log_name = task.name
            membership = session.query(TaskTestCase).filter_by(task_id=task_id, testcase_id=testcase_id).first()
            if membership is None: raise ps.StateError("Execution cannot add Task scope")
            ps.check_execution_token(task, execution_token)
            if testcase_id not in json.loads(task.execution_selection or "[]"): raise ps.StateError("Testcase is not selected")
            if task.execution_worker_id: raise ps.StateError("A Task execution worker is already active", 409)
            if task.execution_stop_requested: raise ps.StateError("Task execution is stopping", 409)
            if membership.status == "Running": raise ps.StateError("Testcase is already running", 409)
            tc = ps.require(session, TestCase, testcase_id)
            if tc.plan_id != task.plan_id: raise ps.StateError('Test Case belongs to another Plan')
            case_revision = tc.settings_revision or 0
            case_source_version = tc.source_version
            if tc.script_kind == 'single':
                definition = sc.definition(MAIN_PROGRAM_DIR, tc)
                case_settings = sc.validate_settings(definition['metadata'], definition['settings'])
                case_module = tc.script_path + '.case'
                single_execution = True
                case_revision = tc.settings_revision or 0
                case_source_version = tc.source_version
                tc_name = tc.display_name
            else:
                raise ps.StateError('Step-based Test Cases are retired. Import a single .py into the Repository.', 410)
            try: environment = te.configuration(task.environment_config, require_host=True)
            except ValueError as error: raise ps.StateError(str(error))
            task.execution_worker_id = session_id
            membership.status = "Running"
            session.commit()
        except Exception as error:
            session.rollback()
            return jsonify(error=str(error)), getattr(error, "code", 500)
        finally:
            session.close()

    msg_queue = queue.Queue()
    input_queue = queue.Queue()
    run_sessions[session_id] = {
        "queue": msg_queue,
        "input_queue": input_queue,
        "status": "running",
        "thread": None,
        "stop_requested": False,
        "project_id": project_id,
        "listeners": [],
        "log_history": [],
        "tc_name": tc_name,
        "task_id": task_id,
        "testcase_id": testcase_id,
        "execution_token": execution_token,
    }

    if project_id:
        locked_project_ids.add(project_id)
        print(f"[API] Project {project_id} execution started; global read-only lock enabled.")

    def execute_in_thread():
        original_put = msg_queue.put
        def put_msg(msg):
            if session_id in run_sessions:
                if msg is not None:
                    run_sessions[session_id]["log_history"].append(msg)
                for q in list(run_sessions[session_id]["listeners"]):
                    q.put(msg)
            original_put(msg)
        msg_queue.put = put_msg
        def web_input(prompt=''):
            # 檢查是否已中斷
            if run_sessions[session_id].get("stop_requested"):
                raise TestInterrupted()
                
            run_sessions[session_id]['input_prompt'] = prompt
            msg_queue.put({"type": "input_required", "text": prompt})
            val = input_queue.get()
            run_sessions[session_id]['input_prompt'] = None
            msg_queue.put({'type': 'input_resolved'})
            
            # 如果抓到的是中斷哨兵值，拋出例外
            if val == "__STOP__":
                raise TestInterrupted()
            return val

        original_stdout = sys.stdout
        import builtins
        original_input = builtins.input
        builtins.input = web_input

        # ── 建立 log 目錄與本次執行的 log 檔 ────────────────────────────
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_tc_name = "".join([c if c.isalnum() or c in "-_" else "_" for c in tc_name]).strip("_")
        if not safe_tc_name:
            safe_tc_name = "Custom_TestCase"
            
        log_dir = os.path.join(WORKSPACE_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_files, result_file = open_log_files(log_dir, task_log_name, tc_name, task_id, testcase_id)
        result_log_path = os.path.join(log_dir, log_files['test'])
        log_header = (f"=== Web UI Run Log ===\nTask: {task_log_name}\nTask ID: {task_id}\n"
                      f"TestCase: {tc_name}\nTestCase ID: {testcase_id}\nTimestamp: {timestamp}\n"
                      + "=" * 40 + "\n\n")
        result_file.write(log_header)
        print_writer = PrintLogWriter(result_file, msg_queue.put)
        case_log = CaseLog(result_file, msg_queue.put)
        sys.stdout = print_writer
        case_log.section("Platform connection")

        try:
            import urllib3
            import redfish
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            conf = environment["redfish"]

            msg_queue.put({"type": "status", "text": f"Connecting to BMC: {conf['host']}..."})

            try:
                real_client = redfish.redfish_client(
                    base_url=conf["host"],
                    username=conf["username"],
                    password=conf["password"],
                    default_prefix="/redfish/v1",
                    cafile=True if conf.get('verify_ssl') else None,
                    timeout=15,
                    max_retry=3
                )
                real_client.login(auth="basic")
                msg_queue.put({"type": "status", "text": f"[OK] Connected to BMC: {conf['host']}"})
                # 套上透明代理，將 Test log 與 msg_queue 傳進去，同時寫 full body 並推送 SSE
                client = WebLoggingRedfishClient(real_client, api_file=result_file, msg_queue=msg_queue, environment=environment)
            except Exception as e:
                msg_queue.put({"type": "error", "text": f"[FAIL] Connection failed: {e}"})
                run_sessions[session_id]["status"] = "error"
                return

            context = {
                "_session_id": session_id,
                "_tc_status": "PASS",
                "redfish": conf
            }
            context['log'] = case_log
            context['console_server'] = environment['console_server']
            context['dut_console'] = environment['dut_console']
            context['dut_os'] = environment['dut_os']
            if single_execution:
                context['case_settings'] = case_settings
            
            if run_sessions[session_id].get('stop_requested'): raise TestInterrupted()
            module_path = case_module
            msg_queue.put({'type': 'case_start', 'case_name': tc_name})
            try:
                sc.execute_script(MAIN_PROGRAM_DIR, module_path, client, context, case_settings.get('preset'))
                result = 'FAIL' if context.get('_tc_status') in ('FAIL', 'Failed') else 'PASS'
                msg_queue.put({'type': 'case_done', 'case_name': tc_name, 'result': result})
            except TestInterrupted: raise
            except Exception as error:
                context['_tc_status'] = 'FAIL'
                msg_queue.put({'type': 'case_done', 'case_name': tc_name, 'result': 'FAIL', 'error': str(error)})

            msg_queue.put({"type": "done", "text": "Test Case execution finished."})
            run_sessions[session_id]["status"] = "done"

        except TestInterrupted:
            msg_queue.put({"type": "status", "text": "Execution was stopped by the operator."})
            msg_queue.put({"type": "done", "text": "Execution stopped."})
            run_sessions[session_id]["status"] = "stopped"

        except Exception as e:
            msg_queue.put({"type": "error", "text": f"Execution error: {e}"})
            run_sessions[session_id]["status"] = "error"
        finally:
            # 確保代理用戶端的登出與連線關閉被執行
            if 'client' in locals() and client:
                try:
                    print("  [Console] Logging out and closing connections...")
                    client.logout()
                except Exception:
                    pass
            elif 'real_client' in locals() and real_client:
                try:
                    real_client.logout()
                except Exception:
                    pass

            print_writer.flush()
            if not case_log.finished:
                state = run_sessions[session_id]["status"]
                stopped = state == "stopped" or run_sessions[session_id].get("stop_requested")
                status = "Stopped" if stopped else ("Pass" if state == "done" and locals().get("context", {}).get("_tc_status") == "PASS" else "Fail")
                errors = [event.get("error") or event.get("text") for event in run_sessions[session_id]["log_history"]
                          if event.get("type") == "error" or event.get("error")]
                case_log.finish(status, next((error for error in reversed(errors) if error),
                                             "Execution stopped by operator" if stopped else "Execution finished"))
            sys.stdout = original_stdout
            builtins.input = original_input
            result_file.write("\n" + "=" * 40 + "\n=== End of Log ===\n")
            result_file.close()
            if task_id:
                result_session = DbSession()
                try:
                    ps.begin_write(result_session)
                    stopped = run_sessions[session_id].get("stop_requested") or run_sessions[session_id]["status"] == "stopped"
                    outcome = "TBD" if stopped else ("Passed" if run_sessions[session_id]["status"] == "done" and locals().get("context", {}).get("_tc_status") == "PASS" else "Failed")
                    with open(result_log_path, encoding="utf-8") as result_log:
                        latest_log = result_log.read()
                    # Persist this testcase's current structured evidence before the stream closes.
                    # SSE-only failures are otherwise lost when the operational session disappears.
                    events = list(run_sessions[session_id].get("log_history", []))
                    case_details = [dict(event) for event in events if event.get("type") in ("case_start", "case_done")]
                    errors = [event.get("error") or event.get("text") for event in events
                              if event.get("type") == "error" or
                              (event.get("type") == "case_done" and event.get("result") == "FAIL")]
                    errors = [error for error in errors if error]
                    if case_details or errors:
                        evidence = ["", "=== Current execution details ==="]
                        for event in case_details:
                            if event.get("type") == "case_done":
                                evidence.append(f"Test Case: {event.get('result')} {event.get('case_name', '')} {event.get('error', '')}".rstrip())
                        evidence.extend(f"[ERROR] {error}" for error in errors)
                        latest_log += "\n".join(evidence) + "\n"
                    ps.save_result(result_session, task_id, {"id": testcase_id, "execution_token": execution_token, "status": outcome, "executed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "result": {"status": outcome, "events": case_details, "errors": errors, "log_records": case_log.records}, "log_text": latest_log, "api_log_text": ""})
                    if single_execution:
                        saved = result_session.query(TaskTestCase).filter_by(task_id=task_id, testcase_id=testcase_id).one()
                        result_data = json.loads(saved.result_json)
                        result_data.update(source_version=case_source_version, plan_settings_revision=case_revision,
                                           settings=case_settings, log_files=log_files)
                        saved.result_json = json.dumps(result_data, ensure_ascii=False)
                    result_session.commit()
                except Exception as persistence_error:
                    result_session.rollback()
                    run_sessions[session_id]["status"] = "error"
                    msg_queue.put({"type": "error", "text": f"Result persistence failed: {persistence_error}"})
                    try:
                        ps.begin_write(result_session)
                        ps.save_result(result_session, task_id, {"id": testcase_id, "execution_token": execution_token, "status": "Failed", "result": {"error": str(persistence_error)}})
                        result_session.commit()
                    except Exception:
                        result_session.rollback()
                    finally:
                        run_sessions[session_id]["stop_requested"] = True
                finally:
                    result_session.close()
            if project_id and project_id in locked_project_ids:
                locked_project_ids.discard(project_id)
                print(f"[API] Project {project_id} execution finished; global lock released.")
            print(f"[Log] Test log saved: {result_log_path}")



    def release_worker():
        if not task_id: return
        with DbSession() as release_session:
            ps.begin_write(release_session)
            task = ps.require(release_session, Task, task_id)
            ps.check_execution_token(task, execution_token)
            if task.execution_worker_id != session_id: raise ps.StateError("Worker admission changed", 409)
            task.execution_worker_id = None
            if task.execution_stop_requested or run_sessions[session_id].get("stop_requested") or run_sessions[session_id]["status"] == "error":
                ps.finish_execution(release_session, task_id, execution_token)
            release_session.commit()

    def guarded_execute():
        import builtins
        saved_stdout, saved_input = sys.stdout, builtins.input
        try:
            if task_id:
                with DbSession() as admission_session:
                    task = ps.require(admission_session, Task, task_id)
                    ps.check_execution_token(task, execution_token)
                    if task.execution_stop_requested:
                        run_sessions[session_id]["stop_requested"] = True
                        run_sessions[session_id]["status"] = "stopped"
                        return
            execute_in_thread()
        except Exception as error:
            sys.stdout, builtins.input = saved_stdout, saved_input
            run_sessions[session_id]["status"] = "error"
            if task_id:
                with DbSession() as failed_session:
                    try:
                        ps.begin_write(failed_session)
                        ps.save_result(failed_session, task_id, {"id": testcase_id, "execution_token": execution_token, "status": "Failed", "result": {"error": str(error)}})
                        failed_session.commit()
                    except Exception:
                        failed_session.rollback()
            msg_queue.put({"type": "error", "text": f"Execution setup failed: {error}"})
        finally:
            try:
                release_worker()
            except Exception as error:
                run_sessions[session_id]["status"] = "error"
                msg_queue.put({"type": "error", "text": f"Execution finalization failed: {error}"})
            run_sessions[session_id]['closed'] = True
            msg_queue.put(None)

    t = threading.Thread(target=guarded_execute, daemon=True)
    run_sessions[session_id]["thread"] = t
    try:
        t.start()
    except Exception as error:
        run_sessions[session_id]["status"] = "error"
        release_worker()
        return jsonify(error=f"Worker could not start: {error}"), 500

    return jsonify({"session_id": session_id, "status": "started"})


# ============================================================================
# API: Update Task TestCase status and BUG ID.
# ============================================================================


# ============================================================================
# API 8: 讀寫 Config.yaml (BMC 設定)
# ============================================================================
@app.route("/api/config", methods=["GET"])
@app.route("/api/settings", methods=["GET", "POST"])
def retired_global_settings():
    return jsonify(error='Connection settings belong to a Task. Use /api/tasks/<task_id>/settings.'), 410


# ============================================================================
# API: Load latest Task execution results.
# ============================================================================




# ============================================================================
# API 6: 中斷測試
# ============================================================================
@app.route("/api/stop", methods=["POST"])
def stop_testcase():
    data = request.json
    session_id = data.get("session_id")
    if session_id in run_sessions:
        run = run_sessions[session_id]
        if run.get("task_id"):
            with DbSession() as stop_session:
                try:
                    ps.begin_write(stop_session)
                    ps.check_execution_token(ps.require(stop_session, Task, run["task_id"]), data.get("execution_token"))
                    if data.get("execution_token") != run.get("execution_token"): raise ps.StateError("Stale execution", 409)
                except ps.StateError as error:
                    return jsonify(error=str(error)), error.code
        run_sessions[session_id]["stop_requested"] = True
        # 餵入哨兵值解除 input_queue.get() 阻塞
        run_sessions[session_id]["input_queue"].put("__STOP__")
        return jsonify({"status": "ok"})
    return jsonify({"error": "Session not found"}), 404


# ============================================================================
# API 7: Server-Sent Events - 串流執行結果
# ============================================================================
@app.route("/api/stream/<session_id>", methods=["GET"])
def stream_results(session_id):
    if session_id not in run_sessions:
        return jsonify({"error": "Execution session not found"}), 404

    sub_queue = queue.Queue()
    run_sessions[session_id]["listeners"].append(sub_queue)

    def generate():
        try:
            # 1. 先回放歷史日誌快照
            history = list(run_sessions[session_id].get("log_history", []))
            for h_msg in history:
                if h_msg.get('type') in ('input_required', 'input_resolved'): continue
                yield f"data: {json.dumps(h_msg, ensure_ascii=False)}\n\n"

            pending = run_sessions[session_id].get('input_prompt')
            if pending is not None:
                yield f"data: {json.dumps({'type': 'input_required', 'text': pending}, ensure_ascii=False)}\n\n"

            if run_sessions[session_id].get('closed'):
                yield f"data: {json.dumps({'type': 'end'})}\n\n"
                return
            # 2. 監聽後續即時廣播
            while True:
                try:
                    msg = sub_queue.get(timeout=60)
                    if msg is None:
                        yield f"data: {json.dumps({'type': 'end'})}\n\n"
                        break
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            if session_id in run_sessions and sub_queue in run_sessions[session_id]["listeners"]:
                run_sessions[session_id]["listeners"].remove(sub_queue)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/")
def index():
    return send_from_directory(os.path.join(BASE_DIR, "static"), "index.html")




ps.install_routes(app, globals())
sc.register(app, globals())
import project_information
project_information.register(app, globals())
tm.register(app, globals())

if __name__ == "__main__":
    print("=" * 60)
    print("  Redfish Test Manager - Web UI")
    print("  Available at http://localhost:5000 or http://<server-ip>:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", debug=True, port=5000, threaded=True, use_reloader=False)

