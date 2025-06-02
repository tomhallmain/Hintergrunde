#!/usr/bin/env python3
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys


def get_default_media_folder():
    """Get the default media folder for the current OS.
    
    Returns:
        Path: Path to the default media folder for the current OS.
        Common locations:
        - Windows: %USERPROFILE%\Pictures
        - macOS: ~/Pictures
        - Linux: ~/Pictures
    """
    system = sys.platform.lower()
    
    if system.startswith('win'):
        # Windows: Use Pictures folder
        return Path(os.path.expandvars('%USERPROFILE%')) / 'Pictures'
    elif system.startswith('darwin'):
        # macOS: Use Pictures folder
        return Path.home() / 'Pictures'
    else:
        # Linux and others: Use Pictures folder
        return Path.home() / 'Pictures'

def check_powershell_execution_policy():
    """Check if PowerShell execution policy might block the script."""
    try:
        result = subprocess.run(['powershell', '-Command', 'Get-ExecutionPolicy'], 
                              capture_output=True, text=True, check=True)
        policy = result.stdout.strip().lower()
        if policy in ['restricted', 'allrestricted']:
            print("Warning: PowerShell execution policy is restricted. The script might not work.",
                  "Consider running: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser",
                  file=sys.stderr)
    except Exception:
        pass  # Ignore any errors in the check

def check_linux_dependencies():
    """Check if required Linux tools are installed."""
    missing_tools = []
    
    # Check for gsettings
    try:
        subprocess.run(['which', 'gsettings'], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        missing_tools.append('gsettings')
    
    # Check for feh
    try:
        subprocess.run(['which', 'feh'], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        missing_tools.append('feh')
    
    if missing_tools:
        print("Warning: The following tools are not installed:", ', '.join(missing_tools),
              "\nYou may need to install them for the script to work on your Linux system.",
              file=sys.stderr) 

def format_relative_time(target_date: datetime) -> str:
    """Format a datetime into a human-readable relative time string.
    
    Args:
        target_date: The target datetime to format
        
    Returns:
        A human-readable string like "today", "tomorrow", "3 days from now", etc.
    """
    now = datetime.now()
    delta = target_date - now.replace(hour=0, minute=0, second=0, microsecond=0)
    days = delta.days
    
    if days == 0:
        return "today"
    elif days == 1:
        return "tomorrow"
    elif days < 7:
        return f"{days} days from now"
    elif days < 14:
        return "next week"
    elif days < 21:
        return "2 weeks from now"
    elif days < 28:
        return "3 weeks from now"
    elif days < 60:
        return "next month"
    elif days < 365:
        months = days // 30
        return f"{months} months from now"
    else:
        years = days // 365
        return f"{years} year{'s' if years > 1 else ''} from now"
