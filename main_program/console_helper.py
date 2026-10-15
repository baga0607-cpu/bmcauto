import re
import time
import telnetlib
import logging

# 確保 log 輸出
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ConsoleClient")

class ConsoleClient:
    def __init__(self, config):
        """
        config 應包含:
        - console_server: host, port, protocol, username, password
        - dut_console: connect_cmd, exit_cmd
        - dut_os: os_type, username, password, prompt_regex
        """
        self.config = config
        self.cs_conf = config.get("console_server", {})
        self.dut_conf = config.get("dut_console", {})
        self.os_conf = config.get("dut_os", {})
        
        self.ssh_client = None
        self.ssh_channel = None
        self.telnet_client = None
        
        self.connected = False

    def connect(self):
        """第一階段：連線至 Console Server，並進入第二與第三階段"""
        host = self.cs_conf.get("host")
        port = int(self.cs_conf.get("port", 22))
        proto = self.cs_conf.get("protocol", "ssh").lower()
        user = self.cs_conf.get("username", "")
        pwd = self.cs_conf.get("password", "")

        if not host:
            raise ValueError("Console Server 主機 IP 未設定！")

        logger.info(f"正在連線至 Console Server ({host}:{port}, 協定: {proto})...")

        if proto == "ssh":
            import paramiko
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(hostname=host, port=port, username=user, password=pwd, timeout=15)
            
            # 開啟互動式 Shell 通道
            self.ssh_channel = self.ssh_client.invoke_shell()
            self.ssh_channel.setblocking(0)
            logger.info("Console Server SSH 連線已建立。")
        elif proto == "telnet":
            self.telnet_client = telnetlib.Telnet(host, port, timeout=15)
            # 處理 Telnet 登入 Console Server (有些 Console Server 需要登入帳密)
            if user:
                self._read_until_regex([r"[lL]ogin:", r"[uU]sername:"])
                self._send(user)
            if pwd:
                self._read_until_regex([r"[pP]assword:"])
                self._send(pwd)
            logger.info("Console Server Telnet 連線已建立。")
        else:
            raise ValueError(f"不支援的連線協定: {proto}")

        self.connected = True

        # 第二階段：轉接到 DUT Console
        self._connect_to_dut()
        
        # 第三階段：登入 Linux OS
        self._login_dut_os()

    def _flush_buffer(self):
        """徹底清空接收緩衝區中的殘留資料，防範 Race Condition"""
        flushed_data = ""
        empty_checks = 0
        while empty_checks < 3: # 必須連續 3 次檢查都是空的，才認為真的清空了
            chunk = ""
            if self.ssh_channel:
                if self.ssh_channel.recv_ready():
                    chunk = self.ssh_channel.recv(4096).decode("utf-8", errors="ignore")
            elif self.telnet_client:
                # read_very_eager() 讀取所有可讀資料而不阻塞
                chunk = self.telnet_client.read_very_eager().decode("utf-8", errors="ignore")
            
            if chunk:
                flushed_data += chunk
                empty_checks = 0 # 讀到資料，重設空檢查計數器
                time.sleep(0.02)
            else:
                empty_checks += 1
                time.sleep(0.02)
        if flushed_data:
            logger.debug(f"[Flush] 已清除緩衝區殘留: {repr(flushed_data)}")

    def _send(self, data):
        """底層發送字串並換行"""
        if self.ssh_channel:
            self.ssh_channel.send(data + "\r\n")
        elif self.telnet_client:
            self.telnet_client.write((data + "\r\n").encode("utf-8", errors="ignore"))

    def _send_raw(self, data):
        """底層發送純字串，不自動加換行"""
        if self.ssh_channel:
            self.ssh_channel.send(data)
        elif self.telnet_client:
            self.telnet_client.write(data.encode("utf-8", errors="ignore"))

    def _read_until_regex(self, patterns, timeout=15):
        """讀取緩衝區直到匹配其中一個正則表達式"""
        compiled = [re.compile(p) for p in patterns]
        buffer = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            chunk = ""
            if self.ssh_channel:
                if self.ssh_channel.recv_ready():
                    chunk = self.ssh_channel.recv(4096).decode("utf-8", errors="ignore")
            elif self.telnet_client:
                # telnet 非阻塞讀取
                chunk = self.telnet_client.read_very_eager().decode("utf-8", errors="ignore")
                
            if chunk:
                buffer += chunk
                # 列印輸出以便除錯
                # logger.debug(f"RAW: {chunk}")
                for idx, r in enumerate(compiled):
                    match = r.search(buffer)
                    if match:
                        return idx, match, buffer
            time.sleep(0.05)
            
        raise TimeoutError(f"等待正則式超時: {patterns}。目前收到的內容：\n{buffer}")

    def _connect_to_dut(self):
        """第二階段：發送轉接指令連至 DUT"""
        cmd = self.dut_conf.get("connect_cmd")
        if not cmd:
            logger.info("未設定 DUT 轉接指令，跳過此階段。")
            return
            
        force_connect_cmd = self.dut_conf.get("force_connect_cmd")
        max_retries = 2
        cmd_to_run = cmd
        
        for retry in range(max_retries + 1):
            logger.info(f"正在送出 DUT 轉接指令: {cmd_to_run} (第 {retry + 1} 次嘗試)...")
            
            # 1. 發送前先清除先前 SSH 登入產生的 prompt 殘留
            self._flush_buffer()
            
            self._send(cmd_to_run)
            
            # 2. 等待 Telnet 連接建立的特徵字元，以確保真正轉接到 DUT Serial
            prompt = self.os_conf.get("prompt_regex", ".*# ")
            
            # 如果是執行搶線指令，我們不比對任何失敗特徵（因為搶線指令在踢人並接管時會輸出該等失敗字串）
            if cmd_to_run == force_connect_cmd:
                patterns = [
                    r"Connected to",            # 0
                    r"Escape character",        # 1
                    r"[lL]ogin:",               # 2
                    r"[pP]assword:",            # 3
                    prompt                      # 4
                ]
                failure_indices = ()
                prompt_idx = 4
            else:
                patterns = [
                    r"Connection refused",      # 0
                    r"Unable to connect",       # 1
                    r"Connection closed",       # 2
                    r"Port already in use",     # 3
                    r"Connected to",            # 4
                    r"Escape character",        # 5
                    r"[lL]ogin:",               # 6
                    r"[pP]assword:",            # 7
                    prompt                      # 8
                ]
                failure_indices = (0, 1, 2, 3)
                prompt_idx = 8

            try:
                logger.info("等待 Telnet 轉接建立提示 (Connected / Escape character)...")
                idx, match, buf = self._read_until_regex(patterns, timeout=10)
                
                if idx in failure_indices:
                    if force_connect_cmd and retry < max_retries:
                        logger.warning(f"偵測到連線被佔用/拒絕 ({match.group(0)})，嘗試執行搶線指令: {force_connect_cmd}...")
                        self._send_raw(chr(3))  # Ctrl+C
                        time.sleep(0.5)
                        self._send("")
                        try:
                            self._read_until_regex([prompt], timeout=5)
                        except TimeoutError:
                            pass
                        
                        cmd_to_run = force_connect_cmd
                        logger.info("已將重試指令切換為搶線指令，進行下一輪嘗試...")
                        continue
                    else:
                        raise ConnectionError(f"Telnet 轉接失敗，無法連上 DUT Serial！錯誤訊息：{match.group(0)}")
                
                if idx == prompt_idx:
                    if force_connect_cmd and retry < max_retries:
                        logger.warning("連線指令直接被退回提示字元，嘗試執行搶線指令...")
                        self._send_raw(chr(3))  # Ctrl+C
                        time.sleep(0.5)
                        self._send("")
                        try:
                            self._read_until_regex([prompt], timeout=5)
                        except TimeoutError:
                            pass
                        
                        cmd_to_run = force_connect_cmd
                        continue
                    else:
                        raise ConnectionError(f"Telnet 轉接失敗，直接退回提示字元！完整輸出：\n{buf.strip()}")
                
                logger.info("Telnet 轉接通道已建立。")
                break
            except TimeoutError:
                if retry < max_retries and force_connect_cmd:
                    logger.warning("等待轉接超時，嘗試發送 Ctrl+C 並切換為搶線指令...")
                    self._send_raw(chr(3))
                    time.sleep(0.5)
                    self._send("")
                    try:
                        self._read_until_regex([prompt], timeout=5)
                    except TimeoutError:
                        pass
                    cmd_to_run = force_connect_cmd
                    continue
                else:
                    logger.warning("未偵測到明確的 Telnet 建立提示，嘗試發送換行以刷新畫面...")
                    self._send("")
                    time.sleep(0.5)
                    break
            
        # 3. 敲一下 Enter 確保畫面更新
        self._send("")
        time.sleep(0.5)
        
        # 4. 在進入 OS 登入狀態機之前，再次清空緩衝區
        self._flush_buffer()

    def _login_dut_os(self):
        """第三階段：OS 登入狀態機 (優先實作 Linux)"""
        os_type = self.os_conf.get("os_type", "linux").lower()
        if os_type != "linux":
            logger.info(f"非 Linux 作業系統 ({os_type})，跳過 Linux 自動登入。")
            return

        username = self.os_conf.get("username", "root")
        password = self.os_conf.get("password", "")
        prompt = self.os_conf.get("prompt_regex", ".*# ")

        logger.info("進入 Linux OS 登入狀態機...")
        
        # 防呆措施 1：敲 Enter 進行狀態探針
        self._send("")
        
        # 等待可能出現的狀態畫面
        # 0: 登入提示 login:
        # 1: 密碼提示 password:
        # 2: 已登入就緒提示字元 prompt
        patterns = [r"[lL]ogin:", r"[pP]assword:", prompt]
        
        try:
            idx, match, buf = self._read_until_regex(patterns, timeout=8)
            if idx == 0:
                # 停在登入提示，送帳號
                logger.info("偵測到 login 提示，送出使用者名稱...")
                self._send(username)
                
                # 等密碼
                idx2, _, _ = self._read_until_regex([r"[pP]assword:", prompt], timeout=8)
                if idx2 == 0:
                    logger.info("送出 OS 登入密碼...")
                    self._send(password)
                    # 等待 Prompt
                    self._read_until_regex([prompt], timeout=10)
            elif idx == 1:
                # 停在密碼提示，可能是髒狀態，送換行重設
                logger.info("偵測到異常的 Password 提示，發送換行以重置登入狀態...")
                self._send("")
                self._read_until_regex([r"[lL]ogin:"], timeout=8)
                self._send(username)
                self._read_until_regex([r"[pP]assword:"], timeout=8)
                self._send(password)
                self._read_until_regex([prompt], timeout=10)
            elif idx == 2:
                # 已經登入成功
                logger.info("偵測到已處於登入狀態，跳過登入程序。")
        except TimeoutError:
            logger.warning("狀態探針超時，嘗試強行送出一次帳密登入...")
            self._send(username)
            time.sleep(0.5)
            self._send(password)
            time.sleep(0.5)
            self._send("")

        # 防呆措施 4：終端規格化
        logger.info("正在進行 terminal 環境規格化 (export TERM=dumb & stty cols 300 rows 0)...")
        self._send("export TERM=dumb")
        time.sleep(0.2)
        self._send("stty cols 300 rows 0")
        time.sleep(0.2)
        self._send("")
        # 清空規格化指令的輸出回顯
        self._read_until_regex([prompt], timeout=5)
        self._flush_buffer()
        logger.info("Linux OS 登入就緒。")

    def exec_command(self, cmd, timeout=15):
        """防呆執行指令"""
        if not self.connected:
            raise ConnectionError("Console 尚未連線！")

        prompt = self.os_conf.get("prompt_regex", ".*# ")
        
        logger.info(f"執行指令: {cmd}")
        
        # 1. 徹底清空接收緩衝區殘留，確保這一次讀取只包含目前指令的輸出
        self._flush_buffer()
        
        # 2. 直接送出指令
        self._send(cmd)
        
        # 3. 等待執行結果的 prompt 結束
        idx, match, buf = self._read_until_regex([prompt], timeout=timeout)
        
        # 解析指令的純輸出（扣掉指令回顯與 Prompt）
        lines = buf.splitlines()
        output_lines = []
        
        for line in lines:
            cleaned = line.replace("\r", "").strip()
            # 忽略指令回顯行
            if cleaned == cmd.strip():
                continue
            # 防呆：若此行包含 Prompt 提示字元，直接跳過，不當作 stdout 還原
            if re.search(prompt, line):
                continue
            output_lines.append(line.replace("\r", ""))
            
        result = "\n".join(output_lines).strip()
        return result

    def close(self):
        """第四階段：安全退出並關閉連線"""
        if not self.connected:
            return
            
        time.sleep(0.5) # 給予終端機短暫緩衝時間
        exit_cmd = self.dut_conf.get("exit_cmd", "~.")
        if exit_cmd:
            logger.info(f"正在關閉連線，送出退回指令: {exit_cmd}...")
            # 支援組合/逸出鍵，如 ^]q
            normalized = exit_cmd.replace("Ctrl+Alt+]", "^]").replace("Ctrl+]", "^]").replace("\\x1d", "^]").replace("\\u001d", "^]")
            if "^]" in normalized:
                parts = normalized.split("^]")
                for i, part in enumerate(parts):
                    if i > 0:
                        # 在發送轉譯字元後的動作之前，嘗試等待 telnet> 提示字元
                        try:
                            logger.info("等待 telnet> 提示字元出現...")
                            self._read_until_regex([r"telnet>"], timeout=2)
                        except TimeoutError as e:
                            logger.warning(f"未偵測到 telnet> 提示字元 ({e})，直接繼續。")
                            time.sleep(0.5)
                    
                    if part:
                        # 發送剩餘動作字元 (例如 q)
                        self._send(part)
                    else:
                        # 這是 ^] 代表傳送 Ctrl+] (chr(29))
                        self._send_raw(chr(29))
                        time.sleep(0.5)
            else:
                self._send(exit_cmd)
                time.sleep(0.5)
            
        if self.ssh_client:
            try:
                self.ssh_channel.close()
                self.ssh_client.close()
            except Exception:
                pass
            self.ssh_client = None
            self.ssh_channel = None
            
        if self.telnet_client:
            try:
                self.telnet_client.close()
            except Exception:
                pass
            self.telnet_client = None
            
        self.connected = False
        logger.info("連線已關閉。")
