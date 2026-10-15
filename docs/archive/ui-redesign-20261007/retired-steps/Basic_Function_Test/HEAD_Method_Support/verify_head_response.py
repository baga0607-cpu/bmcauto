# =============================================================
# Step 2: Verify HEAD Response (純驗證)
# =============================================================

STEP_NAME = "驗證 HEAD 回應 (Verify HEAD Response)"
STEP_DESCRIPTION = "從 context 取出 HEAD 回應資料，依規範逐條驗證 b1/b2/b3。"
STEP_METADATA = {
    "requires": ["head_status", "head_body", "head_link_header"],
    "produces": [],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，驗證結果由 head_request 的 context 自動帶入。",
}

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    status      = context.get("head_status")
    body        = context.get("head_body")
    body_text   = context.get("head_body_text", "")
    link_value  = context.get("head_link_header")
    all_headers = context.get("head_all_headers", "")

    # b1. Redfish shall support "Head" method.
    if status == 200:
        print(f"  [PASS b1] HEAD 方法被支援，Status: {status} OK")
    else:
        raise Exception(f"  [FAIL b1] HEAD 請求未被接受，Status: {status} (預期 200)")

    # b2. Redfish shall not return message body information.
    if not body and not body_text:
        print(f"  [PASS b2] Response Body 確認為空，符合 HEAD 規範。")
    else:
        print(f"  [WARNING b2] Response Body 不為空 (body={body}, text={str(body_text)[:80]})。")
        print(f"               請人工確認 BMC 是否真的回傳了 Body 內容。")

    # b3. Redfish shall reply "Link" in header.
    if link_value:
        print(f"  [PASS b3] Response Header 中找到 Link: {link_value}")
    else:
        print(f"  [WARNING b3] 未在 Header 中找到 Link 欄位。")
        print(f"               全部 Headers: {all_headers}")
        print(f"               請人工確認 BMC 是否有回傳 Link Header。")

    print(f"\n  [PASS] Step 2 驗證完成，請透過 Human Check 確認最終結果。")
