import subprocess

from console_helper import ConsoleClient


class IpmiResponse:
    def __init__(self, stdout, stderr, returncode, data=None):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.status = returncode
        self.data = data or []
        self.completion_code = 0x00 if returncode == 0 else None
        self.dict = {
            "stdout": stdout, 
            "stderr": stderr, 
            "returncode": returncode, 
            "data": self.data,
            "completion_code": self.completion_code
        }


class WebLoggingRedfishClient:
    """API 透明代理：
    - 摘要與完整 response 共用 Test log，並推送 SSE
    - 完整 Response Body 直接寫入同一檔案，不經過 stdout
    """
    def __init__(self, client, api_file=None, msg_queue=None, environment=None):
        self._environment = environment or {}
        self._c       = client
        self._api_f   = api_file
        self._mq      = msg_queue   # SSE 佇列，用來推送完整 api_body 事件
        self._console_client = None

    def _get_console_client(self):
        if self._console_client is None:
            config = self._environment
            cs = config.get("console_server", {})
            if cs.get("host"):
                print("  [Console] Console Server configured; establishing connection...")
                self._console_client = ConsoleClient(config)
                self._console_client.connect()
                print("  [Console] Connected to Console Server.")
        return self._console_client

    def run_ipmitool(self, command_args, interface_options=None, ipmitool_args=None, **kwargs):
        """實作非 raw 的 ipmitool 執行代理，供步驟呼叫"""
        if ipmitool_args is None and interface_options:
            ipmitool_args = interface_options.get("ipmitool_args", [])
        if ipmitool_args is None:
            ipmitool_args = []
            
        interface_type = interface_options.get("type", "iol") if interface_options else "iol"
        
        # 決定是否走 Console Server 遠端執行
        use_remote = False
        if self._environment.get("console_server", {}).get("host") and interface_type in ("kcs", "serial"):
            use_remote = True

        cmd = ["ipmitool"] + ipmitool_args + command_args
        cmd_str = " ".join(cmd)

        if use_remote:
            print(f"  [Console][IPMI] Executing remote command: {cmd_str}")
            if self._api_f:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                self._api_f.write(f"{now_str} - DEBUG - [IPMI  ] [Console] {cmd_str}\n")
                self._api_f.flush()
            if self._mq is not None:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                header_line = f"{now_str} - DEBUG - [IPMI  ] [Console] {cmd_str}"
                self._mq.put({"type": "api_body", "text": header_line})

            try:
                console = self._get_console_client()
                if console:
                    if interface_type == "kcs":
                        remote_cmd = " ".join(["ipmitool"] + command_args)
                    else:
                        remote_cmd = " ".join(["ipmitool"] + ipmitool_args + command_args)
                        
                    stdout_str = console.exec_command(remote_cmd)
                    return {
                        "stdout": stdout_str,
                        "stderr": "",
                        "returncode": 0
                    }
            except Exception as e:
                print(f"         Remote IPMI execution failed: {e}")
                if self._api_f:
                    self._api_f.write(f"  Remote IPMI execution failed, error: {e}\n\n")
                    self._api_f.flush()
                if self._mq is not None:
                    self._mq.put({"type": "api_body", "text": f"  Remote IPMI execution failed, error: {e}"})
                return {
                    "stdout": "",
                    "stderr": str(e),
                    "returncode": 1
                }
        else:
            print(f"  [IPMI] Executing local command: {cmd_str}")
            if self._api_f:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                self._api_f.write(f"{now_str} - DEBUG - [IPMI  ] {cmd_str}\n")
                self._api_f.flush()
            if self._mq is not None:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                header_line = f"{now_str} - DEBUG - [IPMI  ] {cmd_str}"
                self._mq.put({"type": "api_body", "text": header_line})

            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                return {
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "returncode": res.returncode
                }
            except Exception as e:
                print(f"         Local IPMI execution failed: {e}")
                if self._api_f:
                    self._api_f.write(f"  Local IPMI execution failed, error: {e}\n\n")
                    self._api_f.flush()
                if self._mq is not None:
                    self._mq.put({"type": "api_body", "text": f"  Local IPMI execution failed, error: {e}"})
                return {
                    "stdout": "",
                    "stderr": str(e),
                    "returncode": 1
                }

    def raw(self, netfn, command, data=None, interface_options=None, ipmitool_args=None, **kwargs):
        """實作 IPMI raw 指令的代理，供積木呼叫 ipmitool"""
        if data is None:
            data = []
        
        if ipmitool_args is None and interface_options:
            ipmitool_args = interface_options.get("ipmitool_args", [])
        if ipmitool_args is None:
            ipmitool_args = []

        interface_type = interface_options.get("type", "iol") if interface_options else "iol"
        
        # 決定是否走 Console Server 遠端執行
        use_remote = False
        if self._environment.get("console_server", {}).get("host") and interface_type in ("kcs", "serial"):
            use_remote = True

        raw_args = ["raw", f"0x{netfn:02X}", f"0x{command:02X}"] + [f"0x{b:02X}" for b in data]
        cmd = ["ipmitool"] + ipmitool_args + raw_args
        cmd_str = " ".join(cmd)

        if use_remote:
            print(f"  [Console][IPMI] Executing remote command: {cmd_str}")
            if self._api_f:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                self._api_f.write(f"{now_str} - DEBUG - [IPMI  ] [Console] {cmd_str}\n")
                self._api_f.flush()
            if self._mq is not None:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                header_line = f"{now_str} - DEBUG - [IPMI  ] [Console] {cmd_str}"
                self._mq.put({"type": "api_body", "text": header_line})

            try:
                console = self._get_console_client()
                if console:
                    if interface_type == "kcs":
                        remote_cmd = " ".join(["ipmitool"] + raw_args)
                    else:
                        remote_cmd = " ".join(["ipmitool"] + ipmitool_args + raw_args)
                        
                    stdout_str = console.exec_command(remote_cmd)
                    
                    parsed_data = []
                    if stdout_str:
                        for token in stdout_str.strip().split():
                            try:
                                parsed_data.append(int(token, 16))
                            except ValueError:
                                pass
                    print(f"         IPMI succeeded: {parsed_data}")
                    if self._api_f:
                        self._api_f.write(f"  IPMI succeeded, response: {parsed_data}\n\n")
                        self._api_f.flush()
                    if self._mq is not None:
                        self._mq.put({"type": "api_body", "text": f"  IPMI succeeded, response: {parsed_data}"})
                    return IpmiResponse(stdout_str, "", 0, parsed_data)
            except Exception as e:
                print(f"         Remote IPMI execution failed: {e}")
                if self._api_f:
                    self._api_f.write(f"  Remote IPMI execution failed, error: {e}\n\n")
                    self._api_f.flush()
                if self._mq is not None:
                    self._mq.put({"type": "api_body", "text": f"  Remote IPMI execution failed, error: {e}"})
                return IpmiResponse("", str(e), 1, [])
        else:
            print(f"  [API][IPMI  ] {cmd_str}")
            if self._api_f:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                self._api_f.write(f"{now_str} - DEBUG - [IPMI  ] {cmd_str}\n")
                self._api_f.flush()
            if self._mq is not None:
                import datetime as _dt
                now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                header_line = f"{now_str} - DEBUG - [IPMI  ] {cmd_str}"
                self._mq.put({"type": "api_body", "text": header_line})

            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                parsed_data = []
                if res.stdout and res.returncode == 0:
                    for token in res.stdout.strip().split():
                        try:
                            parsed_data.append(int(token, 16))
                        except ValueError:
                            pass
                resp = IpmiResponse(res.stdout, res.stderr, res.returncode, parsed_data)
                
                # Log output
                if res.returncode == 0:
                    print(f"         IPMI succeeded: {parsed_data}")
                    if self._api_f:
                        self._api_f.write(f"  IPMI succeeded, response: {parsed_data}\n\n")
                        self._api_f.flush()
                    if self._mq is not None:
                        self._mq.put({"type": "api_body", "text": f"  IPMI succeeded, response: {parsed_data}"})
                else:
                    print(f"         IPMI failed: {res.stderr.strip()}")
                    if self._api_f:
                        self._api_f.write(f"  IPMI failed, error: {res.stderr.strip()}\n\n")
                        self._api_f.flush()
                    if self._mq is not None:
                        self._mq.put({"type": "api_body", "text": f"  IPMI failed, error: {res.stderr.strip()}"})
                    
                return resp
            except Exception as e:
                print(f"         IPMI exception: {e}")
                if self._api_f:
                    self._api_f.write(f"  IPMI exception: {e}\n\n")
                    self._api_f.flush()
                if self._mq is not None:
                    self._mq.put({"type": "api_body", "text": f"  IPMI exception: {e}"})
                return IpmiResponse("", str(e), -1)

    def _log(self, method, uri, status, resp_dict=None):
        import datetime as _dt
        now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        icon = "[OK]" if status and str(status).isdigit() and int(status) < 300 else "[!!]"
        
        # 摘要行：透過 stdout 到 SSE + Test log
        print(f"  [API][{method:<6}] {uri} -> {status} {icon}")
        
        # 嘗試從 resp_dict 或 response 對象中提取 body
        body_to_log = resp_dict
        if not body_to_log:
            # 如果傳進來的是 None，嘗試從 context 獲取 (這取決於呼叫者，但這裡維持原樣)
            pass

        # 完整 body：直接寫入 Test log (只有首行帶時間戳記，Body 維持純淨縮排)
        if self._api_f:
            self._api_f.write(f"{now_str} - DEBUG - [{method:<6}] {uri} -> {status} {icon}\n")
            if body_to_log:
                import json as _json
                try:
                    body_str = _json.dumps(body_to_log, indent=2, ensure_ascii=False)
                    for line in body_str.splitlines():
                        self._api_f.write(f"  {line}\n")
                except:
                    self._api_f.write(f"  [Error serialization body]\n")
            self._api_f.write("\n")
            self._api_f.flush()
        # Push the full response body to SSE for task-side api_body events.
        if self._mq is not None:
            import json as _json
            header_line = f"{now_str} - DEBUG - [{method:<6}] {uri} -> {status} {icon}"
            body_lines = []
            if body_to_log:
                try:
                    body_str = _json.dumps(body_to_log, indent=2, ensure_ascii=False)
                    body_lines = [f"  {l}" for l in body_str.splitlines()]
                except:
                    body_lines = ["  [Error serialization body]"]
            full_text = "\n".join([header_line] + body_lines)
            self._mq.put({"type": "api_body", "text": full_text})

    def get(self, uri, **kw):
        r = self._c.get(uri, **kw)
        # 優先嘗試 .dict, 其次 .obj (有些版本 redfish 使用 .obj)
        body = getattr(r, "dict", None) or getattr(r, "obj", None)
        self._log("GET", uri, getattr(r, "status", "?"), body)
        return r

    def post(self, uri, **kw):
        r = self._c.post(uri, **kw)
        body = getattr(r, "dict", None) or getattr(r, "obj", None)
        self._log("POST", uri, getattr(r, "status", "?"), body)
        return r

    def patch(self, uri, **kw):
        r = self._c.patch(uri, **kw)
        body = getattr(r, "dict", None) or getattr(r, "obj", None)
        self._log("PATCH", uri, getattr(r, "status", "?"), body)
        return r

    def put(self, uri, **kw):
        r = self._c.put(uri, **kw)
        body = getattr(r, "dict", None) or getattr(r, "obj", None)
        self._log("PUT", uri, getattr(r, "status", "?"), body)
        return r

    def delete(self, uri, **kw):
        r = self._c.delete(uri, **kw)
        body = getattr(r, "dict", None) or getattr(r, "obj", None)
        self._log("DELETE", uri, getattr(r, "status", "?"), body)
        return r

    def head(self, uri, **kw):
        r = self._c.head(uri, **kw)
        body = getattr(r, "dict", None) or getattr(r, "obj", None)
        self._log("HEAD", uri, getattr(r, "status", "?"), body)
        return r

    def login(self, **kw): return self._c.login(**kw)
    def logout(self):
        if self._console_client:
            try:
                print("  [Console] Closing Console Server connection...")
                self._console_client.close()
            except Exception:
                pass
            self._console_client = None
        return self._c.logout()
