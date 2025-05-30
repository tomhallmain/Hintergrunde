from enum import Enum, auto


class ScalingMode(Enum):
    """Enum for wallpaper scaling modes."""
    FILL = auto()    # Fill the screen, may crop
    FIT = auto()     # Fit the screen, may have letterboxing
    STRETCH = auto() # Stretch to fill, may distort
    AUTO = auto()    # Unknown scaling mode

    def get_macos_option(self) -> str:
        """Get the corresponding macOS scaling option."""
        return {
            ScalingMode.FILL: 'fill',
            ScalingMode.FIT: 'fit',
            ScalingMode.STRETCH: 'stretch',
            ScalingMode.AUTO: 'fill'
        }[self]

    def get_gnome_option(self) -> str:
        """Get the corresponding GNOME scaling option."""
        return {
            ScalingMode.FILL: 'zoom',
            ScalingMode.FIT: 'scaled',
            ScalingMode.STRETCH: 'stretched',
            ScalingMode.AUTO: 'zoom'
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
            ScalingMode.STRETCH: 1,  # Stretch
            ScalingMode.AUTO: 4     # Unknown, use fill
        }[self]

    @classmethod
    def from_string(cls, mode_str: str) -> 'ScalingMode':
        """Convert string to ScalingMode enum value."""
        mode_map = {
            'fill': cls.FILL,
            'fit': cls.FIT,
            'stretch': cls.STRETCH,
            'auto': cls.AUTO  # Auto means let the function determine the mode
        }
        mode_str = mode_str.lower()
        if mode_str not in mode_map:
            raise ValueError(f"Invalid scaling mode: {mode_str}. Must be one of: {', '.join(mode_map.keys())}")
        return mode_map[mode_str]

class WallpaperType(Enum):
    """Type of wallpaper change."""
    WALLPAPER = auto()
    LOCK_SCREEN = auto()

class ChangeSource(Enum):
    """Source of the wallpaper change."""
    MANUAL = auto()      # Changed via script or GUI
    AUTOMATED = auto()   # Changed via scheduled task
    UNKNOWN = auto()     # Legacy entries or unknown source