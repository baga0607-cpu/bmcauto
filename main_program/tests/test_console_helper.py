import os
import sys
import yaml
import time
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# 將父目錄與 main_program 目錄加入 path 確保能載入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_program.console_helper import ConsoleClient, logger

# ============================================================================
# 模擬 (Mock) 測試連線通道：用於在我方無真實環境下驗證狀態機邏輯是否正確
# ============================================================================
class MockChannel:
    def __init__(self):
        self.sent_data = []
        self.recv_buffer = "Welcome to Console Server (172.17.22.108)\r\nlogin: "
        self.state = 0 # 0: login, 1: password, 2: prompt, 3: stty, 4: ready, 5: exec

    def send(self, data):
        data_str = data.decode("utf-8") if isinstance(data, bytes) else data
        cleaned_cmd = data_str.replace("\r", "").replace("\n", "").strip()
        self.sent_data.append(cleaned_cmd)
        
        # 狀態機推進模擬
        if cleaned_cmd == "root" and self.state == 0:
            self.recv_buffer += "\r\nPassword: "
            self.state = 1
        elif cleaned_cmd == "advantech" and self.state == 1:
            self.recv_buffer += "\r\n[root@dut ~]# "
            self.state = 2
        elif cleaned_cmd == "export TERM=dumb" and self.state == 2:
            self.recv_buffer += "\r\n[root@dut ~]# "
            self.state = 3
        elif cleaned_cmd == "stty cols 300 rows 0" and self.state == 3:
            self.recv_buffer += "\r\n[root@dut ~]# "
            self.state = 4
        elif cleaned_cmd == "ipmitool mc info" and self.state == 4:
            self.recv_buffer += (
                "\r\nDevice ID             : 32\r\n"
                "Device Revision       : 1\r\n"
                "Firmware Revision     : 1.02\r\n"
                "IPMI Version          : 2.0\r\n"
                "Manufacturer ID       : 1029\r\n"
                "[root@dut ~]# "
            )
            self.state = 5
        elif cleaned_cmd == "~." and self.state == 5:
            self.recv_buffer += "\r\n[Connection closed by foreign host]\r\n"
        elif cleaned_cmd == "" and self.state >= 2:
            self.recv_buffer += "\r\n[root@dut ~]# "

    def recv_ready(self):
        return len(self.recv_buffer) > 0

    def recv(self, limit):
        data = self.recv_buffer[:limit]
        self.recv_buffer = self.recv_buffer[limit:]
        return data.encode("utf-8")
        
    def close(self):
        pass

def run_mock_test():
    print("\n" + "="*50)
    print(" 啟動 Mock 測試：模擬 Console Server 連線與狀態機")
    print("="*50)
    
    mock_config = {
        "console_server": {
            "host": "172.17.22.108",
            "port": 22,
            "protocol": "ssh",
            "username": "admin",
            "password": "password"
        },
        "dut_console": {
            "connect_cmd": "telnet 127.0.0.1 7001",
            "exit_cmd": "~."
        },
        "dut_os": {
            "os_type": "linux",
            "username": "root",
            "password": "advantech",
            "prompt_regex": ".*# "
        }
    }
    
    # 創建 Client 並注入 Mock
    client = ConsoleClient(mock_config)
    client.connected = True
    
    # 手動建立 mock 通道
    mock_chan = MockChannel()
    client.ssh_channel = mock_chan
    
    print("[Mock] 模擬觸發 _login_dut_os 狀態機防呆登入...")
    client._login_dut_os()
    
    print("\n[Mock] 模擬執行 ipmitool mc info 指令...")
    result = client.exec_command("ipmitool mc info")
    
    print("\n" + "-"*30 + " 執行結果 " + "-"*30)
    print(result)
    print("-"*69)
    
    assert "Device ID             : 32" in result, "Mock 測試失敗，輸出不匹配！"
    assert "IPMI Version          : 2.0" in result, "Mock 測試失敗，輸出不匹配！"
    print("\n[OK] Mock 測試通過！自動登入狀態機、Stty 規格化與指令回顯解析邏輯運作完美。")

# ============================================================================
# 真實測試連線通道：當使用者在 UI 配置好後可下此指令進行真實連線
# ============================================================================
def run_real_test(config_path):
    print("\n" + "="*50)
    print(" 啟動實體連線測試：讀取 config.yaml 連線設定")
    print("="*50)
    
    if not os.path.exists(config_path):
        print(f"[FAIL] 找不到連線設定檔 config.yaml: {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 檢查是否有基本設定
    cs = config.get("console_server", {})
    if not cs.get("host") or not cs.get("username"):
        print("[FAIL] 偵測到 config.yaml 中尚未配置 Console Server IP 或帳密！")
        print("請先在 Web UI 點選「連線設定」進行設定並儲存，再行測試。")
        return

    client = ConsoleClient(config)
    try:
        client.connect()
        print("\n[OK] 實體連線與登入狀態機執行成功！")
        
        # 測試基本指令
        print("\n正在發送測試指令: uname -a ...")
        sys_info = client.exec_command("uname -a")
        print(f"\n--- [uname -a] ---\n{sys_info}\n-----------------")
        
        print("\n正在發送測試指令: ipmitool mc info ...")
        mc_info = client.exec_command("ipmitool mc info")
        print(f"\n--- [ipmitool mc info] ---\n{mc_info}\n-------------------------")
        
        print("\n正在發送測試指令: ipmitool mc watchdog get ...")
        wdt_info = client.exec_command("ipmitool mc watchdog get")
        print(f"\n--- [ipmitool mc watchdog get] ---\n{wdt_info}\n----------------------------------")
        
        print("\n正在發送測試指令: ipmitool lan print 1 ...")
        lan_info = client.exec_command("ipmitool lan print 1")
        print(f"\n--- [ipmitool lan print 1] ---\n{lan_info}\n----------------------------------")
        
        print("\n正在發送測試指令: ipmitool fru print ...")
        fru_info = client.exec_command("ipmitool fru print")
        print(f"\n--- [ipmitool fru print] ---\n{fru_info}\n----------------------------------")
        
    except Exception as e:
        print(f"\n[FAIL] 連線測試失敗: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


class ConsoleHelperMockTest(unittest.TestCase):
    def test_console_login_and_ipmitool_command(self):
        run_mock_test()

if __name__ == "__main__":
    config_file = str(REPO_ROOT / "main_program" / "config.yaml")
    
    # 預設支援 --real 參數；如果無參數，先執行 Mock 測試以確認程式正確，再提示可以讀取真實設定
    if "--real" in sys.argv:
        run_real_test(config_file)
    else:
        run_mock_test()
        print("\n提示：若要在您的電腦執行對實體 Console Server 的連線，請先在網頁 UI 儲存設定，然後下達指令：")
        print("   python main_program/tests/test_console_helper.py --real")
