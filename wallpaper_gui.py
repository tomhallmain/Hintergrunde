#!/usr/bin/env python3
import os
import sys

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QSpinBox, QListWidget, QMessageBox, QGroupBox,
                             QTimeEdit, QCheckBox, QComboBox)
from PySide6.QtCore import Qt, QTime
from PySide6.QtGui import QPixmap, QImage

from wallpaper_manager import set_wallpaper, WallpaperRotator, TaskScheduler, Config
from wallpaper_manager.constants import ChangeSource, ScalingMode, WallpaperType
from wallpaper_manager.logger import setup_logger
from wallpaper_manager.ui import DropPreviewLabel
from wallpaper_manager.utils import format_relative_time


# Set up logger for this module
logger = setup_logger('wallpaper_manager.gui')

class WallpaperGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info("Initializing WallpaperGUI")
        self.setWindowTitle("Wallpaper Manager")
        self.setMinimumSize(800, 720)
        
        # Initialize configuration
        self.config = Config()
        
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
        preview_group = QGroupBox("Wallpaper Preview")
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(10, 10, 10, 10)  # Add padding
        
        self.preview_label = DropPreviewLabel(self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(400, 280)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                background-color: #f5f5f5;
                border-radius: 5px;
                padding: 10px;
            }
            QLabel:hover {
                border: 2px dashed #999;
                background-color: #f0f0f0;
            }
        """)
        self.preview_label.setText("Drop wallpaper image or directory here\nor click 'Select Image Directory' above")
        self.preview_label.setWordWrap(True)
        
        preview_layout.addWidget(self.preview_label)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Scaling mode selection
        scaling_layout = QHBoxLayout()
        scaling_layout.addWidget(QLabel("Scaling Mode:"))
        self.scaling_combo = QComboBox()
        self.scaling_combo.addItems(['fill', 'fit', 'stretch', 'auto'])
        self.scaling_combo.setCurrentText('auto')  # Default to AUTO
        scaling_layout.addWidget(self.scaling_combo)
        controls_layout.addLayout(scaling_layout)
        
        # Action buttons
        rotate_button = QPushButton("Rotate Wallpaper")
        rotate_button.clicked.connect(self.rotate_wallpaper)
        controls_layout.addWidget(rotate_button)
        
        layout.addLayout(controls_layout)
        
        # History list
        layout.addWidget(QLabel("Wallpaper History:"))
        self.history_list = QListWidget()
        layout.addWidget(self.history_list)
        
        # Task Scheduling Section
        task_group = QGroupBox("Task Scheduling")
        task_layout = QVBoxLayout()
        
        # Task status
        self.task_status_label = QLabel("No scheduled task")
        self.task_status_label.setStyleSheet("color: #666;")
        task_layout.addWidget(self.task_status_label)
        
        # Enable/Disable scheduling
        self.schedule_checkbox = QCheckBox("Enable automatic rotation")
        self.schedule_checkbox.stateChanged.connect(self.toggle_scheduling)
        task_layout.addWidget(self.schedule_checkbox)
        
        # Min days between repeats
        min_days_layout = QHBoxLayout()
        min_days_layout.addWidget(QLabel("Min days between repeats:"))
        self.min_days_spin = QSpinBox()
        self.min_days_spin.setRange(1, 365)
        self.min_days_spin.setValue(self.config.get('min_days', 7))
        self.min_days_spin.setEnabled(False)  # Initially disabled
        min_days_layout.addWidget(self.min_days_spin)
        task_layout.addLayout(min_days_layout)
        
        # Time selection
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Rotation time:"))
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime.fromString(self.config.get('rotation_time', '09:00'), "HH:mm"))
        self.time_edit.setEnabled(False)
        time_layout.addWidget(self.time_edit)
        task_layout.addLayout(time_layout)
        
        # Task management buttons
        task_buttons_layout = QHBoxLayout()
        self.create_task_button = QPushButton("Create Task")
        self.create_task_button.clicked.connect(self.create_scheduled_task)
        self.create_task_button.setEnabled(False)
        self.remove_task_button = QPushButton("Remove Task")
        self.remove_task_button.clicked.connect(self.remove_scheduled_task)
        self.remove_task_button.setEnabled(False)
        task_buttons_layout.addWidget(self.create_task_button)
        task_buttons_layout.addWidget(self.remove_task_button)
        task_layout.addLayout(task_buttons_layout)
        
        task_group.setLayout(task_layout)
        layout.addWidget(task_group)
        
        self.rotator = None
        self.current_directory = None
        self.task_scheduler = TaskScheduler()
        
        # Load last directory if it exists
        last_dir = self.config.get('last_directory')
        if last_dir and os.path.exists(last_dir):
            logger.info(f"Loading last directory: {last_dir}")
            self.current_directory = last_dir
            self.dir_label.setText(self.current_directory)
            self.rotator = WallpaperRotator(self.current_directory)
            self.update_history()
        
        # Check for existing task and update UI
        self.update_task_status()
        logger.info("WallpaperGUI initialization complete")
    
    def update_task_status(self):
        """Update the task status display and UI state."""
        logger.debug("Updating task status")
        task_info = self.task_scheduler.get_task_info()
        
        if task_info:
            # Task exists
            self.schedule_checkbox.setChecked(True)
            self.min_days_spin.setEnabled(True)
            self.remove_task_button.setEnabled(True)
            self.create_task_button.setEnabled(False)
            
            # Update time and days if they exist
            if 'time' in task_info:
                self.time_edit.setTime(QTime.fromString(task_info['time'], "HH:mm"))
            if 'days' in task_info:
                self.min_days_spin.setValue(task_info['days'])
            
            # Calculate next rotation time from cache if rotator exists
            next_rotation = None
            if self.rotator:
                next_rotation = self.rotator.cache.get_next_rotation_time(
                    min_days_between_repeats=self.min_days_spin.value(),
                    wallpaper_type=WallpaperType.WALLPAPER
                )
            
            # Format the next rotation time display
            if next_rotation:
                next_rotation_str = next_rotation.strftime("%Y-%m-%d")
                relative_time = format_relative_time(next_rotation)
                next_rotation_display = f"{next_rotation_str} ({relative_time})"
            else:
                next_rotation_display = "Unknown"
            
            # Update status text
            status_text = f"Scheduled task active:\n"
            status_text += f"• Rotates every {task_info.get('days', '?')} days\n"
            status_text += f"• At {task_info.get('time', '?')}\n"
            status_text += f"• Next rotation: {next_rotation_display}"
            
            # Add platform-specific note
            if sys.platform.startswith('win'):
                status_text += f"\n• Note: If the computer is off at the scheduled time, the task will run when the computer is next started"
            else:
                status_text += f"\n• Note: The task will only run at the exact scheduled time. If the computer is off, the task will be skipped"
            
            self.task_status_label.setText(status_text)
            self.task_status_label.setStyleSheet("color: #2e7d32;")  # Green color
            
            # Save scheduling state
            self.config.update(
                scheduling_enabled=True,
                scheduled_time=task_info.get('time'),
                scheduled_days=task_info.get('days')
            )
            logger.info(f"Found existing task: {task_info}")
        else:
            # No task exists
            self.schedule_checkbox.setChecked(False)
            self.min_days_spin.setEnabled(False)
            self.remove_task_button.setEnabled(False)
            self.create_task_button.setEnabled(False)
            self.task_status_label.setText("No scheduled task")
            self.task_status_label.setStyleSheet("color: #666;")
            
            # Clear scheduling state
            self.config.update(
                scheduling_enabled=False,
                scheduled_time=None,
                scheduled_days=None
            )
            logger.info("No existing task found")
    
    def toggle_scheduling(self, state):
        """Enable/disable scheduling controls based on checkbox state."""
        enabled = bool(state)
        logger.info(f"Toggling scheduling: {enabled}")
        self.time_edit.setEnabled(enabled)
        self.min_days_spin.setEnabled(enabled)
        self.create_task_button.setEnabled(enabled)
        
        # If disabling scheduling, remove the task if it exists
        if not enabled:
            if self.task_scheduler.check_existing_task():
                try:
                    logger.info("Removing existing task")
                    self.task_scheduler.remove_task()
                except Exception as e:
                    logger.error(f"Failed to remove scheduled task: {str(e)}")
                    QMessageBox.critical(self, "Error", f"Failed to remove scheduled task: {str(e)}")
                    # Revert checkbox state if task removal failed
                    self.schedule_checkbox.setChecked(True)
                    return
            
            self.remove_task_button.setEnabled(False)
            self.task_status_label.setText("No scheduled task")
            self.task_status_label.setStyleSheet("color: #666;")
            
            # Clear scheduling state in config
            self.config.update(
                scheduling_enabled=False,
                scheduled_time=None,
                scheduled_days=None
            )
    
    def create_scheduled_task(self):
        """Create a scheduled task for wallpaper rotation."""
        if not self.current_directory:
            logger.warning("Attempted to create task without directory selected")
            QMessageBox.warning(self, "Error", "Please select an image directory first")
            return
        
        try:
            script_path = os.path.abspath(__file__)
            time_str = self.time_edit.time().toString("HH:mm")
            days = self.min_days_spin.value()
            scaling_mode = self.scaling_combo.currentText()
            
            logger.info(f"Creating scheduled task: time={time_str}, days={days}, scaling={scaling_mode}")
            
            # Save the current settings to config
            self.config.update(
                min_days=days,
                rotation_time=time_str,
                scheduling_enabled=True,
                scheduled_time=time_str,
                scheduled_days=days,
                scaling_mode=scaling_mode
            )
            
            self.task_scheduler.create_task(
                script_path=script_path,
                wallpapers_dir=self.current_directory,
                days_interval=days,
                time_str=time_str,
                scaling_mode=scaling_mode
            )
            
            # Verify task was created
            if not self.task_scheduler.check_existing_task():
                raise RuntimeError("Task creation appeared successful but task was not found")
            
            logger.info("Scheduled task created successfully")
            QMessageBox.information(self, "Success", "Scheduled task created successfully!")
            self.update_task_status()
        except Exception as e:
            logger.error(f"Failed to create scheduled task: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create scheduled task: {str(e)}")
            # Revert config changes if task creation failed
            self.config.update(
                scheduling_enabled=False,
                scheduled_time=None,
                scheduled_days=None,
                scaling_mode=None
            )
            self.update_task_status()
    
    def remove_scheduled_task(self):
        """Remove the scheduled task."""
        try:
            logger.info("Removing scheduled task")
            self.task_scheduler.remove_task()
            QMessageBox.information(self, "Success", "Scheduled task removed successfully!")
            self.schedule_checkbox.setChecked(False)
            self.update_task_status()
        except Exception as e:
            logger.error(f"Failed to remove scheduled task: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to remove scheduled task: {str(e)}")
    
    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Image Directory")
        if directory:
            logger.info(f"Selected directory: {directory}")
            self.current_directory = directory
            self.dir_label.setText(directory)
            self.rotator = WallpaperRotator(directory)
            self.update_history()
            
            # Save the selected directory to config
            self.config.set('last_directory', directory)
        else:
            logger.info("Directory selection cancelled")
    
    def update_history(self):
        if not self.rotator:
            logger.debug("Skipping history update - no directory selected")
            return
        
        try:
            self.history_list.clear()
            history = self.rotator.cache.get_combined_history()
            for change in history:
                self.history_list.addItem(change.format_history_entry())
            logger.debug(f"Updated history with {len(history)} entries")
        except Exception as e:
            logger.error(f"Failed to update history: {str(e)}")
    
    def rotate_wallpaper(self):
        if not self.rotator:
            logger.warning("Attempted to rotate wallpaper without directory selected")
            QMessageBox.warning(self, "Error", "Please select an image directory first")
            return
        
        try:
            logger.info("Rotating wallpaper")
            scaling_mode = ScalingMode.from_string(self.scaling_combo.currentText())
            next_wallpaper = self.rotator.select_next_wallpaper(self.min_days_spin.value(), source=ChangeSource.MANUAL)
            set_wallpaper(next_wallpaper, scaling_mode)
            self.update_preview(next_wallpaper)
            self.update_history()
        except Exception as e:
            logger.error(f"Failed to rotate wallpaper: {str(e)}")
            QMessageBox.critical(self, "Error", str(e))
    
    def update_preview(self, image_path):
        if not os.path.exists(image_path):
            logger.error(f"Preview image not found: {image_path}")
            self.preview_label.setText("Error: Image not found")
            return
        
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                logger.error(f"Could not load preview image: {image_path}")
                self.preview_label.setText("Error: Could not load image")
                return
                
            scaled_pixmap = pixmap.scaled(self.preview_label.size(), 
                                        Qt.KeepAspectRatio, 
                                        Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled_pixmap)
            logger.debug(f"Updated preview with image: {image_path}")
        except Exception as e:
            logger.error(f"Failed to update preview: {str(e)}")
            self.preview_label.setText("Error: Could not load image")

    def set_directory(self, directory):
        """Set the wallpaper directory and update the UI."""
        if directory:
            logger.info(f"Setting directory: {directory}")
            self.current_directory = directory
            self.dir_label.setText(directory)
            self.rotator = WallpaperRotator(directory)
            self.update_history()
            
            # Save the selected directory to config
            self.config.set('last_directory', directory)
        else:
            logger.info("Directory setting cancelled")

def main():
    app = QApplication(sys.argv)
    window = WallpaperGUI()
    window.show()
    logger.info("Starting GUI application")
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 