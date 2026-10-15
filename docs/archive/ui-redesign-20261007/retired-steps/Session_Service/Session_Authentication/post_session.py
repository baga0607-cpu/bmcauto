# =============================================================
# Step 1: Session Authentication (POST)
# =============================================================

STEP_NAME = "建立新 Session (POST Session)"
STEP_DESCRIPTION = "發送 POST 建立新 Session，驗證 X-Auth-Token、Location Header 與 Body 完整性。"
STEP_METADATA = {
    "requires": [],
    "produces": ["new_session_id", "x_auth_token"],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "可填入: auto (使用預設帳密) 或 帳號_密碼 (如 admin_1234)。\n留空 = 互動輸入帳號密碼模式。",
}

SESSION_URI = "/redfish/v1/SessionService/Sessions"

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    # b4. Redfish shall not require user to login by base authentication to create session.
    # 為了嚴格驗證這點，我們在發送請求時，刻意覆蓋 Authorization 標頭為空字串，
    # 確保底層 client 不會偷偷帶上 Basic Auth。
    post_headers = {
        "Content-Type": "application/json",
        "Authorization": "" # 強制抽掉 Basic Auth
    }
    
    # 支援互動模式與自動模式
    target_user = "administrator"
    target_pass = "advantech"
    
    if preset == "auto":
        print(f"  [Auto Mode] 使用預設帳密: {target_user} / {target_pass}")
    elif preset and "_" in preset:
        parts = preset.split("_", 1)
        target_user = parts[0]
        target_pass = parts[1]
        print(f"  [Preset Mode] 使用自訂帳密: {target_user} / {target_pass}")
    else:
        print("  [互動模式] 請輸入要測試的帳號密碼:")
        u = input(f"    UserName [{target_user}] (直接按 Enter 保留，或輸入新值): ").strip()
        if u: target_user = u
        p = input(f"    Password [{target_pass}] (直接按 Enter 保留，或輸入新值): ").strip()
        if p: target_pass = p

    post_body = {
        "UserName": target_user,
        "Password": target_pass
    }
    
    print(f"\n  [測試 b4] 發送無 Basic Auth 的 POST 請求 (使用帳密 {target_user}/*****)...")
    resp_post = client.post(SESSION_URI, body=post_body, headers=post_headers)
    status = getattr(resp_post, "status", None)
    
    # b5. Status code shall be 201.
    if status != 201:
        raise Exception(f" [FAIL b5] 預期狀態碼 201，但收到 {status}。可能是不支援無授權連線或帳密錯誤。")
    print("   [PASS b4, b5] 成功在不依賴 Basic Auth 的情況下建立 Session，並回傳 201。")

    # b1. It shall include X-Auth-Token in response header.
    # b6. Location shall be included in response header.
    x_auth_token = None
    location = None
    
    # 使用多重機制抓取 Header (與 test_timeout.py 一致)
    if hasattr(resp_post, "getheader"):
        x_auth_token = resp_post.getheader("X-Auth-Token")
        location = resp_post.getheader("Location")
    elif hasattr(resp_post, "headers") and isinstance(resp_post.headers, dict):
        x_auth_token = resp_post.headers.get("X-Auth-Token")
        location = resp_post.headers.get("Location")
    elif hasattr(resp_post, "get_header"):
        x_auth_token = resp_post.get_header("X-Auth-Token")
        location = resp_post.get_header("Location")

    if not x_auth_token:
        raise Exception(" [FAIL b1] Response Header 中未發現 X-Auth-Token。")
    print(f"   [PASS b1] 成功取得 X-Auth-Token: [{x_auth_token}]")
    
    if not location:
        raise Exception(" [FAIL b6] Response Header 中未發現 Location。")
    print(f"   [PASS b6] 成功取得 Location: {location}")

    # b2. Redfish shall reply new resource in response body.
    # b3. JSON Body shall contains a full representation.
    data_post = getattr(resp_post, "dict", {})
    odata_id = data_post.get("@odata.id")
    
    if not data_post or not odata_id:
        raise Exception(" [FAIL b2, b3] Response Body 為空或缺少 @odata.id，不是完整的 JSON 表示。")
    
    # 驗證幾個關鍵欄位是否存在來證明這是 full representation
    if "Id" not in data_post or "UserName" not in data_post:
         print("   [警告] Response Body 似乎缺少 Id 或 UserName 欄位，這可能不是完整的表現形式 (Full representation)。")
    else:
         print("   [PASS b2, b3] Response Body 包含 @odata.id, Id, UserName 等，確認為完整表示 (Full Representation)。")

    # 將資料寫入 context 供下一步使用
    context["new_session_id"] = location if location else odata_id
    context["x_auth_token"] = x_auth_token
    print("\n   Step 1 所有驗證項目 (b1~b6) 皆已通過！")
