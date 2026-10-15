# Payload Power Control

## 1
**a.** Post `/redfish/v1/Systems/0/Actions/ComputerSystem.Reset`
```json
{
  "ResetType": "GracefulShutdown"
}
```
Then try other actions: `"ForceOff"`, `"On"`, `"PowerCycle"`, `"ForceRestart"`.

**b.** Enable payload OS NMI function:
```bash
# echo 1 > /proc/sys/kernel/unknown_nmi_panic
```

Post `/redfish/v1/Systems/0/Actions/ComputerSystem.Reset`
```json
{
  "ResetType": "Nmi"
}
```

**DUT shall be:**
- **GracefulShutdown:** DUT do a graceful shutdown.
- **ForceOff:** DUT power off.
- **On:** DUT power on.
- **PowerCycle:** DUT do a power cycle.
- **ForceRestart:** DUT do a cold reset.
- **Nmi:** Trigger payload OS kernel dump.

---

## 2
**a.** Post with OperationApplyTime
`/redfish/v1/Systems/0/Actions/ComputerSystem.Reset`
```json
{
  "ResetType": "GracefulShutdown",
  "@Redfish.OperationApplyTime": "AtMaintenanceWindowStart",
  "MaintenanceWindowStartTime": "<CURRENT_TIME_PLUS_1_MINUTE>"
}
```
*Note: The `MaintenanceWindowStartTime` should be dynamically set to exactly 1 minute after the current execution time, formatted in ISO 8601 string (e.g., `"2024-04-14T15:40:00+08:00"`).*

**b.** Check the system status when the time exceeds the MaintenanceWindowStartTime.

**Expected Results:**
- **a.** It shall return 202 and a task ID.
- **b.** System shall be power off when the time exceeds the MaintenanceWindowStartTime.

---

## 3
**a.** Post with OperationApplyTime
`/redfish/v1/Systems/0/Actions/ComputerSystem.Reset`
```json
{
  "ResetType": "On",
  "@Redfish.OperationApplyTime": "Immediate"
}
```

**b.** Check the system status.

**Expected Results:**
- **a.** It shall return 204.
- **b.** System shall be power on immediately.
