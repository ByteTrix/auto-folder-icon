"""
Logging configuration and utilities.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime


def setup_logging(log_level: str = "INFO") -> None:
    """
    Setup application logging with both file and console handlers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create logs directory
    project_root = Path(__file__).parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Setup log format
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = logs_dir / "media_folder_icon.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
      # Log startup message
    logging.getLogger(__name__).info("Logging initialized")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: The name for the logger
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class GuiLogHandler(logging.Handler):
    """Custom log handler that can emit logs to a GUI widget."""
    
    def __init__(self, text_widget=None):
        super().__init__()
        self.text_widget = text_widget
        self.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        ))
    
    def emit(self, record):
        """Emit a log record to the GUI widget."""
        if self.text_widget is not None:
            try:
                msg = self.format(record)
                # This should be called from the main thread
                self.text_widget.append(msg)
            except Exception:
                pass  # Ignore errors when updating GUI
    
    def set_widget(self, widget):
        """Set the target widget for log messages."""
        self.text_widget = widget


# Global GUI log handler instance
gui_log_handler = GuiLogHandler()


def add_gui_logging(text_widget) -> None:
    """
    Add GUI logging to display logs in a text widget.
    
    Args:
        text_widget: Qt text widget to display logs
    """
    gui_log_handler.set_widget(text_widget)
    gui_log_handler.setLevel(logging.INFO)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(gui_log_handler)


def remove_gui_logging() -> None:
    """Remove GUI logging handler."""
    root_logger = logging.getLogger()
    if gui_log_handler in root_logger.handlers:
        root_logger.removeHandler(gui_log_handler)
