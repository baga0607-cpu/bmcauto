import logging

logger = logging.getLogger(__name__)

STEP_NAME = "總結判定 (Final Judgement)"
STEP_DESCRIPTION = "讀取整個 TestCase 執行過程中的狀態，判斷最終結果為 PASS 還是 FAIL。"
STEP_METADATA = {
    "requires": [],
    "produces": [],
    "type": "automated",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需 preset，將自動統整前面所有步驟的結果。",
}

def execute(client, context, preset=None):
    print(f"\n=======================================================")
    print(f"[執行中] {STEP_NAME} ...")
    
    status = context.get("_tc_status", "PASS")
    
    if status == "FAIL":
        msg = "[TC FAIL] 總結判定：此測試案發現錯誤！ (前面有步驟發生 Exception 或被人工判定為 FAIL)"
        print(f"\n❌ {msg}")
        logger.error(msg)
        print(f"=======================================================\n")
        raise Exception("TestCase 總結判定為 FAIL")
    else:
        msg = "[TC PASS] 總結判定：完美通過！"
        print(f"\n✅ {msg}")
        logger.info(msg)
        print(f"=======================================================\n")
