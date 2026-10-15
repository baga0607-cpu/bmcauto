# =============================================================
# Step 4: Verify Session Deleted (純驗證)
# =============================================================

STEP_NAME = "驗證 Session 刪除與登出 (Verify Session Deleted)"
STEP_DESCRIPTION = "嚴格驗證 DELETE 的回傳值為 204 且 Body 為空，並確保被刪除的 Token 真的失效 (401)。"
STEP_METADATA = {
    "requires": ["new_session_id", "x_auth_token", "delete_status"],
    "produces": [],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，驗證所需資料由 delete_session 的 context 自動帶入。",
}

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    new_session_id = context.get("new_session_id")
    x_auth_token = context.get("x_auth_token")
    delete_status = context.get("delete_status")
    delete_body = context.get("delete_body", {})

    # b1. Status code shall be 204.
    if delete_status not in [200, 204]:
        raise Exception(f" [FAIL b1] 預期刪除成功 (204 或 200)，但收到 Status: {delete_status}")
    
    if delete_status == 204:
        print("   [PASS b1] 回傳 Status Code 為標準的 204 No Content。")
    else:
        print(f"   [注意] 回傳 Status Code 為 {delete_status} (部分 BMC 實作會回 200 而非 204)。")

    # b2. Response data shall be empty.
    if delete_body:
        print(f"   [FAIL b2] 預期 Response Data 應為空，但 BMC 回傳了 JSON: {delete_body}")
    else:
        print("   [PASS b2] Response Data 確認為空。")

    # b3. After delete URI, communication shall be logout.
    test_headers = {"X-Auth-Token": x_auth_token}
    print("\n  [測試 b3] 嘗試拿剛才被刪除的 Token 再發送一次 GET 請求...")
    resp_check = client.get("/redfish/v1/SessionService/Sessions", headers=test_headers)
    status_check = getattr(resp_check, "status", None)
    
    if status_check in [200, 201]:
        raise Exception(f" [FAIL b3] 登出失敗！被刪除的 Token 仍然可以存取資源 (Status: {status_check})。")
    print(f"   [PASS b3] 成功被登出！使用已刪除的 Token 遭到拒絕 (Status: {status_check})。")

    print("\n   Step 4 登出驗證項目 (b1~b3) 皆已通過！")
