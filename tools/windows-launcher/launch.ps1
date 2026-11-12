param(
    [switch]$NoBrowser,
    [ValidateSet('Ask', 'Local', 'LAN')][string]$Mode = 'Ask',
    [ValidateSet('Ask', 'Open', 'Restart')][string]$Action = 'Ask'
)

$ErrorActionPreference = 'Stop'
$taskUrl = 'http://127.0.0.1:5000'
. (Join-Path $PSScriptRoot 'service-control.ps1')
. (Join-Path $PSScriptRoot 'launcher-dialog.ps1')

function Test-BMCAgentReady {
    try {
        $response = Invoke-WebRequest -Uri $taskUrl -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200 -and $response.Content -match '<title>\s*BMCAgent\s*</title>'
    } catch { return $false }
}

try {
    $listener = @(Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue)
    $isLan = @($listener | Where-Object { $_.LocalAddress -notin @('127.0.0.1', '::1') }).Count -gt 0
    if ($Action -eq 'Ask' -and -not $NoBrowser) {
        $choice = Show-BMCAgentLauncherDialog -Lan $isLan
        if (-not $choice.Action -or $choice.Action -eq 'Cancel') { exit 0 }
        $Action = $choice.Action; $Mode = $choice.Mode
    }
    if ($Action -eq 'Ask') { $Action = 'Open' }
    if ($Mode -eq 'Ask') { $Mode = if ($isLan) { 'LAN' } else { 'Local' } }
    $allowLan = $Mode -eq 'LAN'
    $restart = $false; $backupPath = $null
    if ($listener.Count) {
        if (-not (Test-BMCAgentReady)) { throw 'Port 5000 is occupied by a service that is not a ready BMCAgent instance.' }
        $restart = $Action -eq 'Restart' -or $isLan -ne $allowLan
        if ($restart) {
            # Validate ownership before requesting elevation, backing up, or stopping.
            $null = @(Get-BMCAgentProcessChain -Processes @(Get-CimInstance Win32_Process) -ListenerIds @($listener.OwningProcess) -Runtime $PSScriptRoot)
            if ($Action -ne 'Restart') {
                if ($NoBrowser) { throw 'Changing connection mode requires -Action Restart.' }
                $answer = [System.Windows.Forms.MessageBox]::Show('Changing connection mode requires restarting BMCAgent. Restart now?', 'BMCAgent', 'YesNo', 'Question', 'Button2')
                if ($answer -ne 'Yes') { exit 0 }
            }
            Assert-BMCAgentIdle $taskUrl
        }
    }
    if ($allowLan) {
        $firewallScript = Join-Path $PSScriptRoot 'launcher-firewall.ps1'
        $firewallProcess = Start-Process powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$firewallScript`"" -Wait -PassThru
        if ($firewallProcess.ExitCode -ne 0) { throw 'Local network firewall setup did not complete.' }
    }
    $taskRoot = Split-Path -Parent $PSScriptRoot
    $taskPython = Join-Path $taskRoot 'BMCAgent\.venv\Scripts\python.exe'
    $taskDatabase = Join-Path $taskRoot 'BMCAgent\web_ui\workspace\testcase_meta.db'
    if ($restart) {
        Assert-BMCAgentIdle $taskUrl
        $backupPath = Join-Path $PSScriptRoot ('backups\restart-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
        & $taskPython (Join-Path $PSScriptRoot 'restart-backup.py') before $taskDatabase $backupPath
        if ($LASTEXITCODE -ne 0) { throw 'Database backup failed. The existing service was not stopped.' }
        Stop-BMCAgentService -Runtime $PSScriptRoot -Url $taskUrl
    }
    if (-not (Test-BMCAgentReady)) {
        & (Join-Path $PSScriptRoot 'start.ps1') -AllowLan:$allowLan
        $deadline = (Get-Date).AddSeconds(30)
        while (-not (Test-BMCAgentReady)) {
            if ((Get-Date) -ge $deadline) { throw "BMCAgent did not become ready. See $PSScriptRoot\stderr.log" }
            Start-Sleep -Milliseconds 500
        }
    }
    if ($backupPath) {
        & $taskPython (Join-Path $PSScriptRoot 'restart-backup.py') after $taskDatabase $backupPath
        if ($LASTEXITCODE -ne 0) { throw "Service restarted, but data verification needs review. Backup: $backupPath" }
    }
    if (-not $NoBrowser) {
        $chromePaths = @(
            "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
            "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
        )
        $chrome = $chromePaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $chrome) {
            throw 'Google Chrome was not found. Please install Chrome and try again.'
        }
        Start-Process -FilePath $chrome -ArgumentList $taskUrl
    }
    Write-Output "BMCAgent is ready: $taskUrl"
    if ($allowLan -and -not $NoBrowser) {
        $addresses = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*' -and $_.AddressState -eq 'Preferred' }
        $urls = ($addresses | ForEach-Object { "http://$($_.IPAddress):5000" }) -join "`n"
        [System.Windows.Forms.MessageBox]::Show("Local network access is enabled.`nUse the address for your connected network:`n`n$urls", 'BMCAgent LAN addresses') | Out-Null
    }
} catch {
    if ($NoBrowser) { [Console]::Error.WriteLine($_.Exception.Message) }
    else {
        Add-Type -AssemblyName System.Windows.Forms
        [void][System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'BMCAgent startup failed')
    }
    exit 1
}
