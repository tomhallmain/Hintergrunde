# Wallpaper Manager

A simple desktop application that helps you manage and rotate your desktop wallpapers. It allows you to:

- Select a directory of images to use as wallpapers
- Manually rotate wallpapers with a click
- Schedule automatic wallpaper rotation
- Keep track of wallpaper history
- Works on both Windows and Unix (inc. MacOS) systems

The application uses PySide6 for the GUI and supports common image formats. On Windows, it uses the Task Scheduler, and on Unix systems, it uses cron jobs for scheduling.

## Requirements

- Python 3.6+
- PySide6
- Windows or Unix-based operating system

## Installation

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python wallpaper_gui.py
   ``` 