# Get the current script's directory and go up one level to find set_wallpaper.py
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$wallpaperScript = Join-Path $rootDir "set_wallpaper.py"

# Set static wallpapers directory to user's Pictures folder
$WallpapersDir = Join-Path $env:USERPROFILE "Pictures"

# Validate the directory exists
if (-not (Test-Path $WallpapersDir -PathType Container)) {
    Write-Error "Directory $WallpapersDir does not exist"
    exit 1
}

# Create the task action
$action = New-ScheduledTaskAction -Execute "python" -Argument "`"$wallpaperScript`" --rotate `"$WallpapersDir`""

# Create a one-time trigger that runs immediately
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)

# Create the task settings
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Create the task
$taskName = "TestWallpaperRotation"
$description = "Test run of wallpaper rotation"

# Check if task already exists and remove it
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Register the new task for the current user
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Description $description -Action $action -Trigger $trigger -Settings $settings -Principal $principal

Write-Host "`nTest task created successfully!"
Write-Host "Task Name: $taskName"
Write-Host "Description: $description"
Write-Host "Wallpapers Directory: $WallpapersDir"
Write-Host "`nThe task will run in 1 minute. To view the results:"
Write-Host "1. Open Event Viewer (eventvwr.msc)"
Write-Host "2. Navigate to: Windows Logs > Application"
Write-Host "3. Look for entries with source 'Task Scheduler'"
Write-Host "`nTo run the task immediately:"
Write-Host "1. Open Task Scheduler (taskschd.msc)"
Write-Host "2. Find the task named '$taskName'"
Write-Host "3. Right-click and select 'Run'" 