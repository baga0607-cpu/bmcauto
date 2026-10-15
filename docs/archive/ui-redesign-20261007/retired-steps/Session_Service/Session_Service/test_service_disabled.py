# =============================================================
# 測試 Service Disabled (Test Service Disabled)
# =============================================================

STEP_NAME = "測試 Service Disabled 機制"
STEP_DESCRIPTION = "驗證當 ServiceEnabled 為 False 時，是否拒絕建立 Session。"
STEP_METADATA = {
    "requires": [],
    "produces": [],
    "type": "automated",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，必須在 patch_session_service 關閉服務後執行。",
}

SESSION_URI = "/redfish/v1/SessionService/Sessions"

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    # 1. 嘗試 POST 建立 Session
    post_headers = {"Content-Type": "application/json"}
    post_body = {
        "UserName": "operator",
        "Password": "<password>"
    }
    
    print("  在服務關閉的情況下，嘗試建立新 Session...")
    resp_post = client.post(SESSION_URI, body=post_body, headers=post_headers)
    data_post = getattr(resp_post, "dict", {})
    status = getattr(resp_post, "status", None)
    
    # 2. 檢查拒絕狀態及 MessageId
    is_disabled_found = False
    dict_str = str(data_post)
    
    if "Base.1.12.ServiceDisabled" in dict_str or "ServiceDisabled" in dict_str:
        is_disabled_found = True
        
    if not is_disabled_found or status in [200, 201]:
         print(f"   [FAIL] 未能成功觸發 ServiceDisabled 錯誤，或竟然登入成功 (Status: {status})。")
         raise Exception("失敗：Service Disabled 機制無效。")
         
    print(f"   [PASS] 成功驗證！系統擋下建立嘗試，並回傳 ServiceDisabled 訊息 (Status: {status})。")
