# =============================================================
# Step 2：列出 EthernetInterfaces 並由使用者選擇 (或自動選擇)
# 整合了 get_manager 的功能，直接預設 manager_id 為 0，列出所有網路介面，
# 讓使用者選擇後存入 context['interface_id']。
# =============================================================

STEP_NAME = "列出並選擇 EthernetInterface"

STEP_DESCRIPTION = "顯示所有網路介面，並由使用者選擇或自動指定介面。"

STEP_METADATA = {
    "requires": [],
    "produces": ["interface_id", "interface_uri"],
    "type": "interactive",
    "safe_to_skip": False,
    "preset_hint": "可填入: auto (自動選介面 2) 或 數字索引 (1/2/3...)。\n留空 = 互動選單模式。",
}


def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    # 直接整合 get_manager，預設 manager_id 為 "0"
    manager_id = context.get("manager_id", "0")
    uri = f"/redfish/v1/Managers/{manager_id}/EthernetInterfaces"

    resp = client.get(uri)
    data = getattr(resp, "dict", {})

    if getattr(resp, "status", None) != 200:
        raise Exception(f"GET {uri} 失敗，Status: {resp.status}")

    members = data.get("Members", [])
    if not members:
        raise Exception(f"在 {uri} 下找不到任何 EthernetInterface。")

    print(f"  找到 {len(members)} 個 EthernetInterface：")
    interface_ids = []
    for i, m in enumerate(members, 1):
        iid = m.get("@odata.id", "")
        interface_ids.append(iid)
        print(f"    {i}. {iid}")

    # 若自動模式，自動選擇介面 2；若只有一個，自動選擇；否則詢問使用者
    if preset == "auto":
        print("  [Auto Mode] 自動選擇介面 2 (Patch Management LAN)。")
        selected = next((iid for iid in interface_ids if iid.rstrip("/").endswith("2")), None)
        if not selected:
            selected = interface_ids[1] if len(interface_ids) > 1 else interface_ids[0]
    elif preset and preset.isdigit():
        idx = int(preset) - 1
        if 0 <= idx < len(interface_ids):
            selected = interface_ids[idx]
            print(f"  [Preset Mode] 自動選擇介面 index {preset}：{selected}")
        else:
            raise Exception(f"[Preset] 傳入的編號 {preset} 超出範圍（1~{len(interface_ids)}），請檢查。")
    elif len(interface_ids) == 1:
        selected = interface_ids[0]
        print(f"  自動選擇唯一介面：{selected}")
    else:
        while True:
            try:
                choice = int(input(f"  請選擇要操作的介面 (1-{len(interface_ids)}): "))
                if 1 <= choice <= len(interface_ids):
                    selected = interface_ids[choice - 1]
                    break
            except ValueError:
                pass
            print("  輸入不正確，請重試。")

    # 取出介面 ID（例如 .../EthernetInterfaces/2 -> 2）
    interface_id = selected.rstrip("/").split("/")[-1]
    context["interface_id"] = interface_id
    context["interface_uri"] = selected
    print(f"  [OK] 已選擇 interface_id = {interface_id}")
