# =============================================================
# TestCase Controller: Payload Power Control Test
#
# 【本目錄步驟說明書 / Step Cheat Sheet】
# 為了達到 100% 自動驗證，請務必按照「取得 -> 執行 -> 驗證」的順序串接步驟。
#
# 1. get_power_state:
#    - 取得目前電源狀態並存入 context，供後續比對使用。
# 2. post_power_action (支援 preset):
#    - 【互動模式】：若不帶入 preset (只寫模組路徑)，會暫停並跳出互動選單讓使用者手動挑選動作。
#    - 【全自動模式】：帶入以下 preset 即可自動執行對應動作：
#      - "GracefulShutdown"         : 正常關機
#      - "ForceOff"                 : 強制關機
#      - "On"                       : 開機
#      - "PowerCycle"               : 重新啟動
#      - "ForceRestart"             : 強制重啟 (Cold Reset)
#      - "Nmi"                      : 觸發 NMI Kernel Dump (會暫停要求測試員做 OS 準備)
#      - "GracefulShutdownSchedule" : 測試排程關機 (OperationApplyTime: AtMaintenanceWindowStart)
#      - "OnImmediate"              : 測試立即開機 (OperationApplyTime: Immediate)
# 3. verify_power_state:
#    - 自動輪詢 (Polling) BMC，最多等待 3 分鐘，直到狀態改變為期望值才會 PASS。
# 4. common.human_check:
#    - 通用積木：在任何需要暫停的步驟後方加入此模組，程式會暫停並等待測試員手動輸入 Pass 或 Fail，結果將記錄至 log，"testcase_database.steps.common.human_check"。
#      (你也可以加上自訂提示，例如：["testcase_database.steps.common.human_check", "請確認系統是否重啟？"])
# =============================================================

TESTCASE_NAME = "Payload_Power_Control"
FAMILY_ID = "TC_Golden_Project_plan_golden_Resource_Systems_Payload_Power_Control"

STEPS = [
    # ── 1. 基本電源操作測試 ──
    # a. GracefulShutdown
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.get_power_state",
    ("testcase_database.steps.Resource_Systems.Payload_Power_Control.post_power_action", "GracefulShutdown"),
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.verify_power_state",
    "testcase_database.steps.common.human_check", 

    # b. ForceOff (若目前為關機，此步驟會提早通過，為了嚴謹可先開機)
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.get_power_state",
    ("testcase_database.steps.Resource_Systems.Payload_Power_Control.post_power_action", "On"),
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.verify_power_state",
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.get_power_state",
    ("testcase_database.steps.Resource_Systems.Payload_Power_Control.post_power_action", "ForceOff"),
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.verify_power_state",
    "testcase_database.steps.common.human_check", 

    # c. On
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.get_power_state",
    ("testcase_database.steps.Resource_Systems.Payload_Power_Control.post_power_action", "On"),
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.verify_power_state",
    "testcase_database.steps.common.human_check", 

    # d. PowerCycle
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.get_power_state",
    ("testcase_database.steps.Resource_Systems.Payload_Power_Control.post_power_action", "PowerCycle"),
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.verify_power_state",
    "testcase_database.steps.common.human_check", 

    # e. ForceRestart
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.get_power_state",
    ("testcase_database.steps.Resource_Systems.Payload_Power_Control.post_power_action", "ForceRestart"),
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.verify_power_state",
    "testcase_database.steps.common.human_check", 

    # f. NMI (腳本內會暫停，提示測試員登入 OS 輸入指令)
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.get_power_state",
    ("testcase_database.steps.Resource_Systems.Payload_Power_Control.post_power_action", "Nmi"),
    "testcase_database.steps.common.human_check", # NMI 需要測試員手動確認 Kernel Dump


    # ── 2. 排程關機測試 (OperationApplyTime: AtMaintenanceWindowStart) ──
    # a. 發送排程指令 (預期回傳 202)
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.get_power_state",
    ("testcase_database.steps.Resource_Systems.Payload_Power_Control.post_power_action", "GracefulShutdownSchedule"),
    # b. 系統會自動倒數並監控，直到時間超過 MaintenanceWindowStartTime 且成功關機為止
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.verify_power_state",
    "testcase_database.steps.common.human_check", 


    # ── 3. 立即開機測試 (OperationApplyTime: Immediate) ──
    # a. 確保目前在關機狀態下，發送立即開機指令 (預期回傳 204)
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.get_power_state",
    ("testcase_database.steps.Resource_Systems.Payload_Power_Control.post_power_action", "OnImmediate"),
    # b. 驗證立即開機成功
    "testcase_database.steps.Resource_Systems.Payload_Power_Control.verify_power_state",
    "testcase_database.steps.common.human_check", 
]
