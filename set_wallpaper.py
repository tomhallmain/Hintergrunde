#!/usr/bin/env python3
import sys
import argparse
from wallpaper_manager import set_wallpaper, rotate_wallpaper

def print_help():
    """Print detailed help information."""
    print("Wallpaper Manager - A cross-platform wallpaper management tool")
    print("\nUsage:")
    print("  Set specific wallpaper:")
    print("    python set_wallpaper.py <path_to_image>")
    print("\n  Rotate wallpaper:")
    print("    python set_wallpaper.py --rotate <path_to_image_directory> [--min-days DAYS]")
    print("\nOptions:")
    print("  --rotate           Enable wallpaper rotation mode")
    print("  --min-days DAYS    Minimum days between wallpaper repeats (default: 7)")
    print("  -h, --help        Show this help message")
    print("\nExamples:")
    print("  Set a specific wallpaper:")
    print("    python set_wallpaper.py C:/Pictures/wallpaper.jpg")
    print("\n  Rotate wallpapers every 3 days:")
    print("    python set_wallpaper.py --rotate C:/Pictures/Wallpapers --min-days 3")

def main():
    # Check for help flag first
    if len(sys.argv) == 1 or sys.argv[1] in ['-h', '--help']:
        print_help()
        sys.exit(0)

    # Create argument parser
    parser = argparse.ArgumentParser(description="Wallpaper Manager - A cross-platform wallpaper management tool")
    parser.add_argument('--rotate', action='store_true', help='Enable wallpaper rotation mode')
    parser.add_argument('--min-days', type=int, default=7, help='Minimum days between wallpaper repeats (default: 7)')
    parser.add_argument('path', nargs='?', help='Path to image file or directory (for rotation mode)')

    try:
        args = parser.parse_args()
    except SystemExit:
        # If argparse encounters an error, it will call sys.exit()
        # We want to show our custom help instead
        print_help()
        sys.exit(1)

    if args.rotate:
        if not args.path:
            print("Error: Please specify an image directory for rotation")
            print_help()
            sys.exit(1)
        rotate_wallpaper(args.path, args.min_days)
    else:
        if not args.path:
            print("Error: Please specify an image file")
            print_help()
            sys.exit(1)
        set_wallpaper(args.path)

if __name__ == '__main__':
    main() 