function New-BMCAgentLauncherDialog {
    param([bool]$Lan = $false)
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    [Windows.Forms.Application]::EnableVisualStyles()
    $form = New-Object Windows.Forms.Form
    $form.Text = 'BMCAgent'; $form.ClientSize = New-Object Drawing.Size(510, 210)
    $form.StartPosition = 'CenterScreen'; $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $false; $form.MinimizeBox = $false
    $form.Font = New-Object Drawing.Font('Segoe UI', 10)
    $heading = New-Object Windows.Forms.Label
    $heading.Text = 'Open BMCAgent or restart its service.'
    $heading.SetBounds(22, 18, 470, 28); $form.Controls.Add($heading)
    $label = New-Object Windows.Forms.Label
    $label.Text = 'Connection mode'; $label.SetBounds(22, 62, 145, 25); $form.Controls.Add($label)
    $mode = New-Object Windows.Forms.ComboBox
    $mode.Name = 'ConnectionMode'; $mode.DropDownStyle = 'DropDownList'
    $mode.SetBounds(175, 58, 310, 30)
    [void]$mode.Items.Add('This computer only'); [void]$mode.Items.Add('Local network (LAN)')
    $mode.SelectedIndex = [int]$Lan; $form.Controls.Add($mode)
    $help = New-Object Windows.Forms.Label
    $help.Text = 'Restart reloads updated code. Running tests must finish first.'
    $help.SetBounds(22, 103, 465, 38); $form.Controls.Add($help)
    foreach ($entry in @(@('Open', 'Open BMCAgent', 22), @('Restart', 'Restart service', 184), @('Cancel', 'Cancel', 346))) {
        $button = New-Object Windows.Forms.Button
        $button.Name = $entry[0]; $button.Text = $entry[1]; $button.Tag = $entry[0]
        $button.SetBounds([int]$entry[2], 157, 140, 34)
        $button.Add_Click({ $window = $this.FindForm(); $window.Tag = $this.Tag; $window.Close() })
        $form.Controls.Add($button)
        if ($entry[0] -eq 'Open') { $form.AcceptButton = $button }
        if ($entry[0] -eq 'Cancel') { $form.CancelButton = $button }
    }
    return $form
}

function Show-BMCAgentLauncherDialog {
    param([bool]$Lan = $false)
    $form = New-BMCAgentLauncherDialog -Lan $Lan
    try {
        [void]$form.ShowDialog()
        return @{ Action = $form.Tag; Mode = @('Local', 'LAN')[$form.Controls['ConnectionMode'].SelectedIndex] }
    } finally { $form.Dispose() }
}
