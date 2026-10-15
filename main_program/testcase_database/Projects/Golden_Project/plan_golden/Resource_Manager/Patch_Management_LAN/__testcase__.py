# =============================================================
# TestCase Controller: Ethernet Interface Test
#
# 【本目錄步驟說明書 / Step Cheat Sheet】
# 1. get_manager: 已整合至 list_interfaces，預設使用 manager_id="0"。
# 2. list_interfaces (列出並選擇介面):
#    - 【互動模式】：不帶入 preset (只寫模組路徑)，程式會暫停並跳出互動選單讓使用者手動選擇介面。
#    - 【全自動模式】：帶入以下 preset 即可自動執行：
#      - "auto" : 自動選擇 index 2 的介面 (預設為 Patch Management LAN 介面)。
#      - "1", "3" 等數字字串 : 自動選擇對應 index 的介面 (如 "1" 選第 1 個)。
# 3. get_interface: 取得選定介面的當前設定值與 ETag，存入 context。(無參數)
# 4. patch_interface (修改網路設定):
#    - 【互動模式】：不帶入 preset (只寫模組路徑)，程式會逐欄顯示預設值並讓使用者確認或修改。
#    - 【全自動模式】：帶入以下 preset 即可自動執行：
#      - "auto"                              : 直接使用 DEFAULT_BODY 預設值發送，略過所有詢問。
#      - "enabled_ip_mask_gateway"           : 自訂格式，用底線分隔四個欄位。
#        例："False_172.21.73.33_255.255.0.0_0.0.0.0"
#        例："True_192.168.1.100_255.255.255.0_192.168.1.1"
# 5. verify_interface: 自動比對 PATCH 後的設定是否與預期相符。(無參數)
# 6. common.human_check:
#    - 通用積木：在任何需要暫停的步驟後方加入此模組，程式會暫停並等待測試員手動輸入 Pass 或 Fail，結果將記錄至 log，"testcase_database.common.human_check"。
#      (你也可以加上自訂提示，例如：["testcase_database.common.human_check", "請確認系統是否重啟？"])
# =============================================================

TESTCASE_NAME = "Patch_Management_LAN"
FAMILY_ID = "TC_Golden_Project_plan_golden_Resource_Manager_Patch_Management_LAN"

STEPS = [
    # 取得 Manager ID (預設 0) 並列出介面，選擇 interface_id -> 寫入 context
    ("testcase_database.Resource_Manager.Patch_Management_LAN.list_interfaces", "auto"),
    # "testcase_database.Resource_Manager.Patch_Management_LAN.list_interfaces",

    #人工驗證
    "testcase_database.common.human_check",
    
    # GET 選定介面，取得當前值與 ETag -> 寫入 context
    "testcase_database.Resource_Manager.Patch_Management_LAN.get_interface",
    # 顯示預設 Body，允許使用者修改後 PATCH
    ("testcase_database.Resource_Manager.Patch_Management_LAN.patch_interface", "auto"),
    # "testcase_database.Resource_Manager.Patch_Management_LAN.patch_interface",

    # 自動驗證：比對 PATCH 結果是否與期望值相符
    ("testcase_database.Resource_Manager.Patch_Management_LAN.verify_interface"),
    #人工驗證
    "testcase_database.common.human_check",
]

