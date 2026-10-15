import yaml
import urllib3
import redfish
import importlib
import inspect
import logging
import os
import sys
import subprocess
import sqlite3

try:
    from main_program.console_helper import ConsoleClient
except ModuleNotFoundError:
    from console_helper import ConsoleClient

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. 建立日誌系統
#    - result.log：人工互動紀錄（Pass/Fail、場景執行）
#    - api.log   ：Redfish API 詳細流水帳（請求/回應 Body）
# ==========================================
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# result.log：同時輸出至 CLI 與檔案
logger = logging.getLogger("PlaybookRunner")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
file_handler = logging.FileHandler("result.log", mode='a', encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# api.log：只寫入檔案，不輸出至 CLI
api_logger = logging.getLogger("APILogger")
api_logger.setLevel(logging.DEBUG)
api_logger.propagate = False   # 不往上傳遞，避免混入 CLI
api_file_handler = logging.FileHandler("api.log", mode='a', encoding='utf-8')
api_file_handler.setFormatter(formatter)
api_logger.addHandler(api_file_handler)


# ==========================================
# 2. Redfish API Logging Proxy
#    透明代理：攔截所有 API 呼叫，記錄請求與完整回應
#    對 step 模組完全透明，使用方式與原始 client 完全相同
# ==========================================
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

class LoggingRedfishClient:
    """Redfish client 的透明代理，自動將每次 API 請求與回應寫入 api.log"""

    def __init__(self, real_client):
        self._client = real_client
        self._console_client = None

    def _get_console_client(self):
        if self._console_client is None:
            config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            cs = config.get("console_server", {})
            if cs.get("host"):
                print("  [Console] 偵測到配置 Console Server，正在建立連線代理...")
                self._console_client = ConsoleClient(config)
                self._console_client.connect()
                print("  [Console] Console Server 連線成功！")
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
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            if config.get("console_server", {}).get("host") and interface_type in ("kcs", "serial"):
                use_remote = True

        cmd = ["ipmitool"] + ipmitool_args + command_args
        cmd_str = " ".join(cmd)

        if use_remote:
            print(f"  [Console][IPMI] 遠端執行指令: {cmd_str}")
            api_logger.info(f"[Console][IPMI] {cmd_str}")
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
                print(f"         遠端 IPMI 執行失敗: {e}")
                api_logger.error(f"[Console][IPMI] 遠端執行失敗: {e}")
                return {
                    "stdout": "",
                    "stderr": str(e),
                    "returncode": 1
                }
        else:
            print(f"  [IPMI] 本機執行指令: {cmd_str}")
            api_logger.info(f"[IPMI] {cmd_str}")
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                return {
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "returncode": res.returncode
                }
            except Exception as e:
                print(f"         本機 IPMI 執行失敗: {e}")
                api_logger.error(f"[IPMI] 本機執行失敗: {e}")
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
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            if config.get("console_server", {}).get("host") and interface_type in ("kcs", "serial"):
                use_remote = True

        raw_args = ["raw", f"0x{netfn:02X}", f"0x{command:02X}"] + [f"0x{b:02X}" for b in data]
        cmd = ["ipmitool"] + ipmitool_args + raw_args
        cmd_str = " ".join(cmd)

        if use_remote:
            print(f"  [Console][IPMI] 遠端執行指令: {cmd_str}")
            api_logger.info(f"[Console][IPMI] {cmd_str}")
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
                    print(f"         IPMI 成功: {parsed_data}")
                    api_logger.debug(f"  IPMI 成功, 回傳: {parsed_data}")
                    return IpmiResponse(stdout_str, "", 0, parsed_data)
            except Exception as e:
                print(f"         遠端 IPMI 執行失敗: {e}")
                api_logger.error(f"[Console][IPMI] 遠端執行失敗: {e}")
                return IpmiResponse("", str(e), 1, [])
        else:
            print(f"  [IPMI] 本機執行指令: {cmd_str}")
            api_logger.info(f"[IPMI] {cmd_str}")
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
                    print(f"         IPMI 成功: {parsed_data}")
                    api_logger.debug(f"  IPMI 成功, 回傳: {parsed_data}")
                else:
                    print(f"         IPMI 失敗: {res.stderr.strip()}")
                    api_logger.debug(f"  IPMI 失敗, 錯誤: {res.stderr.strip()}")
                    
                return resp
            except Exception as e:
                print(f"         IPMI 異常: {e}")
                api_logger.error(f"  IPMI 異常: {e}")
                return IpmiResponse("", str(e), -1)

    def _log_response(self, method, uri, payload, resp):
        """統一格式化並寫入 api.log，同時將摘要輸出到 CLI"""
        status = getattr(resp, 'status', 'N/A')

        # 根據狀態碼決定前綴標記
        tag = "[API]" if isinstance(status, int) and status < 300 else "[API][WARNING]"

        # --- CLI 即時輸出（摘要） ---
        print(f"  {tag} {method} {uri}  ->  HTTP {status}")

        # 若有 Request Body，也印到 CLI
        if payload:
            print(f"         Request  : {payload}")

        # 取得回應 Body
        body = getattr(resp, 'text', None) or getattr(resp, 'dict', None)
        if body:
            print(f"         Response : {body}")

        # --- api.log 詳細寫入（完整紀錄，不截斷） ---
        api_logger.info(f"{method} {uri}  ->  HTTP {status}")
        if payload:
            api_logger.debug(f"  Request  Payload : {payload}")
        if body:
            api_logger.debug(f"  Response Body    : {body}")
        else:
            api_logger.debug(f"  Response Body    : (empty)")

    def get(self, uri, **kwargs):
        resp = self._client.get(uri, **kwargs)
        self._log_response("GET", uri, None, resp)
        return resp

    def patch(self, uri, body=None, headers=None, **kwargs):
        resp = self._client.patch(uri, body=body, headers=headers, **kwargs)
        self._log_response("PATCH", uri, body, resp)
        return resp

    def post(self, uri, body=None, **kwargs):
        resp = self._client.post(uri, body=body, **kwargs)
        self._log_response("POST", uri, body, resp)
        return resp

    def put(self, uri, body=None, headers=None, **kwargs):
        resp = self._client.put(uri, body=body, headers=headers, **kwargs)
        self._log_response("PUT", uri, body, resp)
        return resp

    def delete(self, uri, **kwargs):
        resp = self._client.delete(uri, **kwargs)
        self._log_response("DELETE", uri, None, resp)
        return resp

    def logout(self):
        if self._console_client:
            try:
                print("  [Console] 正在關閉 Console Server 連線...")
                self._console_client.close()
            except Exception:
                pass
            self._console_client = None
        return self._client.logout()

    def __getattr__(self, name):
        """其他屬性或方法直接轉發給真實 client"""
        return getattr(self._client, name)


# ==========================================
# 3. 自動處理設定檔與全域連線
# ==========================================
def init_redfish_client():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)["redfish"]
    
    print(f"\n[系統] 正在與 BMC {conf['host']} 進行握手與登入，這可能需要 5-15 秒，請稍候...")
    real_client = redfish.redfish_client(
        base_url=conf["host"],
        username=conf["username"],
        password=conf["password"],
        default_prefix="/redfish/v1",
        timeout=15,
        max_retry=3
    )
    real_client.login(auth="basic")
    logger.info(f"系統已成功登入 BMC: {conf['host']}")
    print("[系統] 登入完成！\n")
    
    # 用 Logging Proxy 包裝，所有 API 呼叫自動寫入 api.log
    api_logger.info(f"======== 新連線建立：{conf['host']} ========")
    return LoggingRedfishClient(real_client), conf

# ==========================================
# 4. 讀取劇本清單與渲染選單 (已升級為資料庫動態載入)
# ==========================================
CURRENT_PROJECT = None
CURRENT_PLAN = None

def choose_project_and_plan(db_path):
    global CURRENT_PROJECT, CURRENT_PLAN
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 取得所有 Project 列表
        cursor.execute("SELECT DISTINCT project FROM testcases")
        projects = [row[0] for row in cursor.fetchall() if row[0]]
        if not projects:
            conn.close()
            return False
            
        # 如果只有一個 Project，自動選取；否則列出選單供使用者選擇
        if len(projects) == 1:
            CURRENT_PROJECT = projects[0]
        else:
            print("\n" + "=" * 50)
            print("[主選單] 請選擇測試專案 (Project)：")
            for i, proj in enumerate(projects, 1):
                print(f" {i:2}. {proj}")
            print("=" * 50)
            while True:
                choice = input(f"請輸入專案代碼 (1-{len(projects)}): ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(projects):
                    CURRENT_PROJECT = projects[int(choice) - 1]
                    break
                print("無效的選擇，請重新輸入。")
                
        # 2. 取得該 Project 底下的所有 Plan
        cursor.execute("SELECT DISTINCT plan_id FROM testcases WHERE project = ?", (CURRENT_PROJECT,))
        plans = [row[0] for row in cursor.fetchall() if row[0]]
        if not plans:
            conn.close()
            return False
            
        # 如果該專案只有一個 Plan，自動選取；否則列出選單供使用者選擇
        if len(plans) == 1:
            CURRENT_PLAN = plans[0]
        else:
            print("\n" + "=" * 50)
            print(f"專案：[{CURRENT_PROJECT}]")
            print("[主選單] 請選擇測試計畫 (Plan)：")
            for i, plan in enumerate(plans, 1):
                print(f" {i:2}. {plan}")
            print("=" * 50)
            while True:
                choice = input(f"請輸入計畫代碼 (1-{len(plans)}): ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(plans):
                    CURRENT_PLAN = plans[int(choice) - 1]
                    break
                print("無效的選擇，請重新輸入。")
                
        conn.close()
        return True
    except Exception as e:
        print(f"[警告] 讀取專案計畫失敗: {e}")
        return False

def load_scenarios_from_yaml():
    scenario_path = os.path.join(os.path.dirname(__file__), "scenarios.yaml")
    if not os.path.exists(scenario_path):
        print(f"[錯誤] 找不到劇本檔案: {scenario_path}")
        sys.exit(1)
    with open(scenario_path, "r", encoding="utf-8") as f:
        # scenarios.yaml 雖然目前不被主流程使用，但仍保留做為 fallback 與歷史參考
        return yaml.safe_load(f)

def load_scenarios():
    db_path = os.path.join(os.path.dirname(__file__), "..", "web_ui", "workspace", "testcase_meta.db")
    
    # 判斷是否使用資料庫
    if os.path.exists(db_path):
        global CURRENT_PROJECT, CURRENT_PLAN
        # 如果還沒有選過專案計畫，在此處進行選擇
        if CURRENT_PROJECT is None or CURRENT_PLAN is None:
            success = choose_project_and_plan(db_path)
            if not success:
                print("[警告] 無法從資料庫取得專案計畫，改為載入 scenarios.yaml")
                return load_scenarios_from_yaml()
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT category, display_name, script_path FROM testcases WHERE project = ? AND plan_id = ?",
                (CURRENT_PROJECT, CURRENT_PLAN)
            )
            rows = cursor.fetchall()
            conn.close()
            
            scenarios = {}
            for category, display_name, script_path in rows:
                if not category or not display_name or not script_path:
                    continue
                if category not in scenarios:
                    scenarios[category] = {}
                scenarios[category][display_name] = script_path
            
            # 若資料庫中沒有此計畫的任何測項，則 fallback
            if not scenarios:
                print(f"[警告] 專案 [{CURRENT_PROJECT}] 計畫 [{CURRENT_PLAN}] 下無任何測試案例，改為載入 scenarios.yaml")
                return load_scenarios_from_yaml()
                
            return scenarios
        except Exception as e:
            print(f"[警告] 讀取資料庫測項失敗: {e}，改為載入 scenarios.yaml")
            return load_scenarios_from_yaml()
    else:
        return load_scenarios_from_yaml()

def display_menu(scenarios):
    if not scenarios:
        print("[錯誤] scenarios.yaml 內部沒有任何劇本設定！")
        sys.exit(1)
        
    categories = list(scenarios.keys())
    db_path = os.path.join(os.path.dirname(__file__), "..", "web_ui", "workspace", "testcase_meta.db")
    is_db_mode = os.path.exists(db_path) and CURRENT_PROJECT is not None
    
    while True:
        # ── 顯示第一層選單 (Category) ──
        print("\n" + "=" * 50)
        print("      Redfish Interactive Scenario Runner")
        if is_db_mode:
            print(f"      當前專案: {CURRENT_PROJECT} | 計畫: {CURRENT_PLAN}")
        print("=" * 50)
        print("[主選單] 請選擇測試類別：")
        for i, category in enumerate(categories, 1):
            if category == "Custom":
                print(f" {i:2}. {category} (自訂測試步驟)")
            else:
                print(f" {i:2}. {category}")
        
        extra_options = {}
        curr_idx = len(categories) + 1
        if is_db_mode:
            print(f" {curr_idx:2}. 切換專案/計畫")
            extra_options[str(curr_idx)] = "switch"
            curr_idx += 1
            
        print("  0. 離開程式")
        print("=" * 50)
        
        try:
            cat_choice = input(f"請輸入類別代碼 (0-{curr_idx - 1}): ").strip()
            if cat_choice == "0":
                print("\n[系統] 測試框架結束運行。")
                sys.exit(0)
                
            if cat_choice in extra_options:
                action = extra_options[cat_choice]
                if action == "switch":
                    # 重新選擇專案與計畫
                    choose_project_and_plan(db_path)
                    return "switch_project", None
            
            try:
                cat_idx = int(cat_choice)
            except ValueError:
                print("無效的選擇，請重新輸入。")
                continue
                
            if 1 <= cat_idx <= len(categories):
                selected_category = categories[cat_idx - 1]
                category_content = scenarios[selected_category]
                
                # 如果是 Custom (list格式) 或舊的平坦格式(str格式)，直接回傳
                if isinstance(category_content, (list, str)):
                    return selected_category, category_content
                
                # ── 顯示第二層選單 (TestCase) ──
                testcases = list(category_content.keys())
                while True:
                    print("\n" + "=" * 50)
                    print(f"類別：[{selected_category}]")
                    print("=" * 50)
                    print("請選擇測試案例：")
                    for j, tc_name in enumerate(testcases, 1):
                        print(f" {j:2}. {tc_name}")
                    print("  0. 返回上層選單")
                    print("=" * 50)
                    
                    tc_choice = input(f"請輸入測項代碼 (0-{len(testcases)}): ").strip()
                    tc_idx = int(tc_choice)
                    if tc_idx == 0:
                        break # 返回第一層
                    
                    if 1 <= tc_idx <= len(testcases):
                        selected_tc = testcases[tc_idx - 1]
                        # 返回組合名稱與腳本路徑
                        return f"{selected_category}/{selected_tc}", category_content[selected_tc]
                    else:
                        print("無效的選擇，請重新輸入。")
            else:
                print("無效的選擇，請重新輸入。")
                
        except ValueError:
            print("無效的選擇，請重新輸入。")
        except KeyboardInterrupt:
            print("\n\n[系統] 收到中斷訊號，測試框架結束運行。")
            sys.exit(0)

# ==========================================
# 5. 劇本主引擎 (互動式攔截器)
# ==========================================
def main():
    while True:
        try:
            # 讀取並選擇劇本
            scenarios = load_scenarios()
            scenario_name, playbook = display_menu(scenarios)
            if scenario_name == "switch_project":
                continue
            
            print(f"\n[系統] 您選擇了劇本功能: {scenario_name}")
            
            # 判斷模式：字串 = 標準模式，清單 = Custom 模式
            if isinstance(playbook, str):
                # 標準模式：載入 __testcase__.py 取得步驟清單
                try:
                    controller_module = importlib.import_module(f"{playbook}.__testcase__")
                    playbook = controller_module.STEPS
                    testcase_display_name = getattr(controller_module, "TESTCASE_NAME", scenario_name)
                    print(f"[系統] TestCase: {testcase_display_name}")
                except ModuleNotFoundError:
                    print(f"[錯誤] 在 '{playbook}' 找不到 __testcase__.py！請確認該資料夾內已建立 Controller 檔案。")
                    continue
            else:
                # Custom 模式：直接使用清單中的步驟
                print(f"[系統] 模式： Custom 自訂場景")
            
            # 自動植入總結判定積木 (如果還沒有的話)
            judgement_step = "testcase_database.steps.common.final_judgement"
            if judgement_step not in playbook and not any(isinstance(s, tuple) and s[0] == judgement_step for s in playbook):
                playbook.append(judgement_step)
                
            print("[系統] 劇本即將啟動，包含以下步驟：")
            for step in playbook:
                print(f"  - {step}")
            print("\n")
            
            # 建立唯一連線
            try:
                client, conf = init_redfish_client()
            except Exception as e:
                print(f"[錯誤] 無法連線至伺服器: {e}")
                continue

            # 建立 context 共享字典，在 TestCase 所有步驟間傳遞狀態
            context = {
                "_scenario_name": scenario_name,
                "_last_step_name": "",
                "_tc_status": "PASS",  # 初始化整條 TC 的狀態為 PASS
                "redfish": conf
            }
                
            logger.info(f"--- 啟動劇本測試: {scenario_name} ---")
            api_logger.info(f"--- 啟動劇本測試: {scenario_name} ---")
            
            try:
                for index, entry in enumerate(playbook, 1):
                    
                    # ── 支援兩種 STEPS 格式 ────────────────────────────────────────
                    # 格式 A：純字串 → Interactive 模式，不傳入 preset
                    # 格式 B： Tuple (module, preset) → Preset 模式，自動帶入參數
                    if isinstance(entry, (list, tuple)) and len(entry) == 2:
                        module_name, preset = entry[0], entry[1]
                    else:
                        module_name, preset = entry, None
                    
                    try:
                        # 動態導入指定層級的包
                        step_module = importlib.import_module(module_name)
                    except ModuleNotFoundError:
                        print(f"[錯誤] 找不到動作模組: {module_name} (請確認 testcase_database 目錄結構與拼寫)")
                        continue

                    step_name = getattr(step_module, "STEP_NAME", module_name)
                    step_desc = getattr(step_module, "STEP_DESCRIPTION", None)
                    
                    print("\n" + "-" * 55)
                    print(f">>> [{index}/{len(playbook)}] 正在執行步驟 : {step_name}")
                    if preset is not None:
                        print(f"    預設參數  : {preset}")
                    if step_desc:
                        print(f"    說明      : {step_desc}")
                    print("-" * 55)
                    
                    try:
                        # 檢查 execute() 支援的參數（向下相容舊步驟）
                        # 優先級：context + preset > context only > preset only > 無參數
                        sig = inspect.signature(step_module.execute)
                        has_context = 'context' in sig.parameters
                        has_preset  = 'preset'  in sig.parameters

                        if has_context and has_preset and preset is not None:
                            step_module.execute(client, context=context, preset=preset)
                        elif has_context:
                            step_module.execute(client, context=context)
                        elif has_preset and preset is not None:
                            step_module.execute(client, preset=preset)
                        else:
                            step_module.execute(client)
                        
                        # execute() 後再取一次 STEP_NAME（支援動態更新，如 led_control.py）
                        step_name = getattr(step_module, "STEP_NAME", step_name)
                        
                        if step_name == "總結判定 (Final Judgement)":
                            logger.info(f"====== [TC PASS] {scenario_name} 所有步驟完美通過！ ======")
                        else:
                            logger.info(f"[Step OK] {scenario_name} -> {step_name}")
                            
                        print("[OK] 步驟執行完成。")
                        
                        # 儲存供下一步使用的上下文資訊
                        context["_last_step_name"] = step_name
                        context["_last_step_preset"] = preset
                        
                    except Exception as e:
                        step_name = getattr(step_module, "STEP_NAME", step_name)
                        logger.error(f"[Step Exception] 執行 {step_name} 時發生異常: {e}")
                        print(f"步驟異常，已將錯誤寫入 Log。")
                        context["_tc_status"] = "FAIL"
                        
            finally:
                client.logout()
                logger.info(f"--- 劇本測試結束: {scenario_name} ---")
                api_logger.info(f"--- 劇本測試結束: {scenario_name} ---\n")
                print(f"\n=== 劇本 [{scenario_name}] 執行完畢！")
                print(f"    互動紀錄 -> result.log")
                print(f"    API 詳細 -> api.log")
                
                # 在日誌檔案中自動添加一個空白行區隔
                with open("result.log", "a", encoding="utf-8") as rf:
                    rf.write("\n")
                    
        except KeyboardInterrupt:
            # 攔截包含選單介面的 Ctrl+C 結束信號
            print("\n\n[系統] 收到中斷訊號 (Ctrl+C)，安全退出測試平台。")
            sys.exit(0)

if __name__ == "__main__":
    main()

