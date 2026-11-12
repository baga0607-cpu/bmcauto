$ErrorActionPreference = 'Stop'
try {
    $ruleName = 'BMCAgent-Launcher-LAN-5000'
    $pythonPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'BMCAgent\.venv\Scripts\python.exe'
    Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -Name $ruleName -DisplayName 'BMCAgent TCP 5000 (local subnet)' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000 -Program $pythonPath -RemoteAddress LocalSubnet -Profile Domain,Private -EdgeTraversalPolicy Block | Out-Null
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'BMCAgent firewall setup failed') | Out-Null
    exit 1
}
