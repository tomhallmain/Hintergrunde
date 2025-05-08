#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import random
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

class WallpaperRotator:
    def __init__(self, image_dir, cache_file=None):
        self.image_dir = Path(image_dir)
        self.cache_file = cache_file or str(self.image_dir / '.wallpaper_cache.json')
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp'}
        self.cache = self._load_cache()
    
    def _load_cache(self):
        """Load the cache file if it exists."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self._create_new_cache()
        return self._create_new_cache()
    
    def _create_new_cache(self):
        """Create a new cache structure."""
        return {
            'last_wallpaper': None,
            'last_change': None,
            'history': []
        }
    
    def _save_cache(self):
        """Save the current cache to file."""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def get_available_images(self):
        """Get all supported images in the directory."""
        images = []
        for ext in self.supported_formats:
            images.extend(self.image_dir.glob(f'*{ext}'))
            images.extend(self.image_dir.glob(f'*{ext.upper()}'))
        return [str(img) for img in images if img.is_file()]
    
    def select_next_wallpaper(self, min_days_between_repeats=7):
        """Select the next wallpaper using a random strategy with history tracking."""
        available_images = self.get_available_images()
        if not available_images:
            raise ValueError(f"No supported images found in {self.image_dir}")
        
        # Filter out recently used wallpapers
        current_time = time.time()
        recent_wallpapers = {
            entry['path'] for entry in self.cache['history']
            if current_time - entry['timestamp'] < (min_days_between_repeats * 24 * 3600)
        }
        
        eligible_images = [img for img in available_images if img not in recent_wallpapers]
        
        # If all images have been used recently, use any image
        if not eligible_images:
            eligible_images = available_images
        
        selected_image = random.choice(eligible_images)
        
        # Update cache
        self.cache['last_wallpaper'] = selected_image
        self.cache['last_change'] = current_time
        self.cache['history'].append({
            'path': selected_image,
            'timestamp': current_time
        })
        
        # Keep only last 100 entries in history
        self.cache['history'] = self.cache['history'][-100:]
        
        self._save_cache()
        return selected_image

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

def set_windows_wallpaper(image_path):
    """Set wallpaper on Windows using PowerShell."""
    # Convert to absolute path
    abs_path = str(Path(image_path).resolve())
    
    # PowerShell command to set wallpaper
    ps_command = f'''
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class Wallpaper {{
        [DllImport("user32.dll", CharSet=CharSet.Auto)]
        public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
    }}
"@
    $SPI_SETDESKWALLPAPER = 0x0014
    $UpdateIniFile = 0x01
    $SendChangeEvent = 0x02
    $fWinIni = $UpdateIniFile -bor $SendChangeEvent
    [Wallpaper]::SystemParametersInfo($SPI_SETDESKWALLPAPER, 0, "{abs_path}", $fWinIni)
    '''
    
    try:
        subprocess.run(['powershell', '-Command', ps_command], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: PowerShell command failed: {str(e)}", file=sys.stderr)
        raise

def set_macos_wallpaper(image_path):
    """Set wallpaper on macOS using osascript."""
    abs_path = str(Path(image_path).resolve())
    script = f'''
    tell application "Finder"
        set desktop picture to POSIX file "{abs_path}"
    end tell
    '''
    try:
        subprocess.run(['osascript', '-e', script], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: AppleScript command failed: {str(e)}", file=sys.stderr)
        raise

def set_linux_wallpaper(image_path):
    """Set wallpaper on Linux using gsettings (GNOME) or feh (other DEs)."""
    abs_path = str(Path(image_path).resolve())
    
    # Try GNOME first
    try:
        subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', f'file://{abs_path}'], check=True)
        return
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Warning: gsettings failed: {str(e)}", file=sys.stderr)
    
    # Try feh
    try:
        subprocess.run(['feh', '--bg-fill', abs_path], check=True)
        return
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Warning: feh failed: {str(e)}", file=sys.stderr)
    
    raise RuntimeError("Could not set wallpaper. Neither gsettings nor feh is available.")

def set_wallpaper(image_path):
    """Set wallpaper based on the current operating system."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Check file permissions
    if not os.access(image_path, os.R_OK):
        raise PermissionError(f"Cannot read image file: {image_path}")
    
    system = platform.system().lower()
    
    # Run OS-specific checks
    if system == 'windows':
        check_powershell_execution_policy()
    elif system == 'linux':
        check_linux_dependencies()
    
    try:
        if system == 'windows':
            set_windows_wallpaper(image_path)
        elif system == 'darwin':
            set_macos_wallpaper(image_path)
        elif system == 'linux':
            set_linux_wallpaper(image_path)
        else:
            raise RuntimeError(f"Unsupported operating system: {system}")
        
        print(f"Successfully set wallpaper to: {image_path}")
    except Exception as e:
        print(f"Error setting wallpaper: {str(e)}", file=sys.stderr)
        sys.exit(1)

def rotate_wallpaper(image_dir, min_days_between_repeats=7):
    """Rotate the wallpaper using the WallpaperRotator."""
    rotator = WallpaperRotator(image_dir)
    next_wallpaper = rotator.select_next_wallpaper(min_days_between_repeats)
    set_wallpaper(next_wallpaper) 