# =============================================================
# 取得 Indicator LED 狀態與 ETag
# =============================================================

STEP_NAME = "取得 Indicator LED 狀態 (GET)"
STEP_DESCRIPTION = "發送 GET 請求取得目前 Indicator LED 狀態與可用選項，並保存 ETag。"
STEP_METADATA = {
    "requires": [],
    "produces": ["led_data", "led_etag", "led_allowable"],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，留空直接執行即可。",
}

TARGET_URI = "/redfish/v1/Chassis/1u"

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    resp = client.get(TARGET_URI)
    data = getattr(resp, "dict", {})

    etag = data.get("@odata.etag", "*")
    current_led = data.get("IndicatorLED", "Unknown")
    
    # 撈取可用選項
    allowable = data.get("IndicatorLED@Redfish.AllowableValues", [])
    if not allowable:
        allowable = ["Lit", "Blinking", "Off"]
        print("  [INFO] 未發現 AllowableValues，使用預設選項。")

    context["led_data"] = data
    context["led_etag"] = etag
    context["led_allowable"] = allowable

    print(f"  [OK] 目前狀態: {current_led}")
    print(f"  [OK] ETag 已保存: {etag}")
