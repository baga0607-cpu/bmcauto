import logging

logger = logging.getLogger("PlaybookRunner")

# =============================================================
# 共用步驟：人工驗證 Pass / Fail
#
# 這是一個可以被任意 TestCase 引用的通用步驟。
# 將此步驟放入 STEPS 清單的任意位置，即可在該處暫停
# 並要求測試員輸入 Pass 或 Fail。
#
# 使用方式：
# 1. 互動模式：直接放入 STEPS 清單，執行時會暫停等待輸入。
# 2. 自動模式：若需自動化，請確保 safe_to_skip 為 True 並在執行前移除此步驟。
# =============================================================

STEP_NAME = "人工驗證 (Pass / Fail)"

STEP_DESCRIPTION = "暫停測試流程，要求測試員手動判定階段結果。\n    - 可透過 preset 傳入自訂提示文字。\n    - 若無傳入，將自動抓取上一歩名稱與參數作為提示。"

STEP_METADATA = {
    "requires": [],                          # 不需要任何 context key
    "produces": ["_last_human_result"],      # 將結果寫入 context
    "type": "human_check",
    "safe_to_skip": True,                    # 全自動流程時可選擇從 STEPS 清單中移除
    "preset_hint": "輸入給測試員的提示文字 (可留空)",
}


def execute(client, context, preset=None):
    """
    暫停執行，等待測試員觀察硬體後輸入 Pass 或 Fail。
    結果會寫入 result.log 並儲存至 context['_last_human_result']。
    若傳入 preset，則作為自訂提示文字。若未傳入，則自動抓取上一歩狀態作為提示。
    """
    scenario  = context.get("_scenario_name", "Unknown Scenario")
    prev_step = context.get("_last_step_name", "Unknown Step")
    prev_preset = context.get("_last_step_preset", None)

    if preset:
        # 有自訂文字
        prompt_text = f"[自訂指示] {preset} (pass / fail): "
    else:
        # 聰明判斷邏輯
        if prev_preset:
            prompt_text = f"[自動指示] 請確認 [{prev_step}] 是否符合預期結果 (參數: {prev_preset})？ (pass / fail): "
        else:
            prompt_text = f"[自動指示] 請確認 [{prev_step}] 是否符合預期結果？ (pass / fail): "

    while True:
        result = input(prompt_text).strip().lower()
        if result in ["pass", "fail"]:
            break
        print("輸入格式錯誤，請輸入 pass 或 fail。")

    status_str = "SUCCESS" if result == "pass" else "FAILED"
    logger.info(f"[Human Check] {scenario} -> {prev_step} -> {status_str}")
    context["_last_human_result"] = result

    if result == "fail":
        print("[FAIL] 已記錄為 FAIL，但測試將繼續執行，總結判定時將宣告失敗。")
        context["_tc_status"] = "FAIL"
    else:
        print("[PASS] 已記錄為 PASS。")
