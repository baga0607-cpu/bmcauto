# Connection groups and console login contract — 2026-11-11

## Delivered locally

Task Info → Connection uses three native collapsible groups, initially expanded. Each row retains the compact inline label: field format.

| Group | Fields in order | Existing settings keys |
| --- | --- | --- |
| BMC | BMC IP, BMC User, BMC Password | host, username, password |
| Console Server | Server IP, Server User, Server Password, Console Port | cs_host, cs_username, cs_password, derived dut_connect_cmd |
| DUT OS | DUT User, DUT Password | dut_os_username, dut_os_password |

Password fields remain masked. Collapsing does not change form values or dirty state; values in collapsed groups are saved. Invalid Console Port expands its group so native validation can focus it. Existing save/discard, concurrent-change checks and execution locks remain.

Console Port accepts 1–65535. Existing `telnet localhost <port>` and `telnet 0 <port>` are both recognized. Saving a nonempty port sets `dut_connect_cmd = "telnet 0 <port>"`. An empty port retains an existing custom command, as before. Hidden SSH port/protocol, TLS settings, DUT OS settings, exit and force-connect commands are preserved. Bare BMC input still receives HTTPS on save. No schema migration or backend change is required.

## User-specified case / shared connection contract (not implemented in this change)

1. SSH into Console Server using Server IP/User/Password and the existing SSH port.
2. In that Console Server shell execute `telnet 0 <console port>`.
3. If the response explicitly reports that this console port is occupied, execute `cpc <console port>` on Console Server to release the occupied connection, then retry `telnet 0 <console port>`.
4. If DUT OS presents login/password prompts, use DUT User/Password. If already at the DUT shell, do not send credentials blindly.
5. After confirming the DUT shell, case.py runs the commands required by its test method.

Do not run cpc unconditionally or treat every timeout, refusal or authentication failure as proven occupancy. Actual Console Server response text and retry limits must be verified in the shared connection implementation. This UI change does not populate force_connect_cmd with cpc, change ConsoleClient, or run any SSH/Telnet/cpc operation. Legacy ConsoleClient has its own configurable force-connect behavior; that is not a newly implemented cpc occupancy/reconnect contract.

No case.py files, including the 13 RF-01 sources, are changed. RF-01 continues using the existing Redfish contract. The next phase is shared transport/conditional recovery, not a blanket rewrite of all cases.

## Verification

- Node syntax check for task_info_drawer.js passed.
- Isolated Chrome fixture loads the actual Task Info/TaskManagement scripts and CSS with mocked services. Verified exact group/field order, three masked password inputs, mouse/keyboard collapse without dirty changes, DUT credential save, telnet localhost-to-0 mapping, HTTPS normalization, preservation of hidden values and custom commands, validation of a collapsed invalid port, discard, and nine disabled inputs while executing.
- Light 1440×900 and dark 1280×720 screenshots inspected; rows remain aligned with no horizontal content overflow.
- Existing test_task_environment.py: 5 tests passed with isolated workspace/main/temp and the required web_ui/main_program Python paths. Initial invocation lacked main_program on PYTHONPATH; corrected invocation passed.
- A localhost preview attempt was inaccessible from the browser; UI verification instead used the isolated in-memory service fixture. This is not a physical Console Server/DUT connection test.
- No formal Task data was modified and no service restart is needed for static assets. Reload the existing local application.

Local verification artifacts: bmca-runtime/verification/connection-20261111.

## Publication boundary

The local Task Info drawer integration predates this change but its JS/CSS assets were still untracked and absent from the publication checkout. This submission preserves those complete current assets together with this narrowly scoped Connection update. Other outstanding platform changes (index/workbench/TaskManagement/backend integration) are not bundled here. A fresh remote checkout therefore still needs the earlier Task Info integration before these assets become a live UI; the currently running local checkout already has that integration. Do not interpret this source publication as a full platform release.

## Manual Console Port entry (latest user decision)

Console Port is a plain text input, without number steppers, numeric inputMode, integer validation or range validation. Its value is appended as entered to telnet 0; no Number conversion is performed. Existing telnet 0/localhost values round-trip as text. Blank retains the existing command. This supersedes the earlier 1–65535 validation described above. No case.py or connection executor is changed.
