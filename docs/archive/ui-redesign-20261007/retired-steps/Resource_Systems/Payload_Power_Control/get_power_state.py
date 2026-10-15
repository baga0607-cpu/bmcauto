# =============================================================
# 取得 ComputerSystem 電源狀態 (GET Power State)
# =============================================================

STEP_NAME = "取得 ComputerSystem 電源狀態 (GET System)"
STEP_DESCRIPTION = "讀取 System 目前的 PowerState。\n    - 運作模式：自動讀取並寫入 context。不需介入。"
STEP_METADATA = {
    "requires": [],
    "produces": ["system_power_state"],
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

    power_state = data.get("PowerState", "Unknown")
    context["system_power_state"] = power_state

    print(f"  [OK] 成功取得 System 電源狀態: {power_state}")
