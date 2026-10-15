# =============================================================
# 執行電源控制操作 (POST Power Action)
# 支援各種 ResetType 與 OperationApplyTime
# =============================================================
import datetime

STEP_NAME = "執行電源控制操作 (POST Power Action)"
STEP_DESCRIPTION = "對 ComputerSystem.Reset 發送 POST 請求，執行電源控制操作。"
STEP_METADATA = {
    "requires": [],
    "produces": ["expected_power_state"],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "可填入: On / ForceOff / GracefulShutdown / ForceRestart / Nmi / PowerCycle / OnImmediate / GracefulShutdownSchedule\n留空 = 互動選單模式。",
}

TARGET_URI = "/redfish/v1/Systems/0/Actions/ComputerSystem.Reset"

ACTIONS = [
    "On", "ForceOff", "GracefulShutdown", 
    "ForceRestart", "Nmi", "PowerCycle",
    "OnImmediate", "GracefulShutdownSchedule"
]

def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    action = preset
    if not action:
        print("\n  可用的電源操作:")
        for i, a in enumerate(ACTIONS, 1):
            print(f"    {i}. {a}")
        while True:
            try:
                choice = int(input(f"  請選擇操作 (1-{len(ACTIONS)}): "))
                if 1 <= choice <= len(ACTIONS):
                    action = ACTIONS[choice - 1]
                    break
            except ValueError:
                pass
            print("  輸入不正確，請重試。")

    print(f"  即將執行的動作: {action}")
    
    payload = {}
    expected_state = "Unknown"
    expected_status = 200 # 有些是 204 有些是 200/204

    if action == "OnImmediate":
        payload = {
            "ResetType": "On",
            "@Redfish.OperationApplyTime": "Immediate"
        }
        expected_state = "On"
    elif action == "GracefulShutdownSchedule":
        # 取得 BMC 內部時間，避免本機電腦與 BMC 時間有落差導致 Expired
        resp_managers = client.get("/redfish/v1/Managers")
        manager_uri = "/redfish/v1/Managers/1"
        if "Members" in getattr(resp_managers, "dict", {}) and len(resp_managers.dict["Members"]) > 0:
            manager_uri = resp_managers.dict["Members"][0]["@odata.id"]
            
        resp_mgr = client.get(manager_uri)
        bmc_time_str = getattr(resp_mgr, "dict", {}).get("DateTime")
        
        tw_tz = datetime.timezone(datetime.timedelta(hours=8)) # 強制轉為 +08:00 時區
        
        if bmc_time_str:
            safe_time_str = bmc_time_str.replace("Z", "+00:00")
            bmc_time = datetime.datetime.fromisoformat(safe_time_str)
            # 將取得的 BMC 時間轉換為 +8 時區，再加兩分鐘
            target_time = bmc_time.astimezone(tw_tz) + datetime.timedelta(minutes=2)
        else:
            now = datetime.datetime.now(tw_tz)
            target_time = now + datetime.timedelta(minutes=2)
            
        target_time_str = target_time.isoformat(timespec='seconds')
        payload = {
            "ResetType": "GracefulShutdown",
            "@Redfish.OperationApplyTime": "AtMaintenanceWindowStart",
            "MaintenanceWindowStartTime": target_time_str
        }
        expected_state = "Off"
        expected_status = 202
    else:
        payload = {"ResetType": action}
        if action in ["On", "ForceRestart", "PowerCycle"]:
            expected_state = "On"
        elif action in ["ForceOff", "GracefulShutdown"]:
            expected_state = "Off"
        elif action == "Nmi":
            expected_state = context.get("system_power_state", "Unknown") # NMI 不改變電源狀態
            print("\n  [準備 NMI 測試]")
            print("  >>> 請登入 Payload OS (作業系統)，並以 root 身分執行以下指令：")
            print("  >>> echo 1 > /proc/sys/kernel/unknown_nmi_panic")
            input("  >>> 準備好後，請按下 Enter 鍵發送 NMI 訊號... ")

    print(f"  Payload: {payload}")
    resp_post = client.post(TARGET_URI, body=payload)
    status = getattr(resp_post, "status", None)

    # 針對排程必須回 202，一般回 200 或 204
    if expected_status == 202:
        valid_statuses = [202]
    else:
        valid_statuses = [200, 204]

    if status not in valid_statuses:
        raise Exception(f"POST {TARGET_URI} 失敗，預期狀態碼 {valid_statuses}，實際: {status}")

    context["expected_power_state"] = expected_state
    
    if expected_status == 202:
        context["expected_delay"] = 120 # 通知 verify_power_state 需要等待至少兩分鐘
        print(f"\n  [OK] 排程關機指派成功 (Status: {status})，預計於 {target_time_str} 執行。")
    else:
        context["expected_delay"] = 0
        print(f"\n  [OK] POST 成功 (Status: {status})。電源指令已發送。")
