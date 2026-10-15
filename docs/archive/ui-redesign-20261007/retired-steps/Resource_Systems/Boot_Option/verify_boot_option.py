import logging

logger = logging.getLogger("PlaybookRunner")

STEP_NAME = "自動驗證 Boot Option 設定 (Verify)"
STEP_DESCRIPTION = "比對 BMC 的最新狀態與期望值，給出 PASS 或 FAIL 的結果。"
STEP_METADATA = {
    "requires": ["expected_boot_target"],
    "produces": [],
    "type": "automated",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，驗證結果由前一步驟的 context 自動帶入。",
}

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    # 主動向 BMC 拉取最新資料 (自帶雷達)
    TARGET_URI = "/redfish/v1/Systems/0"
    resp = client.get(TARGET_URI)
    latest_data = getattr(resp, "dict", {})

    expected_target = context.get("expected_boot_target")
    expected_enabled = context.get("expected_boot_enabled")

    if expected_target is None or expected_enabled is None:
        raise Exception("context 中找不到預期設定，請先執行 patch_boot_option 步驟。")

    print(f"\n  開始比對實際值與期望值...")
    print(f"  期望 Target : {expected_target}")
    print(f"  期望 Enabled: {expected_enabled}")

    boot_data = latest_data.get("Boot", {})
    actual_target = boot_data.get("BootSourceOverrideTarget")
    actual_enabled = boot_data.get("BootSourceOverrideEnabled")
    
    errors = []
    if expected_target != actual_target:
        errors.append(f"Target: 期望 {expected_target}, 實際為 {actual_target}")
    if expected_enabled != actual_enabled:
        errors.append(f"Enabled: 期望 {expected_enabled}, 實際為 {actual_enabled}")

    if not errors:
        print("\n   [PASS] 驗證成功：Boot Option 已確實變更為期望值！")
        logger.info(f"[Auto Verify] Boot Option 驗證成功 -> Target: {actual_target}, Enabled: {actual_enabled}")
    else:
        error_msg = "\n    - ".join([""] + errors)
        print(f"\n   [FAIL] 驗證失敗，發現以下不一致：{error_msg}")
        raise Exception("自動驗證失敗 (Verification Failed)。")
