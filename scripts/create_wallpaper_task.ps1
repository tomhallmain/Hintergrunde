# Get parameters from command line
param(
    [string]$WallpapersDir,
    [int]$DaysInterval,
    [string]$Time
)

# Get the current script's directory and go up one level to find set_wallpaper.py
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$wallpaperScript = Join-Path $rootDir "set_wallpaper.py"

# Debug output
Write-Host "Debug: Script started"
Write-Host "Debug: Parameters received:"
Write-Host "WallpapersDir: $WallpapersDir"
Write-Host "DaysInterval: $DaysInterval"
Write-Host "Time: $Time"
Write-Host "PSBoundParameters: $($PSBoundParameters | ConvertTo-Json)"

# If parameters are not provided, get them interactively
if (-not $WallpapersDir) {
    $WallpapersDir = Read-Host "Enter the full path to your wallpapers directory"
}

if (-not $DaysInterval) {
    $daysInput = Read-Host "Enter the number of days between rotations (default: 7)"
    if (-not $daysInput -or -not ($daysInput -match '^\d+$')) {
        $DaysInterval = 7
        Write-Host "Using default interval of 7 days"
    } else {
        $DaysInterval = [int]$daysInput
    }
}

if (-not $Time) {
    $timeInput = Read-Host "Enter the time for rotation (HH:MM, default: 09:00)"
    if (-not $timeInput -or -not ($timeInput -match '^([0-1][0-9]|2[0-3]):[0-5][0-9]$')) {
        $Time = "09:00"
        Write-Host "Using default time of 09:00"
    } else {
        $Time = $timeInput
    }
}

# Validate the directory exists
if (-not (Test-Path $WallpapersDir -PathType Container)) {
    Write-Error "Directory $WallpapersDir does not exist"
    exit 1
}

# Create the task action with the same interval for both the task and the script
$action = New-ScheduledTaskAction -Execute "python" -Argument "`"$wallpaperScript`" --rotate `"$WallpapersDir`" --min-days $DaysInterval"

# Create the task trigger
$trigger = New-ScheduledTaskTrigger -Daily -At $Time

# Create the task settings
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Create the task
$taskName = "RotateWallpaper"
$description = "Rotates desktop wallpaper every $DaysInterval days from the specified directory"

# Check if task already exists and remove it
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Register the new task for the current user
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Description $description -Action $action -Trigger $trigger -Settings $settings -Principal $principal

# Show success message only in interactive mode
if (-not $PSBoundParameters.ContainsKey('WallpapersDir')) {
    Write-Host "`nTask created successfully!"
    Write-Host "Task Name: $taskName"
    Write-Host "Description: $description"
    Write-Host "Wallpapers Directory: $WallpapersDir"
    Write-Host "Rotation Interval: $DaysInterval days"
    Write-Host "Rotation Time: $Time"
    Write-Host "`nNote: The task will run every $DaysInterval days at $Time, and the script will only change the wallpaper"
    Write-Host "if it hasn't been changed in the last $DaysInterval days (to avoid repeating wallpapers too soon)."
    Write-Host "`nTo view task logs:"
    Write-Host "1. Open Event Viewer (eventvwr.msc)"
    Write-Host "2. Navigate to: Windows Logs > Application"
    Write-Host "3. Look for entries with source 'Task Scheduler'"
    Write-Host "`nTo modify the task schedule:"
    Write-Host "1. Open Task Scheduler (taskschd.msc)"
    Write-Host "2. Find the task named '$taskName'"
    Write-Host "3. Right-click and select 'Properties'"
} 