#!/usr/bin/env python3
import os
from PySide6.QtWidgets import QLabel, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from .core import set_wallpaper

class DropPreviewLabel(QLabel):
    """Custom QLabel that accepts drag and drop of files and directories."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.parent = parent
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        urls = event.mimeData().urls()
        if not urls:
            return
        
        # Get the first dropped item
        path = urls[0].toLocalFile()
        
        if os.path.isdir(path):
            # If it's a directory, set it as the wallpaper directory
            self.parent.set_directory(path)
        elif os.path.isfile(path):
            # If it's a file, check if it's an image
            if path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                # Set it as the current wallpaper
                try:
                    set_wallpaper(path)
                    self.parent.update_preview(path)
                except Exception as e:
                    QMessageBox.critical(self.parent, "Error", str(e))
            else:
                QMessageBox.warning(self.parent, "Invalid File", 
                                  "Please drop an image file (.png, .jpg, .jpeg, .bmp)") 