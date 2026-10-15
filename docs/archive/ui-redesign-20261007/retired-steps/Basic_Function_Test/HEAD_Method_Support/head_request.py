# =============================================================
# Step 1: HEAD Request (純動作)
# =============================================================

STEP_NAME = "發送 HEAD 請求 (HEAD Request)"
STEP_DESCRIPTION = "對 /redfish/v1 發送 HEAD 請求，將回應的 status、body、headers 存入 context 供後續驗證。"
STEP_METADATA = {
    "requires": [],
    "produces": ["head_status", "head_body", "head_link_header"],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，留空直接執行即可。",
}

TARGET_URI = "/redfish/v1"

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")
    print(f"  Method: HEAD  URI: {TARGET_URI}")

    if not hasattr(client, "head"):
        raise Exception("[FAIL] 底層 client 不支援 head() 方法，無法執行本測項。")

    resp = client.head(TARGET_URI)
    status = getattr(resp, "status", None)
    body   = getattr(resp, "dict", None)
    text   = getattr(resp, "text", "")

    # 擷取 Link header (嘗試多種格式)
    link_value = None
    if hasattr(resp, "getheader"):
        link_value = resp.getheader("Link") or resp.getheader("link")
    elif hasattr(resp, "headers") and isinstance(resp.headers, dict):
        link_value = resp.headers.get("Link") or resp.headers.get("link")

    # 把所有 headers 也存起來，供 verify 印出除錯用
    all_headers = getattr(resp, "headers", None)

    context["head_status"]     = status
    context["head_body"]       = body
    context["head_body_text"]  = text
    context["head_link_header"]= link_value
    context["head_all_headers"]= str(all_headers)

    print(f"  [OK] HEAD 請求已送出，Status: {status}。結果存入 context，交由 verify 判斷。")
