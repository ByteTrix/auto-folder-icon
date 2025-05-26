#!/usr/bin/env python3
"""
Media Folder Icon Manager
A Python application for setting folder icons and embedding movie thumbnails.
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from config.settings import AppSettings
from ui.main_window import MainWindow
from ui.setup_dialog import SetupDialog
from ui.tray_manager import TrayManager
from utils.logger import setup_logging


def main():
    """Main application entry point."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Media Folder Icon Manager")
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray
    
    # Load or create settings
    settings = AppSettings.load()
    
    # Check if this is first run
    if not settings.is_configured():
        logger.info("First run detected, showing setup dialog")
        setup_dialog = SetupDialog()
        if setup_dialog.exec() != setup_dialog.Accepted:
            logger.info("Setup cancelled, exiting")
            return 0
        
        # Reload settings after setup
        settings = AppSettings.load()
    
    # Create main window
    main_window = MainWindow(settings)
    
    # Create tray manager
    tray_manager = TrayManager(main_window, settings)
    
    # Show main window or start in tray mode
    if settings.tray_mode:
        logger.info("Starting in tray mode")
        tray_manager.show_tray()
    else:
        logger.info("Starting with main window visible")
        main_window.show()
    
    # Start the application
    try:
        exit_code = app.exec()
        logger.info(f"Application exiting with code {exit_code}")
        return exit_code
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
