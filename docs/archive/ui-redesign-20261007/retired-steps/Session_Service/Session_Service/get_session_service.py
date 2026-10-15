# =============================================================
# 取得 Session Service 設定 (GET Service)
# =============================================================

STEP_NAME = "取得 Session Service 設定 (GET Service)"
STEP_DESCRIPTION = "讀取 SessionService 目前的設定與 ETag。\n    - 運作模式：自動讀取並寫入 context。不需介入。"
STEP_METADATA = {
    "requires": [],
    "produces": ["session_etag", "session_data"],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，留空直接執行即可。",
}

TARGET_URI = "/redfish/v1/SessionService"

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    resp = client.get(TARGET_URI)
    data = getattr(resp, "dict", {})

    if getattr(resp, "status", None) != 200:
        raise Exception(f"GET {TARGET_URI} 失敗，Status: {resp.status}")

    etag = data.get("@odata.etag", "*")
    context["session_etag"] = etag
    context["session_data"] = data

    enabled = data.get("ServiceEnabled")
    timeout = data.get("SessionTimeout")
    print(f"  目前設定: ServiceEnabled={enabled}, SessionTimeout={timeout}")
    print(f"  [OK] 成功取得 Session Service 狀態。ETag已儲存。")
