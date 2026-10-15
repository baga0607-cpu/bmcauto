# =============================================================
# TestCase Controller: Indicator LED Test
#
# 【本目錄步驟說明書 / Step Cheat Sheet】
# 1. get_led:
#    - 取得目前面板燈號狀態與可用選項，並保存 ETag。
# 2. patch_led (支援 preset):
#    - 【互動模式】：若不帶入 preset (只寫模組路徑)，會自動向 BMC 查詢可用的 LED 狀態並跳出選單讓使用者挑選。
#    - 【全自動模式】：帶入以下 preset 即可自動執行：
#      - "Lit"      : 恆亮
#      - "Blinking" : 閃爍
#      - "Off"      : 關閉
# 3. verify_led:
#    - 自動比對 Redfish API 上的設定是否已確實變更 (純軟體層驗證)。
# 4. common.human_check:
#    - 通用積木：在任何需要暫停的步驟後方加入此模組，程式會暫停並等待測試員手動輸入 Pass 或 Fail，結果將記錄至 log，"testcase_database.common.human_check"。
#      (你也可以加上自訂提示，例如：["testcase_database.common.human_check", "請確認系統是否重啟？"])
# =============================================================

TESTCASE_NAME = "Indicator_LED_Control"
FAMILY_ID = "TC_Golden_Project_plan_golden_Resource_Chassis_Indicator_LED_Control"

STEPS = [
    # ── a. Turn on Indicator LED ──
    "testcase_database.Resource_Chassis.Indicator_LED_Control.get_led",
    ("testcase_database.Resource_Chassis.Indicator_LED_Control.patch_led", "Lit"),
    # "testcase_database.Resource_Chassis.Indicator_LED_Control.patch_led",

    "testcase_database.Resource_Chassis.Indicator_LED_Control.verify_led",
    "testcase_database.common.human_check",
    # ("testcase_database.common.human_check", "請確認燈號是否正確？"),

    # ── b. Set Indicator LED blink ──
    "testcase_database.Resource_Chassis.Indicator_LED_Control.get_led",
    ("testcase_database.Resource_Chassis.Indicator_LED_Control.patch_led", "Blinking"),
    "testcase_database.Resource_Chassis.Indicator_LED_Control.verify_led",
    "testcase_database.common.human_check",

    # ── c. Turn off Indicator LED ──
    "testcase_database.Resource_Chassis.Indicator_LED_Control.get_led",
    ("testcase_database.Resource_Chassis.Indicator_LED_Control.patch_led", "Off"),
    "testcase_database.Resource_Chassis.Indicator_LED_Control.verify_led",
    "testcase_database.common.human_check",
]
