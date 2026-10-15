import time

STEP_NAME = "設定實體伺服器 Indicator LED 為閃爍 (Blinking)"
CHASSIS_URI = "/redfish/v1/Chassis/1u"

def execute(client):
    resp_get = client.get(CHASSIS_URI)
    etag = resp_get.dict.get("@odata.etag", "*")
    
    headers = {"If-Match": etag} if etag != "*" else {}
    payload = {"IndicatorLED": "Blinking"}
    
    resp_patch = client.patch(CHASSIS_URI, body=payload, headers=headers)
    
    if resp_patch.status not in [200, 204]:
        raise Exception(f"API 請求失敗，狀態碼: {resp_patch.status}")
        
    time.sleep(2)
