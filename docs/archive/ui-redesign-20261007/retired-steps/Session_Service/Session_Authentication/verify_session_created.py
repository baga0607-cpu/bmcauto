# =============================================================
# Step 2: Verify Session Created (純驗證)
# =============================================================

STEP_NAME = "驗證 Session 建立成功 (Verify Session Created)"
STEP_DESCRIPTION = "使用剛剛取得的 X-Auth-Token 發送 GET 請求，檢查 Session Collection 與特定的 Session Resource，確認資源真的有寫入 BMC。"
STEP_METADATA = {
    "requires": ["new_session_id", "x_auth_token"],
    "produces": [],
    "type": "automated",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，驗證所需資料由 post_session 的 context 自動帶入。",
}

SESSION_URI = "/redfish/v1/SessionService/Sessions"

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    new_session_id = context.get("new_session_id")
    x_auth_token = context.get("x_auth_token")

    if not new_session_id or not x_auth_token:
        raise Exception("context 缺少 new_session_id 或 x_auth_token，請先執行 post_session 步驟。")

    # a. Communicate with Redfish by session authentication shall be successful.
    print("  [測試 a] 將 X-Auth-Token 放入 Header，發送 GET 至 Session Collection...")
    test_headers = {"X-Auth-Token": x_auth_token}
    
    resp_col = client.get(SESSION_URI, headers=test_headers)
    status_col = getattr(resp_col, "status", None)
    
    if status_col != 200:
        raise Exception(f" [FAIL a] 使用 Session Auth 失敗，無法讀取 Collection，Status: {status_col}")
    print("   [PASS a] 成功使用 Session Authentication 與 Redfish 溝通 (200 OK)。")

    # b. After create new session, new hyperlink with session ID shall be find.
    data_col = getattr(resp_col, "dict", {})
    members = data_col.get("Members", [])
    
    found_in_collection = False
    for m in members:
        if m.get("@odata.id") == new_session_id:
            found_in_collection = True
            break
            
    if not found_in_collection:
        raise Exception(f" [FAIL b] 在 Session Collection 的 Members 陣列中，找不到新建的 Hyperlink: {new_session_id}")
    print(f"   [PASS b] 在 Collection 中成功找到新建的 Session 連結: {new_session_id}")
    
    # 額外測試：GET 該特定的 Session Resource
    print(f"  額外測試：GET 該特定 Session ({new_session_id})...")
    resp_single = client.get(new_session_id, headers=test_headers)
    if getattr(resp_single, "status", None) == 200:
        print("   成功讀取特定 Session 資源。")
    else:
        print(f"   無法讀取特定 Session 資源，Status: {getattr(resp_single, 'status', None)}")
        
    print("\n   Step 2 建立驗證項目 (a, b) 皆已通過！")
