# Pure process identification is separate from stopping live processes for tests.
function Get-BMCAgentProcessChain {
    param([object[]]$Processes, [int[]]$ListenerIds, [string]$Runtime)
    $root = Split-Path -Parent $Runtime
    $scriptPath = [IO.Path]::GetFullPath((Join-Path $Runtime 'server.py'))
    $allowed = @([IO.Path]::GetFullPath((Join-Path $root 'BMCAgent\.venv\Scripts\python.exe')),
                 [IO.Path]::GetFullPath((Join-Path $Runtime 'python\python.exe')))
    $byId = @{}
    foreach ($item in $Processes) { $byId[[int]$item.ProcessId] = $item }
    $owners = @($ListenerIds | Select-Object -Unique)
    if ($owners.Count -ne 1) { throw 'Expected one BMCAgent listener. No process was stopped.' }
    $chain = @(); $seen = @{}; $current = [int]$owners[0]
    while ($byId.ContainsKey($current) -and -not $seen.ContainsKey($current)) {
        $item = $byId[$current]
        $tokens = @([regex]::Matches([string]$item.CommandLine, '"[^"]*"|\S+') | ForEach-Object { $_.Value.Trim('"') })
        $owned = $item.ExecutablePath -in $allowed -and $tokens.Count -ge 2 -and $tokens[1] -eq $scriptPath
        if (-not $owned) { break }
        if ($chain.Count -and $item.CreationDate -gt $chain[-1].CreationDate) { break }
        $seen[$current] = $true
        $chain += $item
        $current = [int]$item.ParentProcessId
    }
    if (-not $chain.Count) { throw 'Port 5000 does not belong to this BMCAgent launcher. No process was stopped.' }
    # Listener first, then only its verified Python launcher ancestors. server.pid
    # is a hint for operators, never authority to terminate a reused PID.
    return $chain
}

function Assert-BMCAgentIdle {
    param([string]$Url)
    $active = Invoke-RestMethod "$Url/api/run/active" -TimeoutSec 5
    if ($null -eq $active.active_runs) { throw 'Unable to verify active Tasks. Restart cancelled.' }
    if (@($active.active_runs).Count) { throw 'Tasks are running. Finish or stop them before restarting.' }
}

function Stop-BMCAgentService {
    param([string]$Runtime, [string]$Url)
    $listeners = @(Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue)
    if (-not $listeners.Count) { throw 'Service changed during restart. Please try again.' }
    $chain = @(Get-BMCAgentProcessChain -Processes @(Get-CimInstance Win32_Process) -ListenerIds @($listeners.OwningProcess) -Runtime $Runtime)
    Assert-BMCAgentIdle $Url
    foreach ($item in $chain) {
        $live = Get-CimInstance Win32_Process -Filter "ProcessId = $($item.ProcessId)"
        if (-not $live) { continue }
        if ($live.CreationDate -ne $item.CreationDate -or $live.CommandLine -ne $item.CommandLine -or $live.ExecutablePath -ne $item.ExecutablePath) {
            throw 'Process identity changed. Restart cancelled without stopping the replacement process.'
        }
        Stop-Process -Id $item.ProcessId -ErrorAction Stop
        Wait-Process -Id $item.ProcessId -Timeout 10 -ErrorAction SilentlyContinue
    }
    if (Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue) {
        throw 'Port 5000 is still occupied. No replacement service was started.'
    }
}
