#!/usr/bin/env python3
import json
import os
from pathlib import Path
from .logger import setup_logger
from .utils import get_default_media_folder

logger = setup_logger(__name__)

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Config:
    """Configuration manager for the wallpaper manager."""
    
    def __init__(self):
        self.config_file = Path(os.path.join(project_root, '.wallpaper_manager_config.json'))
        self.default_config = {
            'last_directory': str(get_default_media_folder()),
            'min_days': 7,
            'rotation_time': '09:00',
            'scheduling_enabled': False,
            'scheduled_time': None,
            'scheduled_days': None,
            'scaling_mode': 'auto',
            'use_logon_trigger': False,
            'recurse_subdirs': False
        }
        self.config = self.load_config()
        
        # If last_directory is None after loading, set it to the default media folder
        if not self.config.get('last_directory'):
            self.config['last_directory'] = str(get_default_media_folder())
            self.save_config()
    
    def load_config(self):
        """Load configuration from file."""
        config = self.default_config.copy()
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    config.update(saved_config)
            except Exception as e:
                logger.warning(f"Could not load config file: {e}")
        
        return config
    
    def save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save config file: {e}")
    
    def get(self, key, default=None):
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value and save to file."""
        self.config[key] = value
        self.save_config()
    
    def update(self, **kwargs):
        """Update multiple configuration values and save to file."""
        self.config.update(kwargs)
        self.save_config() 