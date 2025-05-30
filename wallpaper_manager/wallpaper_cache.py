import json
import os
import time

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .logger import setup_logger
from .constants import WallpaperType, ChangeSource, ScalingMode

logger = setup_logger('wallpaper_manager.cache')


@dataclass
class WallpaperChange:
    """Represents a single wallpaper change event."""
    path: str
    timestamp: float
    type: WallpaperType
    source: ChangeSource = ChangeSource.UNKNOWN
    scaling_mode: ScalingMode = ScalingMode.AUTO
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], _type: WallpaperType) -> 'WallpaperChange':
        """Create a WallpaperChange from a dictionary.
        
        Args:
            data: Dictionary containing path, timestamp, source, and scaling_mode
        """
        return cls(
            path=data['path'],
            timestamp=data['timestamp'],
            type=_type,
            source=ChangeSource[data.get('source', 'UNKNOWN')],
            scaling_mode=ScalingMode[data.get('scaling_mode', 'AUTO')]
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage.
        
        Note: Type is not stored as it can be inferred from context.
        """
        return {
            'path': self.path,
            'timestamp': self.timestamp,
            'source': self.source.name,
            'scaling_mode': self.scaling_mode.name
        }
    
    def format_history_entry(self) -> str:
        """Format the change as a history entry string.
        
        Returns:
            A formatted string like "2024-03-14 15:30:00 - [Wallpaper] image.jpg (Manual)"
        """
        timestamp = datetime.fromtimestamp(self.timestamp)
        type_str = "Wallpaper" if self.type == WallpaperType.WALLPAPER else "Lock Screen"
        source_str = f"{self.source.name.title()}, " if self.source != ChangeSource.UNKNOWN else ""
        scaling_str = "Scaling: " + self.scaling_mode.name.lower()
        return f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - [{type_str}] {Path(self.path).name} ({source_str}{scaling_str})"

class WallpaperCache:
    """Class to handle wallpaper rotation cache with type safety and default values."""
    
    def __init__(self, cache_file: str):
        """Initialize the cache.
        
        Args:
            cache_file: Path to the cache file
        """
        self.cache_file = cache_file
        self._cache: Dict[str, Any] = self._load_cache()
        self._rebuild_state()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load the cache file if it exists, otherwise create a new one."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                # Validate and normalize cache structure
                return self._normalize_cache(cache)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid cache file {self.cache_file}: {str(e)}. Recreating cache.")
                try:
                    os.remove(self.cache_file)
                except OSError:
                    pass  # Ignore if file can't be removed
                return self._create_new_cache()
        return self._create_new_cache()
    
    def _create_new_cache(self) -> Dict[str, Any]:
        """Create a new cache structure with default values."""
        logger.info("Creating new cache file")
        return {
            'wallpaper_history': [],
            'lock_screen_history': []
        }
    
    def _normalize_cache(self, cache: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required keys exist in the cache with proper types."""
        default_cache = self._create_new_cache()
        
        # Ensure all keys exist with proper types
        for key, default_value in default_cache.items():
            if key not in cache:
                cache[key] = default_value
            elif not isinstance(cache[key], type(default_value)):
                # If type doesn't match, use default
                cache[key] = default_value
        
        return cache
    
    def _rebuild_state(self) -> None:
        """Rebuild derived state from history."""
        # Convert history entries to WallpaperChange objects
        self._wallpaper_history = [
            WallpaperChange.from_dict(entry, WallpaperType.WALLPAPER) 
            for entry in self._cache['wallpaper_history']
        ]
        self._lock_screen_history = [
            WallpaperChange.from_dict(entry, WallpaperType.LOCK_SCREEN) 
            for entry in self._cache['lock_screen_history']
        ]
    
    def save(self) -> None:
        """Save the current cache to file."""
        try:
            # Convert WallpaperChange objects back to dictionaries
            cache_data = {
                'wallpaper_history': [change.to_dict() for change in self._wallpaper_history],
                'lock_screen_history': [change.to_dict() for change in self._lock_screen_history]
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to save cache file: {str(e)}")
    
    def has_wallpaper_history(self) -> bool:
        """Check if there is any wallpaper history."""
        return bool(self._wallpaper_history)

    def has_lock_screen_history(self) -> bool:
        """Check if there is any lock screen history."""
        return bool(self._lock_screen_history)

    @property
    def last_wallpaper(self) -> WallpaperChange:
        """Get the most recent wallpaper change.
        
        Returns:
            The most recent wallpaper change, or a default WallpaperChange if no history exists.
        """
        if not self._wallpaper_history:
            return WallpaperChange(
                path="",
                timestamp=0.0,
                type=WallpaperType.WALLPAPER,
                source=ChangeSource.UNKNOWN,
                scaling_mode=ScalingMode.AUTO
            )
        return max(self._wallpaper_history, key=lambda x: x.timestamp)
    
    @property
    def last_lock_screen(self) -> WallpaperChange:
        """Get the most recent lock screen change.
        
        Returns:
            The most recent lock screen change, or a default WallpaperChange if no history exists.
        """
        if not self._lock_screen_history:
            return WallpaperChange(
                path="",
                timestamp=0.0,
                type=WallpaperType.LOCK_SCREEN,
                source=ChangeSource.UNKNOWN,
                scaling_mode=ScalingMode.AUTO
            )
        return max(self._lock_screen_history, key=lambda x: x.timestamp)
    
    @property
    def last_wallpaper_change(self) -> float:
        """Get the timestamp of the most recent wallpaper change."""
        return self.last_wallpaper.timestamp
    
    @property
    def last_lock_screen_change(self) -> float:
        """Get the timestamp of the most recent lock screen change."""
        return self.last_lock_screen.timestamp
    
    @property
    def last_wallpaper_path(self) -> str:
        """Get the path of the most recent wallpaper change."""
        return self.last_wallpaper.path
    
    @property
    def last_lock_screen_path(self) -> str:
        """Get the path of the most recent lock screen change."""
        return self.last_lock_screen.path
    
    @property
    def wallpaper_history(self) -> List[WallpaperChange]:
        """Get the wallpaper history."""
        return self._wallpaper_history
    
    def add_wallpaper_to_history(self, path: str, source: ChangeSource, scaling_mode: ScalingMode = ScalingMode.AUTO):
        """Add a wallpaper change to history."""
        change = WallpaperChange(
            path=path,
            timestamp=time.time(),
            type=WallpaperType.WALLPAPER,
            source=source,
            scaling_mode=scaling_mode
        )
        self._wallpaper_history.append(change)
        # Keep only last 100 entries
        self._wallpaper_history = self._wallpaper_history[-100:]
        self.save()
    
    @property
    def lock_screen_history(self) -> List[WallpaperChange]:
        """Get the lock screen history."""
        return self._lock_screen_history
    
    def add_lock_screen_to_history(self, path: str, source: ChangeSource, scaling_mode: ScalingMode = ScalingMode.AUTO):
        """Add a lock screen change to history."""
        change = WallpaperChange(
            path=path,
            timestamp=time.time(),
            type=WallpaperType.LOCK_SCREEN,
            source=source,
            scaling_mode=scaling_mode
        )
        self._lock_screen_history.append(change)
        # Keep only last 100 entries
        self._lock_screen_history = self._lock_screen_history[-100:]
        self.save()
    
    def get_combined_history(self) -> List[WallpaperChange]:
        """Get combined history of both wallpaper and lock screen changes, sorted by timestamp.
        
        Returns:
            List of history entries sorted by timestamp in descending order (most recent first).
        """
        all_history = []
        all_history.extend(self.wallpaper_history)
        all_history.extend(self.lock_screen_history)
        return sorted(all_history, key=lambda x: x.timestamp, reverse=True) 