# BMCAgent · case.py 作者指南（草稿）

這份指南供撰寫新 Case 的夥伴使用。下列 Python 是建議的作者介面，正式執行器仍需實作對應功能。範例從兩個位置讀取同一個 BMC 的 Device ID，每條路徑各有一個必要 Checkpoint。

目前共識、分享前待定案的項目，以及兩個 UI 原型的暫緩紀錄，見[作者指南決策紀錄](status/2026-11-18-case-authoring-decisions.md)。

**語言約定**：本指南供 AI 與使用者閱讀，正文可使用中文。依指南產生的整份 `case.py` 必須使用英文，不得含有中文，範圍包含識別名稱、註解、docstring、測試資料字串、Case 與 Checkpoint 名稱、Expected、Result、Reason、Note、Record、Log 及例外訊息。交付前檢查整份原始檔，包括不會顯示在畫面上的文字。

## 先畫出測試路徑

| Checkpoint | 平台先建立的操作環境 | IPMI 指令在哪裡執行 | 指令如何到達 BMC |
|---|---|---|---|
| `lan_device_id` | BMCAgent 用 SSH 登入 Console Server | Console Server 的 shell | 經公司 LAN，以 RMCP+ 送到 BMC 的 `port1` |
| `kcs_device_id` | BMCAgent 用 SSH 登入 Console Server，再從該機執行 `telnet 0 40110`，經 Console cable 進入 DUT OS | DUT 的 shell | 經 DUT 本機 KCS 送到 BMC |

`environments` 定義如何取得某個 shell。`command_routes` 引用該環境，定義最後一段如何發送指令。Case 明確選擇驗證路徑；平台若無法建立該路徑，就把原因交還 Case。這兩條路徑都不需要 Redfish。

## 完整 case.py 範例

本例假設測試機台已確認 DUT 的本機 IPMI 介面對應 KCS。兩筆 Checkpoint 驗證各自可讀到 Device ID 數值；若測試目的還包含比較兩個數值是否相同，應宣告第三筆 Checkpoint。

```python
import re


environments = {
    "console_server_os": {
        "from": "bmcagent",
        "to": "console_server_os",
        "method": "ssh",
        "host": "task.console_server.ip",
        "port": "task.console_server.ssh_port",
        "username": "task.console_server.username",
        "password": "task.console_server.password",
    },
    "dut_console": {
        "from": "console_server_os",
        "to": "dut_os",
        "method": "telnet_console",
        "port": "task.console_server.console_port",
        "username": "task.dut.username",
        "password": "task.dut.password",
        "prompt": "task.dut.shell_prompt",
    },
}

command_routes = {
    "console_server_lan": {
        "from": "console_server_os",
        "to": "bmc",
        "method": "ipmi_lanplus",
        "lan_port": "task.bmc.lan_ports.port1",
        "username": "task.bmc.username",
        "password": "task.bmc.password",
    },
    "dut_kcs": {
        "from": "dut_console",
        "to": "bmc",
        "method": "ipmi_kcs",
    },
}

checkpoints = {
    "lan_device_id": {
        "name": "Read the BMC Device ID over LAN from the Console Server",
        "route": "console_server_lan",
        "expected": "mc info succeeds and returns a numeric Device ID",
    },
    "kcs_device_id": {
        "name": "Read the BMC Device ID over KCS from the DUT",
        "route": "dut_kcs",
        "expected": "mc info succeeds and returns a numeric Device ID",
    },
}


def check_device_id(ctx, checkpoint_id, route):
    result = ctx.ipmi(route=route, args=["mc", "info"])
    if not result.ok:
        error = result.error
        reason = f"{error.hop}: {error.summary}"
        if error.phase == "ipmi":
            ctx.checkpoint(checkpoint_id, "FAIL", reason)
        elif error.phase == "setup":
            # A non-connection prerequisite failed (e.g. ipmitool is missing).
            # A lost connection before dispatch uses the platform flow below.
            ctx.mark_blocked(checkpoint_id, reason)
        else:
            raise RuntimeError(f"Unknown failure phase {error.phase}: {reason}")
        return

    match = re.search(
        r"^[ \t]*Device ID[ \t]*:[ \t]*(\d+)[ \t]*\r?$",
        result.stdout,
        re.MULTILINE,
    )
    if match is None:
        ctx.checkpoint(checkpoint_id, "FAIL", "mc info returned no numeric Device ID")
    else:
        ctx.checkpoint(checkpoint_id, "PASS", f"Device ID = {match.group(1)}")


def run(ctx):
    # Check every required route on both entry and resume, including saved ones.
    connections = ctx.prepare_connections(checkpoints)
    if connections.paused:
        return  # The platform retains the run and does not finalize the Case.

    for checkpoint_id, spec in checkpoints.items():
        if ctx.checkpoint_finished(checkpoint_id):
            continue

        route = spec["route"]
        if not connections.ready(route):
            ctx.mark_blocked(checkpoint_id, connections.reason(route))
            continue

        check_device_id(ctx, checkpoint_id, route)
```

### Task Connection 欄位怎麼用

| 設定 | 使用時機 |
|---|---|
| Console Server 的 Server IP、SSH Port、Server User、Server Password | 兩條路徑都從 BMCAgent 登入 Console Server |
| Console Server 的 Console Port | 只有 `dut_console` 使用。平台在 Console Server 的 OS 執行 `telnet 0 <Console Port>`。Port 填 `40110` 時，實際指令就是 `telnet 0 40110` |
| DUT User、DUT Password、Shell Prompt | 平台先辨識 Console 畫面。看到登入提示才使用 DUT 帳密；已看到 DUT Shell Prompt 就直接使用。無法辨識時回報前置受阻 |
| BMC User、BMC Password、`lan_ports.port1` | LAN 路徑以該筆的 `ip` 和 BMC 帳密發送指令。填了 BMC IP 就必須有 `ipmi_channel`，例如 `port1 = {"ip": "192.0.2.10", "ipmi_channel": 1}`。只有指令本身需要 channel（如 `lan print 1`）時才傳入該數值 |

KCS 使用 DUT 本機介面。上例取得 DUT shell 的方式是 Console cable，因此整個 KCS 路徑都用不到 DUT IP、DUT SSH Port 或 BMC LAN 帳密。若測試指定從 BMCAgent 發送 LAN 指令，可將該 LAN 路徑的 `from` 設為 `bmcagent`。

## Checkpoint、Case 與紀錄

- **固定 Checkpoint** 在執行前宣告名稱及預期結果。**動態 Checkpoint** 在發現實際項目時，以可識別該項目的唯一名稱或識別值登記，再記錄結果。若列舉本身中斷，記錄中斷位置及原因；報告僅列出已知項目。
- **PASS／FAIL** 表示已執行驗證。已從 Console Server 發起 RMCP+ 請求，但 BMC 逾時，此例判 FAIL。若連 Console Server 都無法登入，則記「未執行（前置受阻）」並保留原因。
- **C-PASS** 適用於 Case 事先定義的條件式通過，需附 Note 說明符合哪項條件。**Skip** 適用於作者依測試條件明確判為不適用的項目，需附原因。已宣告但因受阻、中止或例外而沒做到的項目，保留「未執行」及原因。不可把全部 Skip 當成 PASS；全數不適用時，Case 最終顯示 Skip 或 Block 的通用規則仍待定稿。
- **程式例外** 交給平台留下例外類型、訊息與發生位置，保留已完成的 Checkpoint，尚待執行者標記未執行。程式執行錯誤與連線受阻分開記錄。
- **Log 與報告**：平台記錄每次 Command 的路徑、執行位置、指令及回應，遮蔽密碼。Case 可以用 Record 留下當次查到的 IP 等觀察。Checkpoint 寫判定及直接原因。報告同一欄先寫 Judgement，換行寫 Result；沒有 Judgement 就直接寫 Result。

**LAN／KCS 範例完成後的整體判定**採用下表。Task 暫停期間先保留執行進度；恢復並完成測試，或依「繼續測試」跑完流程後，再彙整 Case 結果。每條路徑各自嘗試，即使都依賴 Console Server，第一條的連線錯誤也只證明該次嘗試受阻。

| LAN Checkpoint | KCS Checkpoint | Case | 理由 |
|---|---|---|---|
| PASS | PASS | PASS | 兩項必要驗證皆通過 |
| FAIL | PASS | FAIL | LAN 已實測失敗 |
| PASS | 未執行（前置受阻） | Block | 缺少 KCS 的必要驗證 |
| 未執行（前置受阻） | 未執行（前置受阻） | Block | 兩項皆無法驗證 |
| FAIL | 未執行（前置受阻） | FAIL | 保留已確認的失敗，也保留另一項的受阻原因 |

平台回傳的失敗資料包含 `phase`（`setup` 或 `ipmi`）、`hop`（路段）、`code`（原因代碼）、`summary`（可讀說明）。例如缺少 ipmitool 屬於 setup，但原因是工具缺失；SSH 逾時同屬 setup，原因才是連線異常。排程選項需要分辨這兩者。

## 固定設定、動態設定與關閉連線

每個 Case 從 Task Connection 的固定設定開始。是否查詢動態值、可接受哪個來源、何時重試，取決於 Case 的測試目的。例如驗證「能否 SSH 登入 DUT 目前的 IP」時，可先嘗試已宣告的 `dut_ssh`；若從 Console Server 連向 DUT IP 的那一段失敗，可透過 `dut_console` 查指定網卡目前的 IP，再呼叫 `ctx.connect("dut_ssh", target_ip=new_ip)`。若失敗的是登入 Console Server，本次查 DUT IP 對該路段沒有幫助。

動態 IP 僅供當次 Case 使用，保存於區域變數，並明確傳給該次連線呼叫。平台將來源與嘗試結果寫入 Log，Case 不得寫回 Task。每個 Case 結束或發生例外時，平台釋放它建立的連線；只有測試步驟需要提早斷線時，作者才呼叫 `session.close()`。

## 連線確認與 Checkpoint 續跑契約

1. 在固定 Checkpoint 宣告穩定的識別值及 `route`。初次啟動與每次續跑，`ctx.prepare_connections(checkpoints)` 都重新讀取該 Task 最新 Connection，確認本 Case **全部**必要路徑。LAN 確認 Console Server 的 SSH shell 和所需 BMC 欄位；KCS 確認可經 Console Port 取得 DUT shell。兩條均完成確認後才套用選項。確認時不先執行驗證命令 `mc info`。
2. 平台把 Checkpoint 結果連同本次執行、Case 及 Checkpoint 識別值保存。續跑仍屬同一次執行；重檢包含已完成項目使用的路徑。`ctx.checkpoint_finished()` 只有在檢驗完連線後才用來略過已有最終結果的項目（包括 PASS、FAIL）。前置受阻的「未執行」仍待處理。另行啟動新一輪測試時不沿用舊結果。
3. 若驗證途中發現連線中斷且確認指令尚未送出，平台在 `ctx.ipmi()` 的發送邊界記下路段及當前項目，交回同一套「檢驗全部必要連線 → 套用選項」流程。此類斷線不以一般 setup 錯誤返回給上例。暫停會退出本次呼叫並保留進度；續跑以同一執行再次進入 `run(ctx)`。若已送出但結果不明，保存證據，由 Case 依指令性質與設備現況判斷可否重送。
4. 例：LAN 已記 PASS，發送 KCS 指令前 DUT Console 中斷。測試者修正 Console Port 後按 **Resume**。即使 LAN 已完成，仍要複檢 LAN 和 KCS；兩者都可用後，LAN 沿用原 PASS，只發送尚未執行的 KCS 指令。若第一次確認就受阻而暫停，兩項都尚未執行，恢復後兩項都要做。

## Execution 選項 · Keep Testing if Disconnected

**判斷時點**為目前 Case 所需的前置連線全部確認完畢時。每條連線先試 Task Connection 的固定設定；需要動態處理時，由 Case 取得新值並要求平台重試。平台保留每個路段的嘗試紀錄。固定設定失敗、動態設定成功，該連線即為可用。只要最後仍有任一條必要連線受阻，平台立即套用本次 Task 的「連線受阻時」選項，無須等待 Checkpoint 或整個 Case 的最終判定。

| 選項 | 平台行為 |
|---|---|
| Off（暫停） | 立即暫停該 Task 本次執行中的所有測試工作，包括目前 Case 的剩餘步驟與後續 Case。保留已完成的步驟、結果及連線紀錄，並在該 Task 的 Execution 頁面提示測試者。 |
| On（繼續） | 依 Case 原本的流程跑完。能執行的 Checkpoint 照常驗證；因缺少前置連線而無法執行的項目，保留「未執行（前置受阻）」及原因。Case 依既有規則彙整，再繼續後續測試。 |

**測試者如何恢復執行**

1. 在該 Task 的 Execution 頁面查看暫停位置、受阻的路段、固定與動態設定的嘗試結果，以及各次失敗原因。
2. 手動排除問題。若連線參數有變動，由測試者在該 Task 的 Connection 頁面更新；只有現場接線或服務需要修復時，可沿用原設定。Case 的動態值僅供當次使用，Case 不得寫回 Task。
3. 回到 Execution 頁面啟動測試。平台重新讀取最新的 Task Connection，重新檢驗目前 Case 所需的全部前置連線。
4. 全部通過才恢復目前 Case 並執行剩餘測試。仍有受阻就維持暫停，刷新路段與原因，讓測試者繼續排除。已完成的驗證及暫停前的證據應保留。

**Case A 範例**：Case A 需要 DUT SSH 與 DUT Console。DUT SSH 使用固定 IP 連不上，Case 透過可用的 Console 查得新 IP，重試 SSH 仍失敗。此時兩條連線都已確認：Console 可用、SSH 受阻。選「停止測試」就立即暫停；即使下一個步驟能經 Console 執行，也要等測試者排除問題並通過連線復檢。選「繼續測試」則依原流程執行可用的 Console 步驟，保留 SSH 步驟的受阻原因。

**與 LAN／KCS 範例的關係**：平台確認各條路徑所需的前置連線；Case 負責動態處理與測試判定。對 BMC 發送的 `mc info` 是本例的驗證指令。若前置連線都可用，該指令逾時依規則記 FAIL。若另外有一條前置連線在確認完畢後仍受阻，平台照常套用「連線受阻時」選項，已記錄的 FAIL 保留。
