#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys

from wallpaper_manager import set_wallpaper, rotate_wallpaper, rotate_lock_screen, ScalingMode
from wallpaper_manager.logger import setup_logger
from wallpaper_manager.wallpaper_cache import ChangeSource

# Set up logger for this script
logger = setup_logger('wallpaper_manager.script')

def print_help():
    """Print detailed help information."""
    print("Wallpaper Manager - A cross-platform wallpaper management tool")
    print("\nUsage:")
    print("  Set specific wallpaper:")
    print("    python set_wallpaper.py <path_to_image> [--scaling-mode MODE]")
    print("\n  Rotate wallpaper:")
    print("    python set_wallpaper.py --rotate <path_to_image_directory> [--min-days DAYS] [--no-force]")
    print("\n  Rotate lock screen:")
    print("    python set_wallpaper.py --rotate-lock-screen <path_to_image_directory> [--min-days DAYS] [--no-force]")
    print("\n  Rotate both:")
    print("    python set_wallpaper.py --rotate-both <path_to_image_directory> [--min-days DAYS] [--no-force]")
    print("\nOptions:")
    print("  --rotate           Enable wallpaper rotation mode")
    print("  --rotate-lock-screen  Enable lock screen rotation mode")
    print("  --rotate-both      Enable both wallpaper and lock screen rotation")
    print("  --min-days DAYS    Minimum days between repeats (default: 7)")
    print("  --no-force         Respect minimum days between rotations (default: force rotation)")
    print("  --recurse-subdirs  Include images from subdirectories")
    print("  --scaling-mode MODE  How to scale the wallpaper (default: auto)")
    print("                      Available modes: fill, fit, stretch, auto")
    print("  -h, --help        Show this help message")
    print("\nExamples:")
    print("  Set a specific wallpaper:")
    print("    python set_wallpaper.py C:/Pictures/wallpaper.jpg")
    print("    python set_wallpaper.py C:/Pictures/wallpaper.jpg --scaling-mode fit")
    print("\n  Rotate wallpapers every 3 days:")
    print("    python set_wallpaper.py --rotate C:/Pictures/Wallpapers --min-days 3")
    print("\n  Rotate lock screen:")
    print("    python set_wallpaper.py --rotate-lock-screen C:/Pictures/Wallpapers")
    print("\n  Rotate both:")
    print("    python set_wallpaper.py --rotate-both C:/Pictures/Wallpapers")

def main():
    # Check for help flag first
    if len(sys.argv) == 1 or sys.argv[1] in ['-h', '--help']:
        print_help()
        sys.exit(0)

    logger.info(f"Starting wallpaper manager with arguments: {sys.argv[1:]}")

    # Create argument parser
    parser = argparse.ArgumentParser(description="Wallpaper Manager - A cross-platform wallpaper management tool")
    parser.add_argument('--rotate', action='store_true', help='Enable wallpaper rotation mode')
    parser.add_argument('--rotate-lock-screen', action='store_true', help='Enable lock screen rotation mode')
    parser.add_argument('--rotate-both', action='store_true', help='Enable both wallpaper and lock screen rotation')
    parser.add_argument('--min-days', type=int, default=7, help='Minimum days between repeats (default: 7)')
    parser.add_argument('--no-force', action='store_true', help='Respect minimum days between rotations (default: force rotation)')
    parser.add_argument('--recurse-subdirs', action='store_true', help='Include images from subdirectories')
    parser.add_argument('--scaling-mode', type=str, default='auto',
                      help='How to scale the wallpaper (fill, fit, stretch, or auto)')
    parser.add_argument('path', nargs='?', help='Path to image file or directory (for rotation mode)')

    try:
        args = parser.parse_args()
    except SystemExit:
        # If argparse encounters an error, it will call sys.exit()
        # We want to show our custom help instead
        logger.warning("Argument parsing failed, showing help")
        print_help()
        sys.exit(1)

    try:
        scaling_mode = ScalingMode.from_string(args.scaling_mode)
        logger.info(f"Using scaling mode: {scaling_mode}")
    except ValueError as e:
        logger.error(f"Invalid scaling mode: {str(e)}")
        print(f"Error: {str(e)}")
        print_help()
        sys.exit(1)

    if not args.path:
        logger.error("No image file or directory specified")
        print("Error: Please specify an image file or directory")
        print_help()
        sys.exit(1)

    # Check if path is a directory
    path = Path(args.path)
    is_directory = path.is_dir()
    
    # If it's a directory and no rotation flags are set, automatically enable rotation
    if is_directory and not (args.rotate or args.rotate_lock_screen or args.rotate_both):
        logger.info(f"Directory detected: {args.path}, automatically enabling rotation mode")
        args.rotate = True

    if args.rotate or args.rotate_lock_screen or args.rotate_both:
        if not is_directory:
            logger.error(f"Path is not a directory: {args.path}")
            print(f"Error: Path must be a directory for rotation mode: {args.path}")
            print_help()
            sys.exit(1)
        
        logger.info(f"Rotation mode: {'both' if args.rotate_both else 'lock screen' if args.rotate_lock_screen else 'wallpaper'}")
        logger.info(f"Minimum days between repeats: {args.min_days}")
        logger.info(f"Force rotation: {not args.no_force}")
        logger.info(f"Recurse subdirs: {args.recurse_subdirs}")
        force = not args.no_force
        source = ChangeSource.AUTOMATED if args.no_force else ChangeSource.MANUAL
        recurse = args.recurse_subdirs
        
        if args.rotate_both:
            logger.info("Rotating both wallpaper and lock screen")
            rotate_wallpaper(args.path, args.min_days, force=force, source=source, recurse_subdirs=recurse)
            rotate_lock_screen(args.path, args.min_days, force=force, source=source, recurse_subdirs=recurse)
        elif args.rotate_lock_screen:
            logger.info("Rotating lock screen only")
            rotate_lock_screen(args.path, args.min_days, force=force, source=source, recurse_subdirs=recurse)
        else:  # args.rotate
            logger.info("Rotating wallpaper only")
            rotate_wallpaper(args.path, args.min_days, force=force, source=source, recurse_subdirs=recurse)
    else:
        if is_directory:
            logger.error(f"Cannot set directory as wallpaper: {args.path}")
            print(f"Error: Cannot set directory as wallpaper. Use --rotate to rotate wallpapers from a directory.")
            print_help()
            sys.exit(1)
            
        logger.info(f"Setting specific wallpaper: {args.path}")
        set_wallpaper(args.path, scaling_mode)

if __name__ == '__main__':
    main() 