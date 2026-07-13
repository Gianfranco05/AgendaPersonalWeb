# Register a Windows scheduled task that runs shutdown_hook.py on system shutdown
# Run as Administrator: powershell -ExecutionPolicy Bypass -File scripts\register_shutdown_task.ps1

$ScriptPath = Join-Path $PSScriptRoot "shutdown_hook.py"
$PythonExe = (Get-Command python).Source
$TaskName = "LifeOS-ShutdownHook"
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "$ScriptPath --force --log-level INFO"
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

# Register the task (triggers on Windows shutdown event via EventID 1074)
$CimTrigger = @(
    @{
        Subscription = @(
            @{
                Query = @"
<QueryList>
  <Query Id="0" Path="System">
    <Select Path="System">*[System[EventID=1074]]</Select>
  </Query>
</QueryList>
"@
            }
        )
    }
)

try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Principal $Principal -Settings $Settings -Trigger $Trigger -Force
    Write-Host "Task '$TaskName' registered successfully."

    # Also create a second task triggered by EventID 1074 for immediate shutdown detection
    $TaskNameEvent = "LifeOS-ShutdownHook-Event"
    Unregister-ScheduledTask -TaskName $TaskNameEvent -Confirm:$false -ErrorAction SilentlyContinue

    $ActionEvent = New-ScheduledTaskAction -Execute $PythonExe -Argument "$ScriptPath --force --log-level INFO"
    Register-ScheduledTask -TaskName $TaskNameEvent -Action $ActionEvent -Principal $Principal -Settings $Settings -Trigger $CimTrigger -Force
    Write-Host "Task '$TaskNameEvent' registered successfully (EventID 1074 trigger)."
}
catch {
    Write-Error "Failed to register scheduled task: $_"
    exit 1
}
