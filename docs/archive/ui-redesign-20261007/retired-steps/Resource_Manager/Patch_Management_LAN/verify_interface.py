# =============================================================
# Step 5：自動驗證 EthernetInterface 設定 (Verify Interface)
# 讀取 context 中 patch_interface 寫入的期望值，
# 主動向 BMC 拉取最新資料後進行嚴格比對。
# =============================================================

STEP_NAME = "自動驗證 EthernetInterface 設定 (Verify)"

STEP_DESCRIPTION = "比對 BMC 的最新狀態與期望值，給出 PASS 或 FAIL 的結果。"

STEP_METADATA = {
    "requires": ["interface_uri", "expected_if_enabled", "expected_if_address",
                 "expected_if_subnet", "expected_if_gateway"],
    "produces": [],
    "type": "automated",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，驗證結果由前一步驟的 context 自動帶入。",
}


def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    target_uri = context.get("interface_uri")
    if not target_uri:
        raise Exception("context 中找不到 interface_uri，請先執行 list_interfaces 步驟。")

    # 期望值：從 context 取得（由 patch_interface 寫入）
    expected_enabled = context.get("expected_if_enabled")
    expected_address = context.get("expected_if_address")
    expected_subnet  = context.get("expected_if_subnet")
    expected_gateway = context.get("expected_if_gateway")

    if any(v is None for v in [expected_enabled, expected_address, expected_subnet, expected_gateway]):
        raise Exception(
            "context 中缺少期望值 (expected_if_*)，請確認 patch_interface 已正確執行並寫入 context。"
        )

    print(f"\n  期望值：")
    print(f"    InterfaceEnabled : {expected_enabled}")
    print(f"    IPv4 Address     : {expected_address}")
    print(f"    SubnetMask       : {expected_subnet}")
    print(f"    Gateway          : {expected_gateway}")

    # 主動向 BMC 拉取最新資料 (自帶雷達)
    resp = client.get(target_uri)
    latest_data = getattr(resp, "dict", {})

    # 實際值
    actual_enabled   = latest_data.get("InterfaceEnabled")
    actual_ipv4_list = latest_data.get("IPv4Addresses", [])
    if actual_ipv4_list:
        actual_ipv4    = actual_ipv4_list[0]
        actual_address = actual_ipv4.get("Address")
        actual_subnet  = actual_ipv4.get("SubnetMask")
        actual_gateway = actual_ipv4.get("Gateway")
    else:
        actual_address = actual_subnet = actual_gateway = None

    print(f"\n  實際值：")
    print(f"    InterfaceEnabled : {actual_enabled}")
    print(f"    IPv4 Address     : {actual_address}")
    print(f"    SubnetMask       : {actual_subnet}")
    print(f"    Gateway          : {actual_gateway}")

    print("\n  開始比對...")
    errors = []

    if actual_enabled != expected_enabled:
        errors.append(f"InterfaceEnabled: 期望 {expected_enabled}, 但實際為 {actual_enabled}")

    if actual_address != expected_address:
        errors.append(f"IPv4 Address: 期望 {expected_address}, 但實際為 {actual_address}")

    if actual_subnet != expected_subnet:
        errors.append(f"SubnetMask: 期望 {expected_subnet}, 但實際為 {actual_subnet}")

    if actual_gateway != expected_gateway:
        errors.append(f"Gateway: 期望 {expected_gateway}, 但實際為 {actual_gateway}")

    # 判斷結果
    if not errors:
        print("\n   [PASS] 驗證成功：BMC 網路設定已確實變更為期望值！")
        print("  [手動指示] 軟體驗證通過，接下來請登入 Node Explorer，確認硬體 Channel IP 與 Interface 狀態是否已變更。")
    else:
        error_msg = "\n    - ".join([""] + errors)
        print(f"\n   [FAIL] 驗證失敗，發現以下不一致：{error_msg}")
        raise Exception("自動驗證失敗 (Verification Failed)。")
