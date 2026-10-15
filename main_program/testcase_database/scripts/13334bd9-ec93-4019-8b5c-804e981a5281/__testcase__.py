# =============================================================
# TestCase Controller: Boot Option Test
#
# 【本目錄步驟說明書 / Step Cheat Sheet】
# 為了確保 Boot Option 成功套用，流程結尾必須包含「伺服器重啟」與「人工確認」。
#
# 1. get_system:
#    - 取得目前系統設定與 ETag。PATCH 前必須執行。
# 2. patch_boot_option (支援 preset):
#    - 【互動模式】：不帶入 preset (只寫模組路徑)，程式會暫停並跳出互動選單讓使用者手動挑選動作。
#    - 【全自動模式】：帶入以下 preset 即可自動執行對應動作：
#      - "Hdd"       : 下次開機從硬碟啟動
#      - "Pxe"       : 下次開機從網路 PXE 啟動
#      - "BiosSetup" : 下次開機進入 BIOS 設定選單
#      - "None"      : 取消一次性開機設定
# 3. verify_boot_option:
#    - 自動比對 Redfish API 上的設定是否已確實變更。
# 4. common.human_check:
#    - 通用積木：在任何需要暫停的步驟後方加入此模組，程式會暫停並等待測試員手動輸入 Pass 或 Fail，結果將記錄至 log，"testcase_database.steps.common.human_check"。
#      (你也可以加上自訂提示，例如：["testcase_database.steps.common.human_check", "請確認系統是否重啟？"])
# =============================================================

TESTCASE_NAME = "Boot_Option"
FAMILY_ID = "TC_Golden_Project_plan_golden_Resource_Systems_Boot_Option"

STEPS = [
    # 測試 1: Boot from HDD
    "testcase_database.steps.Resource_Systems.Boot_Option.get_system",
    ("testcase_database.steps.Resource_Systems.Boot_Option.patch_boot_option", "Hdd"),
    "testcase_database.steps.Resource_Systems.Boot_Option.verify_boot_option",
    # -- 跨模組呼叫：發送重開機指令以套用 Boot Option --
    ("testcase_database.steps.Resource_Systems.Payload_Power_Control.post_power_action", "ForceRestart"),
    "testcase_database.steps.common.human_check",

    # 測試 2: Boot into BiosSetup (Setup Menu)
    "testcase_database.steps.Resource_Systems.Boot_Option.get_system",
    ("testcase_database.steps.Resource_Systems.Boot_Option.patch_boot_option", "BiosSetup"),
    "testcase_database.steps.Resource_Systems.Boot_Option.verify_boot_option",
    # -- 跨模組呼叫：發送重開機指令以套用 Boot Option --
    ("testcase_database.steps.Resource_Systems.Payload_Power_Control.post_power_action", "ForceRestart"),
    "testcase_database.steps.common.human_check",
    
    #測試 3: Boot from PXE 
    "testcase_database.steps.Resource_Systems.Boot_Option.get_system",
    ("testcase_database.steps.Resource_Systems.Boot_Option.patch_boot_option", "Pxe"),
    "testcase_database.steps.Resource_Systems.Boot_Option.verify_boot_option",
    # -- 跨模組呼叫：發送重開機指令以套用 Boot Option --
    ("testcase_database.steps.Resource_Systems.Payload_Power_Control.post_power_action", "ForceRestart"),
    "testcase_database.steps.common.human_check",
]
