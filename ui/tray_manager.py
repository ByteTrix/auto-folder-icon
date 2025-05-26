"""
System tray management for running the application in the background.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import pystray
from PIL import Image, ImageDraw
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QIcon, QPixmap, QAction

from config.settings import AppSettings


logger = logging.getLogger(__name__)


class TrayManager(QObject):
    """Manages system tray functionality."""
      # Signals
    show_main_window = Signal()
    start_scan = Signal()
    quit_application = Signal()
    
    def __init__(self, main_window, settings: AppSettings):
        super().__init__()
        self.main_window = main_window
        self.settings = settings
        self.tray_icon = None
        self.tray_menu = None
        
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available")
        
        self._create_tray_icon()
        self._connect_signals()
    
    def _create_tray_icon(self):
        """Create the system tray icon."""
        try:
            # Create tray icon
            self.tray_icon = QSystemTrayIcon(self)
            
            # Set icon
            icon_path = self._get_tray_icon_path()
            if icon_path and icon_path.exists():
                icon = QIcon(str(icon_path))
            else:
                # Create a default icon if none exists
                icon = self._create_default_icon()
            
            self.tray_icon.setIcon(icon)
            self.tray_icon.setToolTip("Media Folder Icon Manager")
            
            # Create context menu
            self._create_context_menu()
            
            # Connect tray icon signals
            self.tray_icon.activated.connect(self._on_tray_activated)
            
        except Exception as e:
            logger.error(f"Failed to create tray icon: {e}")
    
    def _get_tray_icon_path(self) -> Optional[Path]:
        """Get the path to the tray icon."""
        project_root = Path(__file__).parent.parent
        icons_dir = project_root / "assets" / "icons"
        
        # Look for icon files
        for name in ["tray_icon.png", "app_icon.png", "icon.png"]:
            icon_path = icons_dir / name
            if icon_path.exists():
                return icon_path
        
        return None
    
    def _create_default_icon(self) -> QIcon:
        """Create a default tray icon."""
        try:
            # Create a simple icon using PIL
            size = 64
            image = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # Draw a simple folder icon
            # Background
            draw.rectangle([8, 16, size-8, size-8], fill=(255, 206, 84), outline=(200, 150, 50))
            # Tab
            draw.rectangle([8, 12, 24, 16], fill=(255, 206, 84), outline=(200, 150, 50))
            # F letter
            draw.text((size//2-8, size//2-8), "F", fill=(100, 100, 100))
            
            # Convert PIL image to QIcon
            import io
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            
            return QIcon(pixmap)
            
        except Exception as e:
            logger.error(f"Failed to create default icon: {e}")
            # Return a basic QIcon if all else fails
            return QIcon()
    
    def _create_context_menu(self):
        """Create the tray context menu."""
        self.tray_menu = QMenu()
        
        # Show/Hide main window
        self.show_action = QAction("Show Window", self)
        self.show_action.triggered.connect(self._show_main_window)
        self.tray_menu.addAction(self.show_action)
        
        self.tray_menu.addSeparator()
        
        # Manual scan
        scan_action = QAction("Start Scan", self)
        scan_action.triggered.connect(self._start_manual_scan)
        self.tray_menu.addAction(scan_action)
        
        # Settings
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._show_settings)
        self.tray_menu.addAction(settings_action)
        
        self.tray_menu.addSeparator()
        
        # About
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        self.tray_menu.addAction(about_action)
        
        # Quit
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_application)
        self.tray_menu.addAction(quit_action)
        
        # Set menu
        self.tray_icon.setContextMenu(self.tray_menu)
    
    def _connect_signals(self):
        """Connect internal signals."""
        self.show_main_window.connect(self.main_window.show)
        self.show_main_window.connect(self.main_window.raise_)
        self.show_main_window.connect(self.main_window.activateWindow)
        
        self.quit_application.connect(self._on_quit_application)
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_main_window()
        elif reason == QSystemTrayIcon.Trigger:
            # Single click - could show a status tooltip
            self._show_status_message()
    
    def _show_main_window(self):
        """Show the main window."""
        self.show_main_window.emit()
        
        # Update menu text
        if self.main_window.isVisible():
            self.show_action.setText("Hide Window")
        else:
            self.show_action.setText("Show Window")
    
    def _start_manual_scan(self):
        """Start a manual scan."""
        self.start_scan.emit()
        self.show_message("Scan Started", "Manual media scan started", 3000)
    
    def _show_settings(self):
        """Show settings dialog."""
        self._show_main_window()
        # The main window should handle showing settings
        if hasattr(self.main_window, 'show_settings'):
            self.main_window.show_settings()
    
    def _show_about(self):
        """Show about dialog."""
        from PySide6.QtWidgets import QMessageBox
        
        about_text = """
        <h3>Media Folder Icon Manager</h3>
        <p>Automatically sets folder icons for TV shows and anime,<br>
        and embeds poster thumbnails in movie files.</p>
        
        <p><b>Features:</b></p>
        <ul>
        <li>Automatic media directory scanning</li>
        <li>Custom folder icons for TV shows and anime</li>
        <li>Poster thumbnail embedding in movies</li>
        <li>Background operation with system tray</li>
        </ul>
        
        <p><b>APIs Used:</b></p>
        <ul>
        <li>TMDB (The Movie Database)</li>
        <li>AniList (for anime detection)</li>
        </ul>
        """
        
        QMessageBox.about(None, "About", about_text)
    
    def _quit_application(self):
        """Quit the application."""
        logger.info("Quit requested from tray")
        self.quit_application.emit()
    
    def _on_quit_application(self):
        """Handle quit application signal."""
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()
    
    def _show_status_message(self):
        """Show current status in a tooltip."""
        try:
            # Get scan status
            next_scan = "Not scheduled"
            if hasattr(self.main_window, 'scheduler'):
                next_scan_time = self.main_window.scheduler.get_next_scan_time()
                if next_scan_time:
                    next_scan = next_scan_time.strftime("%H:%M %d/%m")
            
            # Show status
            status_msg = f"Next scan: {next_scan}"
            self.tray_icon.setToolTip(f"Media Folder Icon Manager\n{status_msg}")
            
        except Exception as e:
            logger.debug(f"Failed to show status: {e}")
    
    def show_tray(self):
        """Show the tray icon."""
        if self.tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()
            logger.info("System tray icon shown")
            return True
        else:
            logger.warning("Cannot show tray icon - system tray not available")
            return False
    
    def hide_tray(self):
        """Hide the tray icon."""
        if self.tray_icon:
            self.tray_icon.hide()
            logger.info("System tray icon hidden")
    
    def show_message(self, title: str, message: str, timeout: int = 5000):
        """
        Show a tray notification message.
        
        Args:
            title: Message title
            message: Message content
            timeout: Timeout in milliseconds
        """
        if self.tray_icon and self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, timeout)
        else:
            logger.info(f"Tray message: {title} - {message}")
    
    def update_icon_state(self, scanning: bool = False):
        """
        Update tray icon to reflect current state.
        
        Args:
            scanning: Whether a scan is currently in progress
        """
        try:
            if scanning:
                self.tray_icon.setToolTip("Media Folder Icon Manager - Scanning...")
                # Could change icon to indicate scanning
            else:
                self.tray_icon.setToolTip("Media Folder Icon Manager")
                
        except Exception as e:
            logger.debug(f"Failed to update icon state: {e}")
    
    def is_tray_available(self) -> bool:
        """
        Check if system tray is available.
        
        Returns:
            True if system tray is available, False otherwise
        """
        return QSystemTrayIcon.isSystemTrayAvailable()
    
    def cleanup(self):
        """Clean up tray resources."""
        if self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon = None
