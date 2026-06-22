param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$TaskName = 'YTStrategyAgentWatcher'
)

$ErrorActionPreference = 'Stop'

$python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$watcher = Join-Path $RepoRoot 'watcher.py'

if (-not (Test-Path $python)) {
    throw "Python venv not found at $python. Run scripts\bootstrap_windows.ps1 first."
}

$action = New-ScheduledTaskAction -Execute $python -Argument $watcher -WorkingDirectory $RepoRoot
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'YT Strategy Agent watcher' -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "Registered and started scheduled task: $TaskName"
