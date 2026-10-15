# =============================================================
# 變更 Indicator LED 狀態
# =============================================================

STEP_NAME = "設定 Indicator LED 狀態 (PATCH)"
STEP_DESCRIPTION = "發送 PATCH 請求變更 IndicatorLED 狀態。"
STEP_METADATA = {
    "requires": ["led_etag"],
    "produces": ["expected_led_state"],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "可填入: Lit / Blinking / Off\n留空 = 互動選單模式。",
}

TARGET_URI = "/redfish/v1/Chassis/1u"

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    etag = context.get("led_etag", "*")
    allowable = context.get("led_allowable", ["Lit", "Blinking", "Off"])

    chosen = preset
    if not chosen:
        print("\n  可用的 LED 狀態:")
        for i, val in enumerate(allowable, 1):
            print(f"    {i}. {val}")

        while True:
            try:
                choice = input(f"  請選擇要設定的狀態 (1-{len(allowable)}): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(allowable):
                    chosen = allowable[idx]
                    break
            except ValueError:
                pass
            print("  無效輸入，請重試。")

    print(f"  即將設定為: {chosen}")

    headers = {"If-Match": etag} if etag != "*" else {}
    payload = {"IndicatorLED": chosen}

    resp = client.patch(TARGET_URI, body=payload, headers=headers)
    status = getattr(resp, "status", None)

    if status not in [200, 204]:
        raise Exception(f"PATCH 失敗，狀態碼: {status}, 錯誤: {getattr(resp, 'text', '')}")

    print(f"  [OK] PATCH 請求成功 (Status: {status})。")
    context["expected_led_state"] = chosen
