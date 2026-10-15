# =============================================================
# TestCase Controller: Session Service
#
# 【本目錄步驟說明書 / Step Cheat Sheet】
# 1. get_session_service:
#    - 取得目前 Session Service 設定並儲存 ETag。
# 2. patch_session_service (支援 preset):
#    - 【互動模式】：不帶參數，手動輸入 True/False 與秒數。
#    - 【全自動模式】：
#      - "auto"       : 全自動套用預設值 (True / 86400秒)。
#      - "True_86400" : 開啟服務，Timeout 設為 1 天。
#      - "True_300"   : 開啟服務，Timeout 設為 5 分鐘。
#      - "False_86400": 關閉服務。
#      - "True_1000"  : 任意測試值 (修改測試用)。
# 3. verify_session_service:
#    - 自動比對 Redfish API 上的設定是否已確實變更。
# 4. test_timeout:
#    - 建立 Session -> 提取 X-Auth-Token -> 實際發送 GET 驗證 -> 倒數 5 分鐘 -> 驗證失效。
# 5. test_service_disabled:
#    - 驗證 ServiceDisabled 為 False 時是否拒絕建立 Session 並回覆特定錯誤碼，重複步驟3的執行。
# 6. common.human_check:
#    - 通用積木：在任何需要暫停的步驟後方加入此模組，程式會暫停並等待測試員手動輸入 Pass 或 Fail，結果將記錄至 log，"testcase_database.steps.common.human_check"。
#      (你也可以加上自訂提示，例如：["testcase_database.steps.common.human_check", "請確認系統是否重啟？"])
# =============================================================

TESTCASE_NAME = "Session_Service"
FAMILY_ID = "TC_Golden_Project_plan_golden_Session_Service_Session_Service"

STEPS = [
    # ── 1. Get Session Service (檢查預設值) ──
    "testcase_database.steps.Session_Service.Session_Service.get_session_service",
    "testcase_database.steps.common.human_check", # 手動確認預設為 True 與 86400

    # ── 2. Patch Session Service (測試修改功能) ──
    "testcase_database.steps.Session_Service.Session_Service.get_session_service",
    ("testcase_database.steps.Session_Service.Session_Service.patch_session_service", "True_1000"),
    "testcase_database.steps.Session_Service.Session_Service.verify_session_service",
    "testcase_database.steps.common.human_check", # 手動確認 ETag 與 Content 改變

    # ── 3. Check Session Timeout (改為 300 秒並測試) ──
    "testcase_database.steps.Session_Service.Session_Service.get_session_service",
    ("testcase_database.steps.Session_Service.Session_Service.patch_session_service", "True_300"),
    "testcase_database.steps.Session_Service.Session_Service.verify_session_service",
    "testcase_database.steps.Session_Service.Session_Service.test_timeout",
    "testcase_database.steps.common.human_check",

    # ── 4. Service Disabled (關閉服務並測試防護機制) ──
    "testcase_database.steps.Session_Service.Session_Service.get_session_service",
    ("testcase_database.steps.Session_Service.Session_Service.patch_session_service", "False_86400"),
    "testcase_database.steps.Session_Service.Session_Service.verify_session_service",
    "testcase_database.steps.Session_Service.Session_Service.test_service_disabled",
    "testcase_database.steps.common.human_check",

    # ── 5. 還原環境 (Restore) ──
    "testcase_database.steps.Session_Service.Session_Service.get_session_service",
    ("testcase_database.steps.Session_Service.Session_Service.patch_session_service", "True_86400"),
    "testcase_database.steps.Session_Service.Session_Service.verify_session_service",
]
