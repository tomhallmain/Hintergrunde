#!/usr/bin/env python3
from datetime import datetime
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import time

from .constants import ChangeSource, ScalingMode, WallpaperType
from .logger import setup_logger
from .utils import check_powershell_execution_policy, check_linux_dependencies
from .wallpaper_cache import WallpaperCache

# Set up logger for this module
logger = setup_logger('wallpaper_manager.core')


class WallpaperRotator:
    def __init__(self, image_dir, cache_file=None):
        self.image_dir = Path(image_dir)
        self.cache_file = cache_file or str(self.image_dir / '.wallpaper_cache.json')
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp'}
        self.cache = WallpaperCache(self.cache_file)
    
    def get_available_images(self):
        """Get all supported images in the directory."""
        images = []
        for ext in self.supported_formats:
            images.extend(self.image_dir.glob(f'*{ext}'))
            images.extend(self.image_dir.glob(f'*{ext.upper()}'))
        return [str(img) for img in images if img.is_file()]
    
    def select_next_wallpaper(self, min_days_between_repeats=7, source=ChangeSource.MANUAL):
        """Select the next wallpaper using a random strategy with history tracking.
        
        Args:
            min_days_between_repeats: Minimum number of days between wallpaper changes
            source: Source of the wallpaper change (manual or automated)
        """
        available_images = self.get_available_images()
        if not available_images:
            raise ValueError(f"No supported images found in {self.image_dir}")
        
        # Filter out recently used wallpapers
        current_time = time.time()
        recent_wallpapers = {
            entry.path for entry in self.cache.wallpaper_history
            if current_time - entry.timestamp < (min_days_between_repeats * 24 * 3600)
        }
        
        eligible_images = [img for img in available_images if img not in recent_wallpapers]
        
        # If all images have been used recently, use any image
        if not eligible_images:
            eligible_images = available_images
        
        selected_image = random.choice(eligible_images)
        
        # Determine the appropriate scaling mode for this image
        scaling_mode = get_scaling_mode(selected_image)
        
        # Update cache with the determined scaling mode
        self.cache.add_wallpaper_to_history(selected_image, source=source, scaling_mode=scaling_mode)
        
        return selected_image

    def select_next_lock_screen(self, min_days_between_repeats=7, source=ChangeSource.MANUAL):
        """Select the next lock screen image using a random strategy with history tracking.
        
        Args:
            min_days_between_repeats: Minimum number of days between image changes
            source: Source of the lock screen change (manual or automated)
        """
        available_images = self.get_available_images()
        if not available_images:
            raise ValueError(f"No supported images found in {self.image_dir}")
        
        # Filter out recently used lock screen images
        current_time = time.time()
        recent_lock_screens = {
            entry.path for entry in self.cache.lock_screen_history
            if current_time - entry.timestamp < (min_days_between_repeats * 24 * 3600)
        }
        
        eligible_images = [img for img in available_images if img not in recent_lock_screens]
        
        # If all images have been used recently, use any image
        if not eligible_images:
            eligible_images = available_images
        
        selected_image = random.choice(eligible_images)
        
        # Determine the appropriate scaling mode for this image
        scaling_mode = get_scaling_mode(selected_image)
        
        # Update cache with the determined scaling mode
        self.cache.add_lock_screen_to_history(selected_image, source=source, scaling_mode=scaling_mode)
        
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
            else:
                return ScalingMode.FILL
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

def set_wallpaper(image_path, scaling_mode=ScalingMode.AUTO):
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
    if scaling_mode is None or scaling_mode == ScalingMode.AUTO:
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
    except Exception as e:
        logger.error(f"Error setting wallpaper: {str(e)}")
        sys.exit(1)

def rotate_wallpaper(image_dir, min_days_between_repeats=7, force=False, source=ChangeSource.MANUAL):
    """Rotate the wallpaper from the specified directory.
    
    Args:
        image_dir: Path to the directory containing wallpapers
        min_days_between_repeats: Minimum number of days between wallpaper changes
        force: If True, ignore the minimum days check and rotate anyway
        source: Source of the wallpaper change (manual or automated)
    """
    logger.info(f"Rotating wallpaper from directory: {image_dir}")
    rotator = WallpaperRotator(image_dir)
    
    # Check if enough time has passed since the last rotation
    if not force and rotator.cache.has_wallpaper_history():
        current_dt = datetime.now()
        next_rotation_dt = rotator.cache.get_next_rotation_time(min_days_between_repeats, WallpaperType.WALLPAPER)
        
        if next_rotation_dt and current_dt < next_rotation_dt:
            logger.info(
                f"Skipping rotation: {min_days_between_repeats} days have not elapsed since last change. "
                f"Current time: {current_dt.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"Next rotation available: {next_rotation_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            return
    
    # If we get here, either force is True, there's no history, or enough time has passed
    next_wallpaper = rotator.select_next_wallpaper(min_days_between_repeats, source=source)
    logger.info(f"Selected next wallpaper: {next_wallpaper}")
    
    # Get the scaling mode that was determined and saved for this wallpaper
    scaling_mode = rotator.cache.last_wallpaper.scaling_mode
    logger.info(f"Using scaling mode: {scaling_mode}")
    set_wallpaper(next_wallpaper, scaling_mode)

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

def set_lock_screen(image_path, scaling_mode=ScalingMode.AUTO):
    """Set lock screen image based on the current operating system.
    
    Args:
        image_path: Path to the image file
        scaling_mode: How to scale the image (currently not usable)
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
        
        logger.info(f"Successfully set lock screen to: {image_path}")
    except Exception as e:
        print(f"Error setting lock screen: {str(e)}", file=sys.stderr)
        sys.exit(1)

def rotate_lock_screen(image_dir, min_days_between_repeats=7, force=False, source=ChangeSource.MANUAL):
    """Rotate the lock screen image from the specified directory.
    
    Args:
        image_dir: Path to the directory containing images
        min_days_between_repeats: Minimum number of days between image changes
        force: If True, ignore the minimum days check and rotate anyway
        source: Source of the lock screen change (manual or automated)
    """
    logger.info(f"Rotating lock screen from directory: {image_dir}")
    rotator = WallpaperRotator(image_dir)
    
    # Check if enough time has passed since the last rotation
    if not force and rotator.cache.has_lock_screen_history():
        current_dt = datetime.now()
        next_rotation_dt = rotator.cache.get_next_rotation_time(min_days_between_repeats, WallpaperType.LOCK_SCREEN)
        
        if next_rotation_dt and current_dt < next_rotation_dt:
            logger.info(
                f"Skipping lock screen rotation: {min_days_between_repeats} days have not elapsed since last change. "
                f"Current time: {current_dt.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"Next rotation available: {next_rotation_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            return
    
    # If we get here, either force is True, there's no history, or enough time has passed
    next_image = rotator.select_next_lock_screen(min_days_between_repeats, source=source)
    logger.info(f"Selected next lock screen image: {next_image}")
    
    # Get the scaling mode that was determined and saved for this lock screen image
    scaling_mode = rotator.cache.last_lock_screen.scaling_mode
    logger.info(f"Using scaling mode: {scaling_mode}")
    set_lock_screen(next_image, scaling_mode)


