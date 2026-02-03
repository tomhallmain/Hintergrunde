#!/usr/bin/env python3
import os
import platform
import re
import subprocess
from typing import Optional, Dict, Any

from .logger import setup_logger

logger = setup_logger(__name__)

class TaskScheduler:
    """Handles creation and management of scheduled wallpaper rotation tasks."""
    
    def __init__(self):
        self.system = platform.system().lower()
        # Get the path to the scripts directory
        self.script_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts')
        self.ps_script = os.path.join(self.script_dir, 'create_wallpaper_task.ps1')
        self.cron_script = os.path.join(self.script_dir, 'create_wallpaper_cron.sh')
        
        # Validate script existence
        if self.system == 'windows' and not os.path.exists(self.ps_script):
            raise RuntimeError("PowerShell script not found. Please ensure scripts/create_wallpaper_task.ps1 exists.")
        elif self.system in ['linux', 'darwin'] and not os.path.exists(self.cron_script):
            raise RuntimeError("Cron script not found. Please ensure scripts/create_wallpaper_cron.sh exists.")
    
    def get_task_info(self) -> Optional[Dict[str, Any]]:
        """Get detailed information about the existing wallpaper rotation task.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing task information if a task exists,
            None otherwise. The dictionary contains:
            - enabled: bool - Whether the task is enabled
            - time: str - Time of day for rotation (HH:mm format)
            - days: int - Days between rotations
            - directory: str - Wallpaper directory
            - scaling_mode: str - How the wallpaper is scaled
        """
        if self.system == 'windows':
            return self._get_windows_task_info()
        elif self.system in ['linux', 'darwin']:
            return self._get_unix_task_info()
        return None
    
    def _get_windows_task_info(self) -> Optional[Dict[str, Any]]:
        """Get Windows task information."""
        try:
            # First check if the task exists
            result = subprocess.run(['schtasks', '/query', '/tn', 'RotateWallpaper', '/fo', 'list'], 
                                  capture_output=True, text=True, encoding='cp1252', errors='replace')
            
            # If task doesn't exist, return None
            if result.returncode != 0:
                return None
            
            # Now get detailed information
            result = subprocess.run(['schtasks', '/query', '/tn', 'RotateWallpaper', '/fo', 'list', '/v'], 
                                  capture_output=True, text=True, encoding='cp1252', errors='replace')
            
            # Parse task information
            task_info = {}
            for line in result.stdout.splitlines():
                if 'Status:' in line:
                    task_info['enabled'] = 'Running' in line
                elif 'Task To Run:' in line:
                    # Extract command line arguments
                    cmd = line.split('Task To Run:')[1].strip()
                    # Parse arguments
                    if '--rotate' in cmd and '--min-days' in cmd:
                        # Extract directory
                        dir_match = re.search(r'--rotate\s+"([^"]+)"', cmd)
                        if dir_match:
                            task_info['directory'] = dir_match.group(1)
                        # Extract days
                        days_match = re.search(r'--min-days\s+(\d+)', cmd)
                        if days_match:
                            task_info['days'] = int(days_match.group(1))
                        # Extract scaling mode
                        scaling_match = re.search(r'--scaling-mode\s+(\w+)', cmd)
                        if scaling_match:
                            task_info['scaling_mode'] = scaling_match.group(1)
                elif 'Start Time:' in line:
                    time_str = line.split('Start Time:')[1].strip()
                    task_info['time'] = time_str
            
            return task_info if task_info else None
        except Exception:
            return None
    
    def _get_unix_task_info(self) -> Optional[Dict[str, Any]]:
        """Get Unix cron job information."""
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode != 0:
                return None
            
            for line in result.stdout.splitlines():
                if 'set_wallpaper.py.*--rotate' in line:
                    # Parse cron line
                    parts = line.split()
                    if len(parts) >= 6:
                        task_info = {
                            'enabled': True,
                            'time': f"{parts[1]}:{parts[0]}",  # hour:minute
                            'days': int(parts[2].replace('*/', '')),
                            'directory': None,
                            'scaling_mode': 'auto'  # Default if not found
                        }
                        # Extract directory from command
                        dir_match = re.search(r'--rotate\s+"([^"]+)"', line)
                        if dir_match:
                            task_info['directory'] = dir_match.group(1)
                        # Extract scaling mode
                        scaling_match = re.search(r'--scaling-mode\s+(\w+)', line)
                        if scaling_match:
                            task_info['scaling_mode'] = scaling_match.group(1)
                        return task_info
            return None
        except Exception:
            return None
    
    def check_existing_task(self) -> bool:
        """Check if a wallpaper rotation task already exists.
        
        Returns:
            bool: True if a task exists, False otherwise
        """
        return self.get_task_info() is not None
    
    def create_task(self, script_path: str, wallpapers_dir: str, days_interval: int, 
                   time_str: str, scaling_mode: str = 'auto', use_logon_trigger: bool = False,
                   recurse_subdirs: bool = False) -> None:
        """Create a scheduled task for wallpaper rotation.
        
        Args:
            script_path: Path to the wallpaper script
            wallpapers_dir: Directory containing wallpapers
            days_interval: Days between rotations
            time_str: Time of day to rotate (HH:mm format)
            scaling_mode: How to scale the wallpaper (fill, fit, stretch, or auto)
            use_logon_trigger: Whether to use the logon trigger
            recurse_subdirs: Whether to include images from subdirectories
        Raises:
            RuntimeError: If task creation fails
            NotImplementedError: If OS is not supported
        """
        if self.system == 'windows':
            self._create_windows_task(wallpapers_dir, days_interval, time_str, scaling_mode, use_logon_trigger, recurse_subdirs)
        elif self.system in ['linux', 'darwin']:  # darwin is macOS
            self._create_unix_task(wallpapers_dir, days_interval, time_str, scaling_mode, recurse_subdirs)
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
    
    def _create_windows_task(self, wallpapers_dir: str, days_interval: int, time_str: str, scaling_mode: str, use_logon_trigger: bool, recurse_subdirs: bool = False) -> None:
        """Create a Windows scheduled task using PowerShell script."""
        # Run the PowerShell script with the parameters
        cmd = [
            'powershell.exe',
            '-NoProfile',
            '-ExecutionPolicy', 'Bypass',
            '-File', self.ps_script,
            '-WallpapersDir', str(wallpapers_dir),
            '-DaysInterval', str(days_interval),
            '-Time', time_str,
            '-ScalingMode', scaling_mode,
        ]

        if use_logon_trigger:
            cmd.append('-UseLogonTrigger')
            cmd.append('1')
        if recurse_subdirs:
            cmd.append('-RecurseSubdirs')
            cmd.append('1')

        logger.info(f"Creating scheduled task with parameters: dir={wallpapers_dir}, interval={days_interval} days, time={time_str}, scaling={scaling_mode}, use_logon_trigger={use_logon_trigger}, recurse_subdirs={recurse_subdirs}")
        
        # Run the command and show output in real-time
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='cp1252',
            errors='replace'
        )
        
        # Print output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output and "Debug:" in output:  # Only show debug lines
                logger.debug(f"PowerShell: {output.strip()}")
        
        # Get any remaining output and the return code
        stdout, stderr = process.communicate()
        if stderr:
            logger.error(f"PowerShell error: {stderr.strip()}")
        
        if process.returncode != 0:
            raise RuntimeError(f"Failed to create task. Return code: {process.returncode}\nError: {stderr}")
    
    def _create_unix_task(self, wallpapers_dir: str, days_interval: int, time_str: str, scaling_mode: str, recurse_subdirs: bool = False) -> None:
        """Create a Unix cron job using shell script."""
        # Make the script executable
        os.chmod(self.cron_script, 0o755)
        
        # Run the shell script with the parameters (5th param: 1 = recurse, 0 = don't)
        cmd = [
            self.cron_script,
            wallpapers_dir,
            str(days_interval),
            time_str,
            scaling_mode,
            '1' if recurse_subdirs else '0'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create cron job: {result.stderr}")
    
    def _remove_windows_task(self) -> None:
        """Remove the Windows scheduled task."""
        # First try without admin privileges (succeeds for user-created tasks)
        result = subprocess.run(['schtasks', '/delete', '/tn', 'RotateWallpaper', '/f'],
                              capture_output=True, text=True, encoding='cp1252', errors='replace')

        # If access denied, run elevated once: one UAC prompt, one elevated process (no temp script)
        if result.returncode != 0 and "Access is denied" in result.stderr:
            elevate_cmd = (
                r"& { $p = Start-Process powershell -Verb RunAs "
                r"-ArgumentList '-NoProfile','-WindowStyle','Hidden','-Command','schtasks /delete /tn RotateWallpaper /f' "
                r"-Wait -PassThru; exit $p.ExitCode }"
            )
            result = subprocess.run(
                ['powershell.exe', '-WindowStyle', 'Hidden', '-NoProfile', '-Command', elevate_cmd],
                capture_output=True, text=True, encoding='cp1252', errors='replace', timeout=60
            )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to remove task: {result.stderr}")
    
    def _remove_unix_task(self) -> None:
        """Remove the Unix cron job."""
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