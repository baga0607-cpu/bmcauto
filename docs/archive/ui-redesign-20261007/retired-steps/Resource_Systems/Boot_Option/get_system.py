# =============================================================
# 取得 ComputerSystem 詳細資訊 (GET System)
# 讀取 System 目前狀態，並將 ETag 存入 context
# =============================================================

STEP_NAME = "取得 ComputerSystem 詳細資訊 (GET System)"
STEP_DESCRIPTION = "讀取 System 目前狀態與 ETag。\n    - 運作模式：自動讀取並寫入 context。不需介入。"
STEP_METADATA = {
    "requires": [],
    "produces": ["system_etag"],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，留空直接執行即可。",
}

SYS_URI = "/redfish/v1/Systems/0"

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    resp = client.get(SYS_URI)
    data = getattr(resp, "dict", {})

    if getattr(resp, "status", None) != 200:
        raise Exception(f"GET {SYS_URI} 失敗，Status: {resp.status}")

    etag = data.get("@odata.etag", "*")
    context["system_etag"] = etag
    context["system_data"] = data

    print(f"  [OK] 成功取得 System 狀態。ETag: {etag}")
