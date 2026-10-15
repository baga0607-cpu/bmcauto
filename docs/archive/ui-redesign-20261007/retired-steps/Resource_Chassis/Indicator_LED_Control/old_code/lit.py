import time

# 這是劇本引擎會印出來的名稱
STEP_NAME = "設定實體伺服器 Indicator LED 為恆亮 (Lit)"

# 您機器的獨立路徑
CHASSIS_URI = "/redfish/v1/Chassis/1u"

def execute(client):
    """
    這是一個原子的資料庫步驟，只專注於將燈號設為 Lit。
    """
    # 取得 ETag
    resp_get = client.get(CHASSIS_URI)
    etag = resp_get.dict.get("@odata.etag", "*")
    
    headers = {"If-Match": etag} if etag != "*" else {}
    payload = {"IndicatorLED": "Lit"}
    
    # 執行更改動作
    resp_patch = client.patch(CHASSIS_URI, body=payload, headers=headers)
    
    if resp_patch.status not in [200, 204]:
        raise Exception(f"API 請求失敗，狀態碼: {resp_patch.status}")
        
    # 等待硬體收到從 BMC 傳遞出來的 GPIO 指令
    time.sleep(2)
