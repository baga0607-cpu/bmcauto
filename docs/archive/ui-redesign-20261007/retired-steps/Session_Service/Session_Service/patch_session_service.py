# =============================================================
# 變更 Session Service 設定 (PATCH Service)
# =============================================================

STEP_NAME = "變更 Session Service 設定 (PATCH Service)"
STEP_DESCRIPTION = "修改 ServiceEnabled 與 SessionTimeout。"
STEP_METADATA = {
    "requires": ["session_etag"],
    "produces": ["expected_session_enabled", "expected_session_timeout"],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "可填入: auto (預設 True_86400) 或 自訂格式 Enabled_Timeout (如 True_3600 / False_86400)。\n留空 = 互動輸入模式。",
}

TARGET_URI = "/redfish/v1/SessionService"

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    etag = context.get("session_etag", "*")
    req_headers = {"If-Match": etag} if etag != "*" else {}

    enabled = True
    timeout = 86400

    # 動態解析 preset
    is_auto = False
    if preset == "auto":
        print(f"  [Auto Mode] 使用預設數值: ServiceEnabled={enabled}, SessionTimeout={timeout}")
        is_auto = True
    elif preset and "_" in preset:
        parts = preset.split("_")
        if len(parts) == 2 and parts[0] in ["True", "False"] and parts[1].isdigit():
            enabled = (parts[0] == "True")
            timeout = int(parts[1])
            is_auto = True
            print(f"  [Preset Mode] 使用自訂數值: ServiceEnabled={enabled}, SessionTimeout={timeout}")

    if not is_auto:
        # 手動輸入
        print("\n  [互動模式] 未提供有效的 preset，請手動設定參數：")
        en_in = input("  ServiceEnabled (true/false) [true]: ").strip().lower()
        if en_in == "false": enabled = False
        
        to_in = input("  SessionTimeout (秒) [86400]: ").strip()
        if to_in.isdigit(): timeout = int(to_in)

    body = {
        "ServiceEnabled": enabled,
        "SessionTimeout": timeout
    }

    print(f"  即將發送 Body: {body}")
    resp = client.patch(TARGET_URI, body=body, headers=req_headers)
    status = getattr(resp, "status", None)

    if status not in [200, 204]:
        raise Exception(f"PATCH {TARGET_URI} 失敗，Status: {status}")

    context["expected_session_enabled"] = enabled
    context["expected_session_timeout"] = timeout
    print(f"  [OK] PATCH 成功 (Status: {status})。")
