# =============================================================
# 修改 Boot Option 設定 (PATCH Boot)
# =============================================================

STEP_NAME = "修改 Boot Option 設定 (PATCH Boot)"
STEP_DESCRIPTION = "對 BootSourceOverrideTarget 發送 PATCH 請求，修改開機目標。"
STEP_METADATA = {
    "requires": ["system_etag"],
    "produces": ["expected_boot_target"],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "可填入: hdd / pxe / setup_menu / none\n留空 = 互動編號選單模式。",
}

SYS_URI = "/redfish/v1/Systems/0"

# 允許的 Boot Target 對應表 (簡寫轉標準名稱)
TARGET_MAP = {
    "hdd": "Hdd",
    "pxe": "Pxe",
    "setup_menu": "BiosSetup",
    "none": "None"
}

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    etag = context.get("system_etag", "*")

    target = None
    if preset:
        target = TARGET_MAP.get(preset.lower())
        if not target:
            target = preset # 如果沒有在 mapping 內就直接使用傳入的
        print(f"  [自動模式] 使用 Preset 目標: {target}")
    else:
        # 互動模式：顯示有編號的選單
        options = list(TARGET_MAP.items())  # [("hdd", "Hdd"), ...]
        print("\n  =============================================")
        print("  可選的 Boot Target：")
        for i, (key, val) in enumerate(options):
            print(f"    [{i+1}] {val}")
        print("  =============================================")
        while True:
            choice = input("  請輸入編號選擇 Boot Target: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                target = options[int(choice) - 1][1]
                break
            print(f"  [錯誤] 請輸入 1 到 {len(options)} 之間的數字。")
            
    # 預設行為
    enabled = "Once" if target != "None" else "Disabled"
    mode = "UEFI"
    
    body = {
        "Boot": {
            "BootSourceOverrideEnabled": enabled,
            "BootSourceOverrideTarget": target
        }
    }
    # 只有當設定非 None 且不是 BiosSetup 時，設定 Mode 為 UEFI
    if target not in ["None", "BiosSetup"]:
        body["Boot"]["BootSourceOverrideMode"] = mode

    print(f"\n  即將發送的 Body：")
    print(f"    BootSourceOverrideTarget : {target}")
    print(f"    BootSourceOverrideEnabled: {enabled}")
    if "BootSourceOverrideMode" in body["Boot"]:
        print(f"    BootSourceOverrideMode   : {mode}")

    req_headers = {"If-Match": etag} if etag != "*" else {}
    resp = client.patch(SYS_URI, body=body, headers=req_headers)
    status = getattr(resp, "status", None)

    if status not in [200, 204]:
        raise Exception(f"PATCH {SYS_URI} 失敗，Status: {status}")

    context["expected_boot_target"] = target
    context["expected_boot_enabled"] = enabled
    print(f"\n  [OK] PATCH 成功 (Status: {status})。Boot Option 已更新。")
