# Registers a Windows scheduled task that runs the tracker every 2 hours.
#   powershell -ExecutionPolicy Bypass -File .\register_task.ps1
# Remove it with:  Unregister-ScheduledTask -TaskName JobTracker -Confirm:$false
$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "run.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`"" `
    -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Hours 2)
# StartWhenAvailable: if the PC was off/asleep at run time, run as soon as it's back.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "JobTracker" -Action $action -Trigger $trigger `
    -Settings $settings -Description "Personal embedded job tracker (every 2h)" -Force | Out-Null
Write-Host "Registered task 'JobTracker' (every 2 hours, first run in ~1 minute)."
