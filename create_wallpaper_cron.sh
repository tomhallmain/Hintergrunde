#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
WALLPAPER_SCRIPT="$SCRIPT_DIR/set_wallpaper.py"

# Check if the wallpaper script exists
if [ ! -f "$WALLPAPER_SCRIPT" ]; then
    echo "Error: set_wallpaper.py not found in $SCRIPT_DIR"
    exit 1
fi

# Make sure the wallpaper script is executable
chmod +x "$WALLPAPER_SCRIPT"

# Get the wallpapers directory
read -p "Enter the full path to your wallpapers directory: " WALLPAPERS_DIR

# Validate the directory exists
if [ ! -d "$WALLPAPERS_DIR" ]; then
    echo "Error: Directory $WALLPAPERS_DIR does not exist"
    exit 1
fi

# Get the rotation interval
read -p "Enter the number of days between rotations (default: 7): " DAYS_INTERVAL
if ! [[ "$DAYS_INTERVAL" =~ ^[0-9]+$ ]]; then
    DAYS_INTERVAL=7
    echo "Using default interval of 7 days"
fi

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

# Add the new cron job (runs at 9 AM every X days)
echo "# Wallpaper rotation task" >> "$TEMP_CRON"
echo "0 9 */$DAYS_INTERVAL * * python3 \"$WALLPAPER_SCRIPT\" --rotate \"$WALLPAPERS_DIR\" --min-days $DAYS_INTERVAL >> \"$WALLPAPERS_DIR/wallpaper_rotation.log\" 2>&1" >> "$TEMP_CRON"

# Install the new crontab
if ! crontab "$TEMP_CRON"; then
    echo "Error: Failed to install new crontab"
    rm "$TEMP_CRON"
    exit 1
fi

# Clean up
rm "$TEMP_CRON"

echo -e "\nCron job created successfully!"
echo "Task: Rotate wallpaper every $DAYS_INTERVAL days"
echo "Wallpapers Directory: $WALLPAPERS_DIR"
echo "Log File: $WALLPAPERS_DIR/wallpaper_rotation.log"
echo -e "\nNote: The task will run every $DAYS_INTERVAL days at 9 AM, and the script will only change the wallpaper"
echo "if it hasn't been changed in the last $DAYS_INTERVAL days (to avoid repeating wallpapers too soon)."
echo -e "\nTo view the rotation logs:"
echo "cat $WALLPAPERS_DIR/wallpaper_rotation.log"
echo -e "\nTo modify the schedule:"
echo "1. Run: crontab -e"
echo "2. Edit the line starting with '0 9'"
echo "3. Save and exit" 