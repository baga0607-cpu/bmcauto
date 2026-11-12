param([switch]$AllowLan)

$ErrorActionPreference = 'Stop'
$taskRuntime = $PSScriptRoot
$taskRoot = Split-Path -Parent $taskRuntime
$taskPython = Join-Path $taskRoot 'BMCAgent\.venv\Scripts\python.exe'
if (Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 5000 is already in use.' }
$taskArguments = '"' + (Join-Path $taskRuntime 'server.py') + '"'
if ($AllowLan) { $taskArguments += ' --lan' }
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList $taskArguments -WorkingDirectory (Join-Path $taskRoot 'BMCAgent\web_ui') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskRuntime 'stdout.log') -RedirectStandardError (Join-Path $taskRuntime 'stderr.log') -PassThru
$taskProcess.Id | Set-Content (Join-Path $taskRuntime 'server.pid')
Write-Output "BMCAgent PID: $($taskProcess.Id); URL: http://127.0.0.1:5000"
