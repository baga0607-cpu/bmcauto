# =============================================================
# Step 3: Delete Session (純動作)
# =============================================================

STEP_NAME = "刪除 Session (DELETE Session)"
STEP_DESCRIPTION = "發送 DELETE 刪除新建的 Session，純粹發送指令，不涉及邏輯驗證。"
STEP_METADATA = {
    "requires": ["new_session_id", "x_auth_token"],
    "produces": [],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，待刪除的 Session ID 由 post_session 的 context 自動帶入。",
}

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    new_session_id = context.get("new_session_id")
    x_auth_token = context.get("x_auth_token")

    if not new_session_id or not x_auth_token:
        raise Exception("context 缺少 new_session_id 或 x_auth_token，請先執行 post_session 步驟。")

    test_headers = {"X-Auth-Token": x_auth_token}

    # a. After step 2, DELETE URI: /redfish/v1/SessionService/Sessions/<session_id>
    print(f"  [測試 a] 發送 DELETE 請求至: {new_session_id}")
    resp_del = client.delete(new_session_id, headers=test_headers)
    status_del = getattr(resp_del, "status", None)
    
    # 這裡只做最基礎的 API 是否回覆檢查 (是否接受了這個指令)
    if status_del not in [200, 202, 204]:
        raise Exception(f" DELETE 指令發送失敗，API 拒絕或發生錯誤，Status: {status_del}")
    
    print(f"   DELETE 指令成功送出，API 回傳 Status: {status_del}。")
    print("  後續將交由 verify_session_deleted 進行真正的刪除與登出驗證。")
    
    # 把 response 存進 context 給 verify 積木檢查 204 無內容
    context["delete_status"] = status_del
    context["delete_body"] = getattr(resp_del, "dict", {})
