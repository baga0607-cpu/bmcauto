# =============================================================
# 測試 Session 逾時機制 (Test Timeout)
# =============================================================
import time
import sys

STEP_NAME = "測試 Session 逾時機制 (Test Timeout)"
STEP_DESCRIPTION = "建立新 Session 並等待 5 分鐘，驗證其是否自動失效。"
STEP_METADATA = {
    "requires": [],
    "produces": [],
    "type": "automated",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，會自動建立 Session 並倒數 5 分鐘驗證淨時。",
}

SESSION_URI = "/redfish/v1/SessionService/Sessions"

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    # 1. POST 建立 Session
    post_headers = {"Content-Type": "application/json"}
    post_body = {
        "UserName": "operator",
        "Password": "advantech"
    }
    
    print("  嘗試建立新 Session (使用預設帳密 operator/advantech)...")
    resp_post = client.post(SESSION_URI, body=post_body, headers=post_headers)
    if getattr(resp_post, "status", None) != 201:
        raise Exception(f"失敗：建立 Session 時未能取得 201，收到 {getattr(resp_post, 'status', 'None')}")
        
    data_post = getattr(resp_post, "dict", {})
    new_session_id = data_post.get("@odata.id")
    if not new_session_id and hasattr(resp_post, "get_header"):
        new_session_id = resp_post.get_header("Location")
        
    if not new_session_id:
         new_session_id = SESSION_URI
         
    x_auth_token = None
    
    # Python redfish library 的 response 通常具有 getheader 或 headers 屬性
    if hasattr(resp_post, "getheader"):
        x_auth_token = resp_post.getheader("X-Auth-Token")
    elif hasattr(resp_post, "headers") and isinstance(resp_post.headers, dict):
        x_auth_token = resp_post.headers.get("X-Auth-Token")
    elif hasattr(resp_post, "get_header"):
        x_auth_token = resp_post.get_header("X-Auth-Token")
        
    if hasattr(resp_post, "getheader") and not new_session_id:
        new_session_id = resp_post.getheader("Location")
    elif hasattr(resp_post, "headers") and not new_session_id:
        new_session_id = getattr(resp_post, "headers", {}).get("Location")
    
    if not x_auth_token:
        print("   [警告] 無法從 Header 取得 X-Auth-Token，後續將使用預設 Session 連線測試。")
    else:
        # 印出完整 Token
        print(f"  [OK] Session 建立成功。成功取得 X-Auth-Token: [{x_auth_token}]")
        print("  嘗試使用該 X-Auth-Token 發送 GET 請求進行連線測試...")
        test_headers = {"X-Auth-Token": x_auth_token}
        resp_test = client.get(SESSION_URI, headers=test_headers)
        if getattr(resp_test, "status", None) != 200:
             raise Exception(f"失敗：使用新 X-Auth-Token 測試連線失敗，狀態碼: {getattr(resp_test, 'status', 'None')}")
        print("  [OK] 新 Token 測試連線成功 (200 OK)。")
    
    # 2. 自動倒數 5 分鐘
    target_time = 300
    print()
    while target_time > 0:
        mins, secs = divmod(target_time, 60)
        sys.stdout.write(f"\r  -> 倒數計時等待逾時: {mins:02d}:{secs:02d} ... ")
        sys.stdout.flush()
        time.sleep(1)
        target_time -= 1
    sys.stdout.write("\r  倒數結束！開始驗證自動登出機制...                  \n")
    
    # 3. 驗證是否失效
    check_headers = {"X-Auth-Token": x_auth_token} if x_auth_token else {}
    resp_check = client.get(new_session_id, headers=check_headers)
    status_check = getattr(resp_check, "status", None)
    
    if status_check in [200, 201]:
        print(f"   [FAIL] 5 分鐘已過，系統仍回覆 {status_check}，未能自動移除 Session 或撤銷 Token。")
        raise Exception("逾時測試失敗：Session 資源依然存活。")
    else:
        print(f"   [PASS] Timeout 生效！系統已清除該 Session 或 Token 失效 (Status: {status_check})")
