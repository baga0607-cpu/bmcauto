import time
import logging

logger = logging.getLogger("PlaybookRunner")

STEP_NAME = "自動驗證 電源狀態 (Verify)"
STEP_DESCRIPTION = "重複抓取 BMC 狀態，直到與預期相符，超時則判斷 FAIL。"
STEP_METADATA = {
    "requires": ["expected_power_state"],
    "produces": [],
    "type": "automated",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，驗證結果由前一步驟的 context 自動帶入。",
}

SYS_URI = "/redfish/v1/Systems/0"

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    expected_state = context.get("expected_power_state")
    if not expected_state or expected_state == "Unknown":
        print("  [INFO] 預期電源狀態未知 (例如執行了 NMI 或剛重啟)，略過嚴格比對。")
        return

    print(f"\n  開始驗證... 預期狀態: {expected_state}")
    
    expected_delay = context.get("expected_delay", 0)
    if expected_delay > 0:
        print(f"  [排程驗證] 此動作為排程操作，預期在 {expected_delay} 秒後觸發。")
        print("  將先監控前半段時間，確保系統【不會】提早改變狀態...")
        safe_wait = expected_delay - 30 # 提早 30 秒結束前半段監控
        
        elapsed = 0
        while elapsed < safe_wait:
            resp = client.get(SYS_URI)
            actual_state = getattr(resp, "dict", {}).get("PowerState")
            if actual_state == expected_state:
                raise Exception(f" [FAIL] 排程驗證失敗：系統提早進入了 {expected_state} 狀態！(未遵守排程)")
            time.sleep(5)
            elapsed += 5
            
        print("  [OK] 前半段等待完畢，系統尚未改變狀態，符合排程行為。")
        print("  進入後半段監控，等待排程時間到達並執行狀態切換...")
        context["expected_delay"] = 0 # 清除避免影響後續

    # 電源狀態改變可能需要時間 (特別是 GracefulShutdown 或重啟)
    # 我們給予最長 3 分鐘 (180秒) 的等待時間
    max_retries = 36
    sleep_interval = 5
    
    for i in range(max_retries):
        resp = client.get(SYS_URI)
        data = getattr(resp, "dict", {})
        actual_state = data.get("PowerState")
        
        if actual_state == expected_state:
            print(f"\n   [PASS] 驗證成功：電源狀態已轉為 {expected_state}！")
            logger.info(f"[Auto Verify] 電源狀態驗證成功 -> 預期: {expected_state}, 實際: {actual_state}")
            return
            
        print(f"    - 目前狀態: {actual_state}，等待 {sleep_interval} 秒後重試... ({i+1}/{max_retries})")
        time.sleep(sleep_interval)

    print(f"\n   [FAIL] 驗證失敗：等待超時，電源狀態仍未轉為 {expected_state}")
    raise Exception("自動驗證失敗 (Verification Failed)。")
