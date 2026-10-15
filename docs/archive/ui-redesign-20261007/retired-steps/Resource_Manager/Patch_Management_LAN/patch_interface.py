# =============================================================
# Step 4：PATCH EthernetInterface
# 使用預設 Body 對選定的介面發出 PATCH，使用者可在執行前
# 手動修改任意欄位，並自動帶入 context 中的 ETag。
# =============================================================

STEP_NAME = "修改 EthernetInterface 設定 (PATCH Interface)"

STEP_DESCRIPTION = "對 EthernetInterface 發送 PATCH 請求以更改網路設定。\n    - 互動模式：不傳入參數。使用者可手動確認或修改每個欄位的值。\n    - 自動模式：傳入 preset='auto'。直接帶入預設值發送，不需手動按 Enter。"

STEP_METADATA = {
    "requires": ["interface_uri", "interface_etag"],
    "produces": ["expected_if_enabled", "expected_if_address", "expected_if_subnet", "expected_if_gateway"],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "可填入:\n  auto         → 直接使用預設對 Body 發送\n  自訂格式 → enabled_ip_mask_gateway\n  例: False_172.21.73.33_255.255.0.0_0.0.0.0\n留空 = 互動逐項確認模式。",
}

# 預設的 PATCH Body
DEFAULT_BODY = {
    "InterfaceEnabled": False,
    "IPv4Addresses": [{
        "Address": "172.21.73.33",
        "SubnetMask": "255.255.0.0",
        "Gateway": "0.0.0.0"
    }]
}


def _prompt_edit(label, current_value):
    """詢問使用者是否要更改某個欄位，Return 新的值或原值。"""
    user_input = input(f"    {label} [{current_value}] (直接按 Enter 保留，或輸入新值): ").strip()
    if user_input == "":
        return current_value
    # 嘗試轉換為 bool（給 InterfaceEnabled 使用）
    if user_input.lower() in ("true", "false"):
        return user_input.lower() == "true"
    return user_input


def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    interface_uri = context.get("interface_uri")
    etag = context.get("interface_etag", "*")

    if not interface_uri:
        raise Exception("context 中找不到 interface_uri，請先執行 list_interfaces 步驟。")

    # 複製預設 Body，避免污染全域定義
    import copy
    body = copy.deepcopy(DEFAULT_BODY)
    ipv4 = body["IPv4Addresses"][0]  # 先定義好變數，後面兩種模式才都抓得到

    if preset == "auto":
        print("\n  [Auto Mode] 直接使用預設 Body 參數，略過所有詢問。")
    elif preset and "_" in preset:
        # 自訂格式： enabled_ip_mask_gateway
        # 例: False_172.21.73.33_255.255.0.0_0.0.0.0
        parts = preset.split("_", 3)
        if len(parts) == 4:
            enabled_str, ip, mask, gateway = parts
            body["InterfaceEnabled"] = (enabled_str.lower() == "true")
            ipv4["Address"]    = ip
            ipv4["SubnetMask"] = mask
            ipv4["Gateway"]    = gateway
            print(f"\n  [Preset Mode] 使用自訂對 Body：")
            print(f"    InterfaceEnabled: {body['InterfaceEnabled']}")
            print(f"    IP / Mask / GW  : {ip} / {mask} / {gateway}")
        else:
            raise Exception(
                f"[Preset] 格式错誤，預期 'enabled_ip_mask_gateway'，實際收到 '{preset}'，"
                f"請檢查分隔符數量。"
            )
    else:
        print("\n  以下為預設 PATCH Body，請逐項確認或修改：")
        print("  (直接按 Enter 代表使用預設值)\n")

        # --- 修改 InterfaceEnabled ---
        body["InterfaceEnabled"] = _prompt_edit(
            "InterfaceEnabled (true/false)", body["InterfaceEnabled"]
        )

        # --- 修改 IPv4 欄位 ---
        ipv4["Address"]    = _prompt_edit("IPv4 Address",    ipv4["Address"])
        ipv4["SubnetMask"] = _prompt_edit("SubnetMask",      ipv4["SubnetMask"])
        ipv4["Gateway"]    = _prompt_edit("Gateway",         ipv4["Gateway"])

    print(f"\n  即將發送的 Body：")

    print(f"    InterfaceEnabled : {body['InterfaceEnabled']}")
    print(f"    IPv4 Address     : {ipv4['Address']}")
    print(f"    SubnetMask       : {ipv4['SubnetMask']}")
    print(f"    Gateway          : {ipv4['Gateway']}")
    print(f"    If-Match (ETag)  : {etag}")

    req_headers = {"If-Match": etag} if etag != "*" else {}

    resp = client.patch(interface_uri, body=body, headers=req_headers)
    status = getattr(resp, "status", None)

    if status not in [200, 204]:
        raise Exception(f"PATCH {interface_uri} 失敗，Status: {status}")

    # 將實際發送的對 Body 寫入 context，供 verify_interface 使用
    context["expected_if_enabled"] = body["InterfaceEnabled"]
    context["expected_if_address"]  = ipv4["Address"]
    context["expected_if_subnet"]   = ipv4["SubnetMask"]
    context["expected_if_gateway"]  = ipv4["Gateway"]

    print(f"\n  [OK] PATCH 成功 (Status: {status})。BMC LAN 設定已發送。")
