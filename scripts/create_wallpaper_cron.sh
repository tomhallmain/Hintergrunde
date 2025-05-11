#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Go up one directory to find set_wallpaper.py
WALLPAPER_SCRIPT="$(dirname "$SCRIPT_DIR")/set_wallpaper.py"

# Check if the wallpaper script exists
if [ ! -f "$WALLPAPER_SCRIPT" ]; then
    echo "Error: set_wallpaper.py not found in $(dirname "$SCRIPT_DIR")"
    exit 1
fi

# Make sure the wallpaper script is executable
chmod +x "$WALLPAPER_SCRIPT"

# Check if parameters are provided
if [ $# -eq 3 ]; then
    # Use provided parameters
    WALLPAPERS_DIR="$1"
    DAYS_INTERVAL="$2"
    TIME_STR="$3"
else
    # Get the wallpapers directory from user input
    read -p "Enter the full path to your wallpapers directory: " WALLPAPERS_DIR

    # Get the rotation interval
    read -p "Enter the number of days between rotations (default: 7): " DAYS_INTERVAL
    if ! [[ "$DAYS_INTERVAL" =~ ^[0-9]+$ ]]; then
        DAYS_INTERVAL=7
        echo "Using default interval of 7 days"
    fi

    # Get the time
    read -p "Enter the time for rotation (HH:MM, default: 09:00): " TIME_STR
    if ! [[ "$TIME_STR" =~ ^([0-1][0-9]|2[0-3]):[0-5][0-9]$ ]]; then
        TIME_STR="09:00"
        echo "Using default time of 09:00"
    fi
fi

# Validate the directory exists
if [ ! -d "$WALLPAPERS_DIR" ]; then
    echo "Error: Directory $WALLPAPERS_DIR does not exist"
    exit 1
fi

# Validate days interval
if ! [[ "$DAYS_INTERVAL" =~ ^[0-9]+$ ]]; then
    echo "Error: Days interval must be a positive integer"
    exit 1
fi

# Validate time format
if ! [[ "$TIME_STR" =~ ^([0-1][0-9]|2[0-3]):[0-5][0-9]$ ]]; then
    echo "Error: Time must be in HH:MM format"
    exit 1
fi

# Parse time
IFS=':' read -r HOUR MINUTE <<< "$TIME_STR"

# Create a temporary file for the new crontab
TEMP_CRON=$(mktemp)

# Get the current crontab
crontab -l 2>/dev/null > "$TEMP_CRON"

# Check for existing wallpaper rotation entries
if grep -q "set_wallpaper.py.*--rotate" "$TEMP_CRON"; then
    echo "Found existing wallpaper rotation task. Removing it..."
    # Remove the existing entries
    sed -i '/# Wallpaper rotation task/d' "$TEMP_CRON"
    sed -i '/set_wallpaper.py.*--rotate/d' "$TEMP_CRON"
    # Remove any empty lines that might have been created
    sed -i '/^$/d' "$TEMP_CRON"
fi

# Add the new cron job (runs at specified time every X days)
echo "# Wallpaper rotation task" >> "$TEMP_CRON"
echo "$MINUTE $HOUR */$DAYS_INTERVAL * * python3 \"$WALLPAPER_SCRIPT\" --rotate \"$WALLPAPERS_DIR\" --min-days $DAYS_INTERVAL >> \"$WALLPAPERS_DIR/wallpaper_rotation.log\" 2>&1" >> "$TEMP_CRON"

# Install the new crontab
if ! crontab "$TEMP_CRON"; then
    echo "Error: Failed to install new crontab"
    rm "$TEMP_CRON"
    exit 1
fi

# Clean up
rm "$TEMP_CRON"

# Show success message only in interactive mode
if [ $# -ne 3 ]; then
    echo -e "\nCron job created successfully!"
    echo "Task: Rotate wallpaper every $DAYS_INTERVAL days at $TIME_STR"
    echo "Wallpapers Directory: $WALLPAPERS_DIR"
    echo "Log File: $WALLPAPERS_DIR/wallpaper_rotation.log"
    echo -e "\nNote: The task will run every $DAYS_INTERVAL days at $TIME_STR, and the script will only change the wallpaper"
    echo "if it hasn't been changed in the last $DAYS_INTERVAL days (to avoid repeating wallpapers too soon)."
    echo -e "\nTo view the rotation logs:"
    echo "cat $WALLPAPERS_DIR/wallpaper_rotation.log"
    echo -e "\nTo modify the schedule:"
    echo "1. Run: crontab -e"
    echo "2. Edit the line starting with '$MINUTE $HOUR'"
    echo "3. Save and exit"
fi 