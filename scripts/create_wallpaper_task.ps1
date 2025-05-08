# Get the current script's directory and go up one level to find set_wallpaper.py
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$wallpaperScript = Join-Path $rootDir "set_wallpaper.py"

# Get the wallpapers directory from user input
$wallpapersDir = Read-Host "Enter the full path to your wallpapers directory"

# Get the rotation interval from user input (default to 7 days)
$daysInterval = Read-Host "Enter the number of days between rotations (default: 7)"
if (-not $daysInterval -or -not ($daysInterval -match '^\d+$')) {
    $daysInterval = 7
    Write-Host "Using default interval of 7 days"
}

# Create the task action with the same interval for both the task and the script
$action = New-ScheduledTaskAction -Execute "python" -Argument "`"$wallpaperScript`" --rotate `"$wallpapersDir`" --min-days $daysInterval"

# Create the task trigger
$trigger = New-ScheduledTaskTrigger -Daily -DaysInterval $daysInterval

# Create the task settings
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Create the task
$taskName = "RotateWallpaper"
$description = "Rotates desktop wallpaper every $daysInterval days from the specified directory"

# Check if task already exists and remove it
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Register the new task
Register-ScheduledTask -TaskName $taskName -Description $description -Action $action -Trigger $trigger -Settings $settings -User $env:USERNAME -RunLevel Highest

Write-Host "`nTask created successfully!"
Write-Host "Task Name: $taskName"
Write-Host "Description: $description"
Write-Host "Wallpapers Directory: $wallpapersDir"
Write-Host "Rotation Interval: $daysInterval days"
Write-Host "`nNote: The task will run every $daysInterval days, and the script will only change the wallpaper"
Write-Host "if it hasn't been changed in the last $daysInterval days (to avoid repeating wallpapers too soon)."
Write-Host "`nTo view task logs:"
Write-Host "1. Open Event Viewer (eventvwr.msc)"
Write-Host "2. Navigate to: Windows Logs > Application"
Write-Host "3. Look for entries with source 'Task Scheduler'"
Write-Host "`nTo modify the task schedule:"
Write-Host "1. Open Task Scheduler (taskschd.msc)"
Write-Host "2. Find the task named '$taskName'"
Write-Host "3. Right-click and select 'Properties'" 