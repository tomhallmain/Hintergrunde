#!/usr/bin/env python3
import sys
import os
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QSpinBox, QListWidget, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage

# Import the wallpaper functionality
from set_wallpaper import WallpaperRotator, set_wallpaper

class WallpaperGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wallpaper Manager")
        self.setMinimumSize(800, 600)
        
        # Initialize the main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Directory selection
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("No directory selected")
        dir_button = QPushButton("Select Image Directory")
        dir_button.clicked.connect(self.select_directory)
        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(dir_button)
        layout.addLayout(dir_layout)
        
        # Preview area
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setStyleSheet("border: 1px solid #ccc;")
        layout.addWidget(self.preview_label)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Min days between repeats
        min_days_layout = QHBoxLayout()
        min_days_layout.addWidget(QLabel("Min days between repeats:"))
        self.min_days_spin = QSpinBox()
        self.min_days_spin.setRange(1, 365)
        self.min_days_spin.setValue(7)
        min_days_layout.addWidget(self.min_days_spin)
        controls_layout.addLayout(min_days_layout)
        
        # Action buttons
        rotate_button = QPushButton("Rotate Wallpaper")
        rotate_button.clicked.connect(self.rotate_wallpaper)
        controls_layout.addWidget(rotate_button)
        
        layout.addLayout(controls_layout)
        
        # History list
        layout.addWidget(QLabel("Wallpaper History:"))
        self.history_list = QListWidget()
        layout.addWidget(self.history_list)
        
        self.rotator = None
        self.current_directory = None
    
    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Image Directory")
        if directory:
            self.current_directory = directory
            self.dir_label.setText(directory)
            self.rotator = WallpaperRotator(directory)
            self.update_history()
    
    def update_history(self):
        if not self.rotator:
            return
        
        self.history_list.clear()
        for entry in reversed(self.rotator.cache['history']):
            timestamp = datetime.fromtimestamp(entry['timestamp'])
            self.history_list.addItem(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {Path(entry['path']).name}")
    
    def rotate_wallpaper(self):
        if not self.rotator:
            QMessageBox.warning(self, "Error", "Please select an image directory first")
            return
        
        try:
            next_wallpaper = self.rotator.select_next_wallpaper(self.min_days_spin.value())
            set_wallpaper(next_wallpaper)
            self.update_preview(next_wallpaper)
            self.update_history()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def update_preview(self, image_path):
        if not os.path.exists(image_path):
            return
        
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(self.preview_label.size(), 
                                    Qt.KeepAspectRatio, 
                                    Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled_pixmap)

def main():
    app = QApplication(sys.argv)
    window = WallpaperGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 