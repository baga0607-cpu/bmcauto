# =============================================================
# TestCase Controller: Session Authentication
#
# 【本目錄步驟說明書 / Step Cheat Sheet】
# 本測項完美落實「動作積木」與「驗證積木」的職責分離。
#
# 1. post_session (純動作):
#    - 無論底層是否有 Basic Auth，強制以無授權狀態發送 POST 到 /Sessions。
#    - 將取得的 Token 與 Session ID 存入 context。
#    - 【互動模式】：不帶入 preset (只寫模組路徑)，程式會暫停並跳出表單讓使用者手動填寫帳號密碼。
#    - 【全自動模式】：帶入以下 preset 即可自動執行：
#      - "auto"       : 全自動寫入預設帳密 (administrator / advantech)。
#      - "帳號_密碼"  : (如 "operator_1234") 全自動寫入自訂帳密。
# 2. verify_session_created (純驗證):
#    - 拿前一步取得的 Token 發送 GET，驗證 Collection 內真的出現了該 Session ID。
# 3. delete_session (純動作):
#    - 帶上 Token 發送 DELETE 摧毀該 Session，並紀錄回傳 Status。
# 4. verify_session_deleted (純驗證):
#    - 驗證 DELETE 的回傳值必須為 204 且為空。
#    - 再次使用作廢的 Token 敲門，驗證是否確實收到 401 拒絕。
# 5. common.human_check:
#    - 通用積木：在任何需要暫停的步驟後方加入此模組，程式會暫停並等待測試員手動輸入 Pass 或 Fail，結果將記錄至 log，"testcase_database.common.human_check"。
#      (你也可以加上自訂提示，例如：["testcase_database.common.human_check", "請確認系統是否重啟？"])
# =============================================================

TESTCASE_NAME = "Session_Authentication"
FAMILY_ID = "TC_Golden_Project_plan_golden_Session_Service_Session_Authentication"

STEPS = [
    # POST 建立 Session (純動作) ──
    ("testcase_database.Session_Service.Session_Authentication.post_session", "auto"),
    
    # 驗證 Session 建立成功 (純驗證) ──
    "testcase_database.Session_Service.Session_Authentication.verify_session_created",
    "testcase_database.common.human_check",
    
    # DELETE 刪除 Session (純動作) ──
    "testcase_database.Session_Service.Session_Authentication.delete_session",
    # 驗證 Session 刪除與登出成功 (純驗證) ──
    "testcase_database.Session_Service.Session_Authentication.verify_session_deleted",
    "testcase_database.common.human_check",
]
