#!/usr/bin/env python3
import os
import platform
import subprocess
from pathlib import Path

class TaskScheduler:
    """Handles creation and management of scheduled wallpaper rotation tasks."""
    
    def __init__(self):
        self.system = platform.system().lower()
    
    def check_existing_task(self) -> bool:
        """Check if a wallpaper rotation task already exists.
        
        Returns:
            bool: True if a task exists, False otherwise
        """
        if self.system == 'windows':
            try:
                result = subprocess.run(['schtasks', '/query', '/tn', 'RotateWallpaper'], 
                                     capture_output=True, text=True)
                return result.returncode == 0
            except Exception:
                return False
        elif self.system in ['linux', 'darwin']:  # darwin is macOS
            try:
                result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
                return 'set_wallpaper.py.*--rotate' in result.stdout
            except Exception:
                return False
        return False
    
    def create_task(self, script_path: str, wallpapers_dir: str, days_interval: int, 
                   time_str: str) -> None:
        """Create a scheduled task for wallpaper rotation.
        
        Args:
            script_path: Path to the wallpaper script
            wallpapers_dir: Directory containing wallpapers
            days_interval: Days between rotations
            time_str: Time of day to rotate (HH:mm format)
            
        Raises:
            RuntimeError: If task creation fails
            NotImplementedError: If OS is not supported
        """
        if self.system == 'windows':
            self._create_windows_task(script_path, wallpapers_dir, days_interval, time_str)
        elif self.system in ['linux', 'darwin']:  # darwin is macOS
            self._create_unix_task(script_path, wallpapers_dir, days_interval, time_str)
        else:
            raise NotImplementedError(f"Task scheduling not supported on {self.system}")
    
    def remove_task(self) -> None:
        """Remove the scheduled wallpaper rotation task.
        
        Raises:
            RuntimeError: If task removal fails
            NotImplementedError: If OS is not supported
        """
        if self.system == 'windows':
            self._remove_windows_task()
        elif self.system in ['linux', 'darwin']:  # darwin is macOS
            self._remove_unix_task()
        else:
            raise NotImplementedError(f"Task scheduling not supported on {self.system}")
    
    def _create_windows_task(self, script_path: str, wallpapers_dir: str, 
                           days_interval: int, time_str: str) -> None:
        """Create a Windows scheduled task."""
        # Create the task action
        action = f'python "{script_path}" --rotate "{wallpapers_dir}" --min-days {days_interval}'
        
        # Create the task using schtasks
        cmd = [
            'schtasks', '/create', '/tn', 'RotateWallpaper',
            '/tr', action, '/sc', 'daily', '/st', time_str,
            '/f'  # Force creation (overwrite if exists)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create task: {result.stderr}")
    
    def _create_unix_task(self, script_path: str, wallpapers_dir: str, 
                         days_interval: int, time_str: str) -> None:
        """Create a Unix cron job (Linux or macOS)."""
        # Get current crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        current_crontab = result.stdout if result.returncode == 0 else ""
        
        # Remove any existing wallpaper rotation entries
        lines = current_crontab.splitlines()
        lines = [line for line in lines if 'set_wallpaper.py.*--rotate' not in line]
        
        # Add new cron job
        hour, minute = map(int, time_str.split(':'))
        # Use python3 for Linux, python for macOS (as macOS typically has python3 as python)
        python_cmd = 'python3' if self.system == 'linux' else 'python'
        cron_line = f"{minute} {hour} */{days_interval} * * {python_cmd} \"{script_path}\" --rotate \"{wallpapers_dir}\" --min-days {days_interval} >> \"{wallpapers_dir}/wallpaper_rotation.log\" 2>&1"
        lines.append(cron_line)
        
        # Install new crontab
        new_crontab = '\n'.join(lines) + '\n'
        result = subprocess.run(['crontab', '-'], input=new_crontab, text=True, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create cron job: {result.stderr}")
    
    def _remove_windows_task(self) -> None:
        """Remove the Windows scheduled task."""
        result = subprocess.run(['schtasks', '/delete', '/tn', 'RotateWallpaper', '/f'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to remove task: {result.stderr}")
    
    def _remove_unix_task(self) -> None:
        """Remove the Unix cron job (Linux or macOS)."""
        # Get current crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.splitlines()
            # Remove wallpaper rotation entries
            lines = [line for line in lines if 'set_wallpaper.py.*--rotate' not in line]
            # Install new crontab
            new_crontab = '\n'.join(lines) + '\n'
            result = subprocess.run(['crontab', '-'], input=new_crontab, text=True, capture_output=True)
            if result.returncode != 0:
                raise RuntimeError(f"Failed to remove cron job: {result.stderr}") 