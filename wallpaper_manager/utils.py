#!/usr/bin/env python3
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