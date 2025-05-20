#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import random
import json
import time
from pathlib import Path
from enum import Enum, auto
from .utils import check_powershell_execution_policy, check_linux_dependencies

class ScalingMode(Enum):
    """Enum for wallpaper scaling modes."""
    FILL = auto()    # Fill the screen, may crop
    FIT = auto()     # Fit the screen, may have letterboxing
    STRETCH = auto() # Stretch to fill, may distort

    def get_macos_option(self) -> str:
        """Get the corresponding macOS scaling option."""
        return {
            ScalingMode.FILL: 'fill',
            ScalingMode.FIT: 'fit',
            ScalingMode.STRETCH: 'stretch'
        }[self]

    def get_gnome_option(self) -> str:
        """Get the corresponding GNOME scaling option."""
        return {
            ScalingMode.FILL: 'zoom',
            ScalingMode.FIT: 'scaled',
            ScalingMode.STRETCH: 'stretched'
        }[self]

    def get_feh_option(self) -> str:
        """Get the corresponding feh scaling option."""
        return '--bg-scale' if self == ScalingMode.FIT else '--bg-fill'

    def get_windows_style(self) -> int:
        """Get the corresponding Windows wallpaper style.
        
        Windows styles:
        0 = Center
        1 = Stretch
        2 = Tile
        3 = Fit
        4 = Fill
        5 = Span
        """
        return {
            ScalingMode.FILL: 4,    # Fill
            ScalingMode.FIT: 3,     # Fit
            ScalingMode.STRETCH: 1  # Stretch
        }[self]

    @classmethod
    def from_string(cls, mode_str: str) -> 'ScalingMode':
        """Convert string to ScalingMode enum value."""
        mode_map = {
            'fill': cls.FILL,
            'fit': cls.FIT,
            'stretch': cls.STRETCH,
            'auto': None  # None means let the function determine the mode
        }
        mode_str = mode_str.lower()
        if mode_str not in mode_map:
            raise ValueError(f"Invalid scaling mode: {mode_str}. Must be one of: {', '.join(mode_map.keys())}")
        return mode_map[mode_str]

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

def get_scaling_mode(image_path):
    """Determine the appropriate scaling mode based on image aspect ratio.
    Returns FILL if PIL is not available or if the image is landscape."""
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            width, height = img.size
            # If image is portrait (height > width), use FIT to avoid stretching
            if width < height:
                return ScalingMode.FIT
    except (ImportError, Exception):
        pass
    return ScalingMode.FILL

def set_windows_wallpaper(image_path, scaling_mode=ScalingMode.FILL):
    """Set wallpaper on Windows using PowerShell."""
    # Convert to absolute path
    abs_path = str(Path(image_path).resolve())
    
    # Get Windows style from scaling mode
    style = scaling_mode.get_windows_style()
    
    # PowerShell command to set wallpaper and style
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
    $SPI_SETDESKWALLPAPERSTYLE = 0x001B
    $UpdateIniFile = 0x01
    $SendChangeEvent = 0x02
    $fWinIni = $UpdateIniFile -bor $SendChangeEvent
    [Wallpaper]::SystemParametersInfo($SPI_SETDESKWALLPAPER, 0, "{abs_path}", $fWinIni) | Out-Null
    [Wallpaper]::SystemParametersInfo($SPI_SETDESKWALLPAPERSTYLE, 0, $null, $fWinIni) | Out-Null
    Set-ItemProperty -Path 'HKCU:\\Control Panel\\Desktop' -Name WallpaperStyle -Value {style}
    Set-ItemProperty -Path 'HKCU:\\Control Panel\\Desktop' -Name TileWallpaper -Value 0
    '''
    
    try:
        subprocess.run(['powershell', '-Command', ps_command], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: PowerShell command failed: {str(e)}", file=sys.stderr)
        raise

def set_macos_wallpaper(image_path, scaling_mode=ScalingMode.FILL):
    """Set wallpaper on macOS using osascript."""
    abs_path = str(Path(image_path).resolve())
    
    script = f'''
    tell application "Finder"
        set desktop picture to POSIX file "{abs_path}"
        set desktop picture options to {{scaling: {scaling_mode.get_macos_option()}}}
    end tell
    '''
    try:
        subprocess.run(['osascript', '-e', script], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: AppleScript command failed: {str(e)}", file=sys.stderr)
        raise

def set_linux_wallpaper(image_path, scaling_mode=ScalingMode.FILL):
    """Set wallpaper on Linux using gsettings (GNOME) or feh (other DEs)."""
    abs_path = str(Path(image_path).resolve())
    
    # Try GNOME first
    try:
        subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-options', 
                       scaling_mode.get_gnome_option()], check=True)
        subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', 
                       f'file://{abs_path}'], check=True)
        return
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Warning: gsettings failed: {str(e)}", file=sys.stderr)
    
    # Try feh
    try:
        subprocess.run(['feh', scaling_mode.get_feh_option(), abs_path], check=True)
        return
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Warning: feh failed: {str(e)}", file=sys.stderr)
    
    raise RuntimeError("Could not set wallpaper. Neither gsettings nor feh is available.")

def set_wallpaper(image_path, scaling_mode=None):
    """Set wallpaper based on the current operating system.
    
    Args:
        image_path: Path to the image file
        scaling_mode: Optional ScalingMode enum value. If None, the mode will be
                     determined automatically based on the image aspect ratio.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Check file permissions
    if not os.access(image_path, os.R_OK):
        raise PermissionError(f"Cannot read image file: {image_path}")
    
    # If no scaling mode specified, determine it based on image dimensions
    if scaling_mode is None:
        scaling_mode = get_scaling_mode(image_path)
    
    system = platform.system().lower()
    
    # Run OS-specific checks
    if system == 'windows':
        check_powershell_execution_policy()
    elif system == 'linux':
        check_linux_dependencies()
    
    try:
        if system == 'windows':
            set_windows_wallpaper(image_path, scaling_mode)
        elif system == 'darwin':
            set_macos_wallpaper(image_path, scaling_mode)
        elif system == 'linux':
            set_linux_wallpaper(image_path, scaling_mode)
        else:
            raise RuntimeError(f"Unsupported operating system: {system}")
        
        print(f"Successfully set wallpaper to: {image_path}")
    except Exception as e:
        print(f"Error setting wallpaper: {str(e)}", file=sys.stderr)
        sys.exit(1)

def rotate_wallpaper(image_dir, min_days_between_repeats=7, force=False):
    """Rotate the wallpaper from the specified directory.
    
    Args:
        image_dir: Path to the directory containing wallpapers
        min_days_between_repeats: Minimum number of days between wallpaper changes
        force: If True, ignore the minimum days check and rotate anyway
    """
    rotator = WallpaperRotator(image_dir)
    
    # Check if enough time has passed since the last rotation
    if not force and rotator.cache['last_change'] is not None:
        current_time = time.time()
        time_since_last = current_time - rotator.cache['last_change']
        min_seconds = min_days_between_repeats * 24 * 3600
        
        if time_since_last < min_seconds:
            print(f"Skipping rotation: {min_days_between_repeats} days have not elapsed since last change")
            return
    
    # If we get here, either force is True, there's no history, or enough time has passed
    next_wallpaper = rotator.select_next_wallpaper(min_days_between_repeats)
    set_wallpaper(next_wallpaper) 