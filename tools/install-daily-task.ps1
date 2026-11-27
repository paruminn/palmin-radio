$ErrorActionPreference = 'Stop'
$taskName = 'Palmin Radio Daily'
$stateRoot = Join-Path $env:LOCALAPPDATA 'PalminRadio'
$runScript = Join-Path $PSScriptRoot 'daily-run.ps1'

New-Item -ItemType Directory -Path $stateRoot -Force | Out-Null

$action = New-ScheduledTaskAction -Execute (Join-Path $PSHOME 'powershell.exe') -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runScript`""
$trigger = New-ScheduledTaskTrigger -Daily -At '06:20'
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Generate and publish Palmin Radio every day at 06:20 Japan time.' -Force | Out-Null

Write-Host "Scheduled '$taskName' daily at 06:20. The task runs when this Windows account is signed in; missed runs start when the PC is available."
Write-Host "Logs: $(Join-Path $stateRoot 'logs')"
