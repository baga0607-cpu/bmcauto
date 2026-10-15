# =============================================================
# Step 3：GET 選定的 EthernetInterface
# 讀取使用者在 Step 2 選擇的介面詳細資訊，並將 ETag 存入 context，
# 供後續 PATCH 步驟使用。
# =============================================================

STEP_NAME = "取得 EthernetInterface 詳細資訊 (GET Interface)"

STEP_DESCRIPTION = "讀取網卡目前 IP/Mask/ETag。\n    - 運作模式：自動讀取並將必要資訊（如 ETag）寫入 context。不需介入。"

STEP_METADATA = {
    "requires": ["interface_uri"],
    "produces": ["interface_etag", "interface_data"],
    "type": "api",
    "safe_to_skip": False,
    "preset_hint": "此步驟不需要 preset，留空直接執行即可。",
}



def execute(client, context, preset=None):
    print(f"\n[執行中] {STEP_NAME} ...")

    interface_uri = context.get("interface_uri")
    if not interface_uri:
        raise Exception("context 中找不到 interface_uri，請先執行 list_interfaces 步驟。")

    resp = client.get(interface_uri)
    data = getattr(resp, "dict", {})

    if getattr(resp, "status", None) != 200:
        raise Exception(f"GET {interface_uri} 失敗，Status: {resp.status}")

    # 取得並儲存 ETag（供後續 PATCH 使用）
    etag = data.get("@odata.etag", "*")
    context["interface_etag"] = etag
    context["interface_data"] = data

    # 顯示目前關鍵設定值供使用者參考
    print(f"  目前設定值：")
    print(f"    InterfaceEnabled : {data.get('InterfaceEnabled', 'N/A')}")
    ipv4_list = data.get("IPv4Addresses", [])
    if ipv4_list:
        ip0 = ipv4_list[0]
        print(f"    IP Address       : {ip0.get('Address', 'N/A')}")
        print(f"    SubnetMask       : {ip0.get('SubnetMask', 'N/A')}")
        print(f"    Gateway          : {ip0.get('Gateway', 'N/A')}")
    print(f"    ETag             : {etag}")
    print(f"  [OK] ETag 已寫入 context，準備 PATCH。")
