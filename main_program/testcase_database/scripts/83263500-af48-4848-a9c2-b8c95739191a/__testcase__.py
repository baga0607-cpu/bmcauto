# =============================================================
# TestCase Controller: HEAD Method Support
#
# 【本目錄步驟說明書 / Step Cheat Sheet】
# 本測項驗證 Redfish 是否正確支援 HTTP HEAD 方法。
# 遵循「純動作 -> 純驗證 -> Human Check」的標準四部曲架構。
#
# 1. head_request (純動作):
#    - 對 /redfish/v1 發送 HEAD 請求。
#    - 將回應的 status、body、Link header 存入 context，交由 verify 判斷。
#    - (此步驟無互動模式，固定以無參數執行)
#
# 2. verify_head_response (純驗證):
#    - 從 context 取出回應資料，逐條驗證：
#    - 驗證 b1: 回傳 200，確認 HEAD 方法被支援。
#    - 驗證 b2: Response Body 為空，符合 HEAD 規範。
#    - 驗證 b3: Response Header 中包含 Link 欄位。
#    - 注意：b2/b3 若 BMC 格式特殊，會降級為 [WARNING] 並由 Human Check 確認。
#    - (此步驟無互動模式，固定以無參數執行)
#
# 3. common.human_check:
#    - 通用積木：在任何需要暫停的步驟後方加入此模組，程式會暫停並等待測試員手動輸入 Pass 或 Fail，結果將記錄至 log，"testcase_database.steps.common.human_check"。
#      (你也可以加上自訂提示，例如：["testcase_database.steps.common.human_check", "請確認系統是否重啟？"])
# =============================================================

TESTCASE_NAME = "HEAD_Method_Support"
FAMILY_ID = "TC_Golden_Project_plan_golden_Basic_Function_Test_HEAD_Method_Support"

STEPS = [
    # 純動作：發送 HEAD 請求，結果存入 context
    "testcase_database.steps.Basic_Function_Test.HEAD_Method_Support.head_request",

    # 純驗證：從 context 取出資料，驗證 b1/b2/b3
    "testcase_database.steps.Basic_Function_Test.HEAD_Method_Support.verify_head_response",
    "testcase_database.steps.common.human_check",
]
