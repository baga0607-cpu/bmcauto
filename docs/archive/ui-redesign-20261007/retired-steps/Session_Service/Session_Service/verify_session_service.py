import logging

logger = logging.getLogger("PlaybookRunner")

STEP_NAME = "自動驗證 Session Service 設定 (Verify)"
STEP_DESCRIPTION = "比對最新的 ServiceEnabled 與 SessionTimeout 是否符合預期。"
STEP_METADATA = {
    "requires": ["session_data", "expected_session_enabled", "expected_session_timeout"],
    "produces": [],
    "type": "automated",
    "preset_hint": "此步驟不需要 preset，驗證結果由前一步驟的 context 自動帶入。",
    "safe_to_skip": True,
}

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    # 主動向 BMC 拉取最新資料 (自帶雷達)
    TARGET_URI = "/redfish/v1/SessionService"
    resp = client.get(TARGET_URI)
    latest_data = getattr(resp, "dict", {})

    exp_enabled = context.get("expected_session_enabled")
    exp_timeout = context.get("expected_session_timeout")

    if exp_enabled is None and exp_timeout is None:
        raise Exception("context 中找不到預期設定，請先執行 patch_session_service 步驟。")

    act_enabled = latest_data.get("ServiceEnabled")
    act_timeout = latest_data.get("SessionTimeout")

    errors = []
    if exp_enabled is not None and exp_enabled != act_enabled:
        errors.append(f"ServiceEnabled: 期望 {exp_enabled}, 實際為 {act_enabled}")
    if exp_timeout is not None and exp_timeout != act_timeout:
        errors.append(f"SessionTimeout: 期望 {exp_timeout}, 實際為 {act_timeout}")

    if not errors:
        print("\n   [PASS] 驗證成功：Session Service 設定已確實變更為期望值！")
        logger.info(f"[Auto Verify] Session Service 驗證成功 -> Enabled: {act_enabled}, Timeout: {act_timeout}")
    else:
        error_msg = "\n    - ".join([""] + errors)
        print(f"\n   [FAIL] 驗證失敗，發現以下不一致：{error_msg}")
        raise Exception("自動驗證失敗 (Verification Failed)。")
