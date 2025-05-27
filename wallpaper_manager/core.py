#!/usr/bin/env python3
from datetime import datetime, timedelta
from enum import Enum, auto
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import time
from .utils import check_powershell_execution_policy, check_linux_dependencies
from .logger import setup_logger

# Set up logger for this module
logger = setup_logger('wallpaper_manager.core')

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
                    cache = json.load(f)
                # Validate cache structure
                required_keys = {
                    'last_wallpaper', 'last_lock_screen',
                    'last_wallpaper_change', 'last_lock_screen_change',
                    'wallpaper_history', 'lock_screen_history'
                }
                if not all(key in cache for key in required_keys):
                    logger.warning(f"Cache file {self.cache_file} is missing required keys. Recreating cache.")
                    os.remove(self.cache_file)
                    return self._create_new_cache()
                return cache
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid cache file {self.cache_file}: {str(e)}. Recreating cache.")
                try:
                    os.remove(self.cache_file)
                except OSError:
                    pass  # Ignore if file can't be removed
                return self._create_new_cache()
        return self._create_new_cache()
    
    def _create_new_cache(self):
        """Create a new cache structure."""
        logger.info("Creating new cache file")
        return {
            'last_wallpaper': None,
            'last_lock_screen': None,
            'last_wallpaper_change': None,
            'last_lock_screen_change': None,
            'wallpaper_history': [],
            'lock_screen_history': []
        }
    
    def _save_cache(self):
        """Save the current cache to file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to save cache file: {str(e)}")
            # Continue execution even if cache save fails
    
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
            entry['path'] for entry in self.cache['wallpaper_history']
            if current_time - entry['timestamp'] < (min_days_between_repeats * 24 * 3600)
        }
        
        eligible_images = [img for img in available_images if img not in recent_wallpapers]
        
        # If all images have been used recently, use any image
        if not eligible_images:
            eligible_images = available_images
        
        selected_image = random.choice(eligible_images)
        
        # Update cache
        self.cache['last_wallpaper'] = selected_image
        self.cache['last_wallpaper_change'] = current_time
        self.cache['wallpaper_history'].append({
            'path': selected_image,
            'timestamp': current_time
        })
        
        # Keep only last 100 entries in history
        self.cache['wallpaper_history'] = self.cache['wallpaper_history'][-100:]
        
        self._save_cache()
        return selected_image

    def select_next_lock_screen(self, min_days_between_repeats=7):
        """Select the next lock screen image using a random strategy with history tracking."""
        available_images = self.get_available_images()
        if not available_images:
            raise ValueError(f"No supported images found in {self.image_dir}")
        
        # Filter out recently used lock screen images
        current_time = time.time()
        recent_lock_screens = {
            entry['path'] for entry in self.cache['lock_screen_history']
            if current_time - entry['timestamp'] < (min_days_between_repeats * 24 * 3600)
        }
        
        eligible_images = [img for img in available_images if img not in recent_lock_screens]
        
        # If all images have been used recently, use any image
        if not eligible_images:
            eligible_images = available_images
        
        selected_image = random.choice(eligible_images)
        
        # Update cache
        self.cache['last_lock_screen'] = selected_image
        self.cache['last_lock_screen_change'] = current_time
        self.cache['lock_screen_history'].append({
            'path': selected_image,
            'timestamp': current_time
        })
        
        # Keep only last 100 entries in history
        self.cache['lock_screen_history'] = self.cache['lock_screen_history'][-100:]
        
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
    logger.info(f"Setting Windows wallpaper: {image_path} with scaling mode {scaling_mode}")
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
        logger.info("Successfully set Windows wallpaper")
    except subprocess.CalledProcessError as e:
        logger.error(f"PowerShell command failed: {str(e)}")
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
    logger.info(f"Setting wallpaper: {image_path}")
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Check file permissions
    if not os.access(image_path, os.R_OK):
        logger.error(f"Cannot read image file: {image_path}")
        raise PermissionError(f"Cannot read image file: {image_path}")
    
    # If no scaling mode specified, determine it based on image dimensions
    if scaling_mode is None:
        scaling_mode = get_scaling_mode(image_path)
        logger.info(f"Auto-determined scaling mode: {scaling_mode}")
    
    system = platform.system().lower()
    logger.info(f"Detected operating system: {system}")
    
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
            logger.error(f"Unsupported operating system: {system}")
            raise RuntimeError(f"Unsupported operating system: {system}")
        
        logger.info(f"Successfully set wallpaper to: {image_path}")
        print(f"Successfully set wallpaper to: {image_path}")
    except Exception as e:
        logger.error(f"Error setting wallpaper: {str(e)}")
        print(f"Error setting wallpaper: {str(e)}", file=sys.stderr)
        sys.exit(1)

def rotate_wallpaper(image_dir, min_days_between_repeats=7, force=False):
    """Rotate the wallpaper from the specified directory.
    
    Args:
        image_dir: Path to the directory containing wallpapers
        min_days_between_repeats: Minimum number of days between wallpaper changes
        force: If True, ignore the minimum days check and rotate anyway
    """
    logger.info(f"Rotating wallpaper from directory: {image_dir}")
    rotator = WallpaperRotator(image_dir)
    
    # Check if enough time has passed since the last rotation
    if not force and rotator.cache['last_wallpaper_change'] is not None:
        current_dt = datetime.now()
        last_change_dt = datetime.fromtimestamp(rotator.cache['last_wallpaper_change'])
        
        # Calculate next rotation time
        next_rotation_dt = last_change_dt + timedelta(days=min_days_between_repeats)
        next_rotation_dt = _adjust_rotation_time(next_rotation_dt)
        
        if current_dt < next_rotation_dt:
            logger.info(
                f"Skipping rotation: {min_days_between_repeats} days have not elapsed since last change. "
                f"Current time: {current_dt.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"Next rotation available: {next_rotation_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            print(
                f"Skipping rotation: {min_days_between_repeats} days have not elapsed since last change. "
                f"Next rotation available: {next_rotation_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            return
    
    # If we get here, either force is True, there's no history, or enough time has passed
    next_wallpaper = rotator.select_next_wallpaper(min_days_between_repeats)
    logger.info(f"Selected next wallpaper: {next_wallpaper}")
    set_wallpaper(next_wallpaper)

def set_windows_lock_screen(image_path):
    """Set lock screen image on Windows using PowerShell."""
    logger.info(f"Setting Windows lock screen: {image_path}")
    # Convert to absolute path
    abs_path = str(Path(image_path).resolve())
    
    # PowerShell command to set lock screen
    ps_command = f'''
    $LockScreenPath = "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\PersonalizationCSP"
    $LockScreenImagePath = "$LockScreenPath\\LockScreenImagePath"
    $LockScreenImageStatus = "$LockScreenPath\\LockScreenImageStatus"
    $LockScreenImageUrl = "$LockScreenPath\\LockScreenImageUrl"
    
    # Create the registry keys if they don't exist
    if (!(Test-Path $LockScreenPath)) {{
        New-Item -Path $LockScreenPath -Force | Out-Null
    }}
    
    # Set the lock screen image
    Set-ItemProperty -Path $LockScreenPath -Name "LockScreenImagePath" -Value "{abs_path}" -Type String -Force
    Set-ItemProperty -Path $LockScreenPath -Name "LockScreenImageStatus" -Value 1 -Type DWord -Force
    Set-ItemProperty -Path $LockScreenPath -Name "LockScreenImageUrl" -Value "" -Type String -Force
    '''
    
    try:
        subprocess.run(['powershell', '-Command', ps_command], check=True, capture_output=True)
        logger.info("Successfully set Windows lock screen")
    except subprocess.CalledProcessError as e:
        logger.error(f"PowerShell command failed: {str(e)}")
        raise

def set_lock_screen(image_path):
    """Set lock screen image based on the current operating system.
    
    Args:
        image_path: Path to the image file
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Check file permissions
    if not os.access(image_path, os.R_OK):
        raise PermissionError(f"Cannot read image file: {image_path}")
    
    system = platform.system().lower()
    
    try:
        if system == 'windows':
            set_windows_lock_screen(image_path)
        else:
            raise RuntimeError(f"Lock screen setting not supported on {system}")
        
        print(f"Successfully set lock screen to: {image_path}")
    except Exception as e:
        print(f"Error setting lock screen: {str(e)}", file=sys.stderr)
        sys.exit(1)

def rotate_lock_screen(image_dir, min_days_between_repeats=7, force=False):
    """Rotate the lock screen image from the specified directory.
    
    Args:
        image_dir: Path to the directory containing images
        min_days_between_repeats: Minimum number of days between image changes
        force: If True, ignore the minimum days check and rotate anyway
    """
    logger.info(f"Rotating lock screen from directory: {image_dir}")
    rotator = WallpaperRotator(image_dir)
    
    # Check if enough time has passed since the last rotation
    if not force and rotator.cache['last_lock_screen_change'] is not None:
        current_dt = datetime.now()
        last_change_dt = datetime.fromtimestamp(rotator.cache['last_lock_screen_change'])
        
        # Calculate next rotation time
        next_rotation_dt = last_change_dt + timedelta(days=min_days_between_repeats)
        next_rotation_dt = _adjust_rotation_time(next_rotation_dt)

        if current_dt < next_rotation_dt:
            logger.info(
                f"Skipping lock screen rotation: {min_days_between_repeats} days have not elapsed since last change. "
                f"Current time: {current_dt.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"Next rotation available: {next_rotation_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            print(
                f"Skipping lock screen rotation: {min_days_between_repeats} days have not elapsed since last change. "
                f"Next rotation available: {next_rotation_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            return
    
    # If we get here, either force is True, there's no history, or enough time has passed
    next_image = rotator.select_next_lock_screen(min_days_between_repeats)
    logger.info(f"Selected next lock screen image: {next_image}")
    set_lock_screen(next_image)


def _adjust_rotation_time(next_rotation_dt):
    """Adjust the next rotation time to start of day, normalize based on hour."""
    if next_rotation_dt.hour < 18:
        # If before 6 PM, set to start of current day
        next_rotation_dt = next_rotation_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # If after 6 PM, set to start of next day
        next_rotation_dt = (next_rotation_dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return next_rotation_dt


