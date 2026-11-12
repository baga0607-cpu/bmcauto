$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'service-control.ps1')
$runtime = 'D:\Fixture\bmca-runtime'
function New-TestProcess($id, $parent, $exe, $script = 'D:\Fixture\bmca-runtime\server.py', $created = 1) {
    [pscustomobject]@{ProcessId=$id; ParentProcessId=$parent; ExecutablePath=$exe; CommandLine=('"'+$exe+'" "'+$script+'"'); CreationDate=$created}
}
function Assert-Ids($actual, $expected) {
    if ((@($actual | ForEach-Object ProcessId) -join ',') -ne ($expected -join ',')) { throw 'Unexpected owned process chain' }
}
$parent = New-TestProcess 100 999 'D:\Fixture\BMCAgent\.venv\Scripts\python.exe'
$child = New-TestProcess 101 100 'D:\Fixture\bmca-runtime\python\python.exe' -created 2
Assert-Ids @(Get-BMCAgentProcessChain @($parent,$child) @(101) $runtime) @(101,100)
Assert-Ids @(Get-BMCAgentProcessChain @($child) @(101,101) $runtime) @(101)
Assert-Ids @(Get-BMCAgentProcessChain @($parent) @(100) $runtime) @(100)
# An unrelated / reused parent must not be stopped, even with the same PID.
$foreign = New-TestProcess 100 999 'C:\Other\python.exe'
Assert-Ids @(Get-BMCAgentProcessChain @($foreign,$child) @(101) $runtime) @(101)
$newParent = New-TestProcess 100 999 'D:\Fixture\BMCAgent\.venv\Scripts\python.exe' -created 3
Assert-Ids @(Get-BMCAgentProcessChain @($newParent,$child) @(101) $runtime) @(101)
foreach ($bad in @(
    (New-TestProcess 101 100 'C:\Other\python.exe'),
    (New-TestProcess 101 100 'D:\Fixture\bmca-runtime\python\python.exe' 'D:\Fixture\bmca-runtime\server.py.evil'),
    (New-TestProcess 101 100 'D:\Fixture\bmca-runtime\python\python.exe' 'D:\Other\server.py')
)) {
    $rejected = $false
    try { $null = Get-BMCAgentProcessChain @($bad) @(101) $runtime } catch { $rejected = $true }
    if (-not $rejected) { throw 'Unrelated listener accepted' }
}
$rejected = $false
try { $null = Get-BMCAgentProcessChain @($parent,$child) @(100,101) $runtime } catch { $rejected = $true }
if (-not $rejected) { throw 'Multiple listeners accepted' }
function Invoke-RestMethod { [pscustomobject]@{active_runs=@(@{id='active'})} }
$rejected = $false
try { Assert-BMCAgentIdle 'http://fixture' } catch { $rejected = $true }
if (-not $rejected) { throw 'Active test was not protected' }
function Invoke-RestMethod { [pscustomobject]@{active_runs=@()} }
Assert-BMCAgentIdle 'http://fixture'
function Invoke-RestMethod { [pscustomobject]@{} }
$rejected = $false
try { Assert-BMCAgentIdle 'http://fixture' } catch { $rejected = $true }
if (-not $rejected) { throw 'Unknown execution state accepted' }
Write-Output 'PASS: 12 ownership and active-test cases; no live process stopped.'
