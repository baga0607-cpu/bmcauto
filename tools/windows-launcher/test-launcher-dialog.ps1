param([string]$OutputPath)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'launcher-dialog.ps1')
foreach ($action in @('Open', 'Restart', 'Cancel')) {
    $form = New-BMCAgentLauncherDialog -Lan $true
    try {
        $form.ShowInTaskbar = $false
        $form.StartPosition = 'Manual'
        $form.Location = New-Object Drawing.Point(-10000, -10000)
        $form.Show()
        [Windows.Forms.Application]::DoEvents()
        if ($form.Controls['ConnectionMode'].SelectedIndex -ne 1) { throw 'LAN default not retained' }
        if ($action -eq 'Restart' -and $OutputPath) {
            $bitmap = New-Object Drawing.Bitmap($form.Width, $form.Height)
            try {
                $form.DrawToBitmap($bitmap, (New-Object Drawing.Rectangle(0, 0, $form.Width, $form.Height)))
                $bitmap.Save($OutputPath)
            } finally { $bitmap.Dispose() }
        }
        $form.Controls[$action].PerformClick()
        if ($form.Tag -ne $action) { throw "Button did not return $action" }
    } finally { $form.Dispose() }
}
Write-Output 'PASS: Open / Restart / Cancel buttons and retained LAN selection; no service action invoked.'
