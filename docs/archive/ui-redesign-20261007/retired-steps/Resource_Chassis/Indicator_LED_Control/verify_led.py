# =============================================================
# 自動驗證 Indicator LED 狀態
# =============================================================
import logging
import time

logger = logging.getLogger("PlaybookRunner")

STEP_NAME = "驗證 Indicator LED 狀態 (Verify LED)"
STEP_DESCRIPTION = "抓取最新的 Indicator LED，與預期值比對。"
STEP_METADATA = {
    "requires": ["expected_led_state"],
    "produces": [],
    "type": "automated",
    "preset_hint": "此步驟不需要 preset，驗證結果由前一步驟的 context 自動帶入。",
    "safe_to_skip": True,
}

TARGET_URI = "/redfish/v1/Chassis/1u"

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    expected_state = context.get("expected_led_state")
    if not expected_state:
        raise Exception("context 中找不到 expected_led_state，請先執行 patch_led 步驟。")

    print(f"\n  開始比對實際值與期望值... 預期: {expected_state}")

    # 給予一點時間讓 BMC 更新狀態
    time.sleep(2)

    resp = client.get(TARGET_URI)
    data = getattr(resp, "dict", {})
    actual_state = data.get("IndicatorLED")

    if actual_state == expected_state:
        print(f"\n   [PASS] 驗證成功：API 狀態已顯示為 {expected_state}！")
        logger.info(f"[Auto Verify] Indicator LED 軟體驗證成功 -> 預期: {expected_state}, 實際: {actual_state}")
    else:
        print(f"\n   [FAIL] 驗證失敗，預期 {expected_state}，實際為 {actual_state}")
        raise Exception("自動驗證失敗 (Verification Failed)。")
