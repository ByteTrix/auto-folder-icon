"""
Initial setup dialog for first-time configuration.
"""

import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QCheckBox, QSpinBox,
    QTextEdit, QTabWidget, QWidget, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QIcon

from config.settings import AppSettings
from api.tmdb_client import TMDBClient
from core.scanner import MediaScanner


logger = logging.getLogger(__name__)


class ValidationWorker(QThread):
    """Worker thread for validating settings."""
    
    validation_complete = Signal(dict)
    
    def __init__(self, media_directory: str, tmdb_api_key: str, anilist_api_key: str = ""):
        super().__init__()
        self.media_directory = media_directory
        self.tmdb_api_key = tmdb_api_key
        self.anilist_api_key = anilist_api_key
    
    def run(self):
        """Run validation in background."""
        result = {
            'directory_valid': False,
            'tmdb_api_key_valid': False,
            'anilist_api_key_valid': False,
            'directory_stats': {},
            'error_message': ''
        }
        
        try:
            # Validate directory
            if self.media_directory:
                scanner = MediaScanner()
                validation = scanner.validate_directory(Path(self.media_directory))
                result['directory_valid'] = validation['valid']
                if validation['valid']:
                    result['directory_stats'] = validation.get('stats', {})
                else:
                    result['error_message'] = validation.get('error', 'Unknown error')
            
            # Validate TMDB API key
            if self.tmdb_api_key:
                tmdb_client = TMDBClient(self.tmdb_api_key)
                result['tmdb_api_key_valid'] = tmdb_client.test_api_key()
            else:
                result['tmdb_api_key_valid'] = True  # Optional
            
            # Validate AniList API key
            if self.anilist_api_key:
                from api.anilist_client import AniListClient
                anilist_client = AniListClient(self.anilist_api_key)
                result['anilist_api_key_valid'] = anilist_client.test_api_key()
            else:
                result['anilist_api_key_valid'] = True  # Optional
            
        except Exception as e:
            result['error_message'] = str(e)
            logger.error(f"Validation error: {e}")
        
        self.validation_complete.emit(result)


class SetupDialog(QDialog):
    """Initial setup dialog for configuring the application."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Media Folder Icon Manager - Setup")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        self.settings = AppSettings()
        self.validation_worker = None
        
        self._init_ui()
        self._connect_signals()
        
        # Load existing settings if any
        self._load_existing_settings()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Welcome to Media Folder Icon Manager")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Description
        description = QLabel(
            "This application automatically sets folder icons for TV shows and anime, "
            "and embeds poster thumbnails in movie files. Please configure the settings below."
        )
        description.setWordWrap(True)
        description.setStyleSheet("margin: 10px; color: #666;")
        layout.addWidget(description)
        
        # Tabs
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Basic settings tab
        self._create_basic_tab()
        
        # API settings tab
        self._create_api_tab()
        
        # Features tab
        self._create_features_tab()
        
        # Validation status
        self.validation_label = QLabel("Click 'Validate Settings' to check configuration")
        self.validation_label.setStyleSheet("margin: 10px; font-style: italic;")
        layout.addWidget(self.validation_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.validate_button = QPushButton("Validate Settings")
        self.validate_button.clicked.connect(self._validate_settings)
        button_layout.addWidget(self.validate_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self._save_and_accept)
        self.ok_button.setEnabled(False)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
    
    def _create_basic_tab(self):
        """Create the basic settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Media directory group
        dir_group = QGroupBox("Media Directory")
        dir_layout = QFormLayout(dir_group)
        
        self.directory_edit = QLineEdit()
        self.directory_edit.setPlaceholderText("Select your media directory...")
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_directory)
        
        dir_row = QHBoxLayout()
        dir_row.addWidget(self.directory_edit)
        dir_row.addWidget(browse_button)
        
        dir_layout.addRow("Media Directory:", dir_row)
        layout.addWidget(dir_group)
        
        # Scan settings group
        scan_group = QGroupBox("Scan Settings")
        scan_layout = QFormLayout(scan_group)
        
        self.frequency_spin = QSpinBox()
        self.frequency_spin.setRange(1, 168)  # 1 hour to 1 week
        self.frequency_spin.setValue(24)
        self.frequency_spin.setSuffix(" hours")
        
        self.tray_mode_check = QCheckBox("Start in system tray")
        self.tray_mode_check.setChecked(True)
        
        scan_layout.addRow("Scan Frequency:", self.frequency_spin)
        scan_layout.addRow("Tray Mode:", self.tray_mode_check)
        layout.addWidget(scan_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Basic")
    
    def _create_api_tab(self):
        """Create the API settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # TMDB API group
        tmdb_group = QGroupBox("TMDB API Configuration")
        tmdb_layout = QVBoxLayout(tmdb_group)
        
        info_text = QTextEdit()
        info_text.setMaximumHeight(100)
        info_text.setReadOnly(True)
        info_text.setHtml("""
        <p>To use this application optimally, you can configure API keys for enhanced features:</p>
        <ul>
        <li><strong>TMDB:</strong> Required for movie and TV show metadata</li>
        <li><strong>AniList:</strong> Optional for enhanced anime features (public API works without key)</li>
        </ul>
        """)
        tmdb_layout.addWidget(info_text)
        
        # TMDB API Key section
        tmdb_form = QFormLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Enter your TMDB API key...")
        
        show_key_check = QCheckBox("Show TMDB API key")
        show_key_check.toggled.connect(self._toggle_api_key_visibility)
        
        tmdb_form.addRow("TMDB API Key:", self.api_key_edit)
        tmdb_form.addRow("", show_key_check)
        
        # Add TMDB instructions
        tmdb_instructions = QTextEdit()
        tmdb_instructions.setMaximumHeight(80)
        tmdb_instructions.setReadOnly(True)
        tmdb_instructions.setHtml("""
        <small>Get your free TMDB API key from: 
        <a href="https://www.themoviedb.org/settings/api">https://www.themoviedb.org/settings/api</a></small>
        """)
        tmdb_form.addRow("", tmdb_instructions)
        
        tmdb_layout.addLayout(tmdb_form)
        
        # AniList API Key section
        anilist_group = QGroupBox("AniList Configuration (Optional)")
        anilist_layout = QVBoxLayout(anilist_group)
        
        anilist_form = QFormLayout()
        self.anilist_api_key_edit = QLineEdit()
        self.anilist_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.anilist_api_key_edit.setPlaceholderText("Enter your AniList API key (optional)...")
        
        show_anilist_key_check = QCheckBox("Show AniList API key")
        show_anilist_key_check.toggled.connect(self._toggle_anilist_api_key_visibility)
        
        anilist_form.addRow("AniList API Key:", self.anilist_api_key_edit)
        anilist_form.addRow("", show_anilist_key_check)
        
        # Add AniList instructions
        anilist_instructions = QTextEdit()
        anilist_instructions.setMaximumHeight(80)
        anilist_instructions.setReadOnly(True)
        anilist_instructions.setHtml("""
        <small>AniList API key is optional. The app works with public API, but authenticated requests provide more features. 
        Get your key from: <a href="https://anilist.co/settings/developer">https://anilist.co/settings/developer</a></small>
        """)
        anilist_form.addRow("", anilist_instructions)
        
        anilist_layout.addLayout(anilist_form)
        layout.addWidget(anilist_group)
        layout.addWidget(tmdb_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "API Keys")
    
    def _create_features_tab(self):
        """Create the features tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Features group
        features_group = QGroupBox("Features")
        features_layout = QVBoxLayout(features_group)
        
        self.tv_shows_check = QCheckBox("Set folder icons for TV Shows")
        self.tv_shows_check.setChecked(True)
        
        self.movies_check = QCheckBox("Embed thumbnails in Movie files")
        self.movies_check.setChecked(True)
        
        self.anime_check = QCheckBox("Set folder icons for Anime (requires internet)")
        self.anime_check.setChecked(True)
        
        features_layout.addWidget(self.tv_shows_check)
        features_layout.addWidget(self.movies_check)
        features_layout.addWidget(self.anime_check)
        
        layout.addWidget(features_group)
        
        # Requirements group
        req_group = QGroupBox("Requirements")
        req_layout = QVBoxLayout(req_group)
        
        req_text = QLabel("""
        <b>For movie thumbnail embedding:</b><br>
        • FFmpeg executable must be placed in the assets/ffmpeg/ folder<br>
        • Download from: <a href="https://ffmpeg.org/download.html">https://ffmpeg.org/download.html</a><br><br>
        
        <b>Supported video formats:</b><br>
        • MP4, MKV, AVI, MOV, WMV, and others<br><br>
        
        <b>Note:</b> Icon creation requires write permissions to your media folders.
        """)
        req_text.setWordWrap(True)
        req_text.setOpenExternalLinks(True)
        req_layout.addWidget(req_text)
        
        layout.addWidget(req_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Features")
    
    def _connect_signals(self):
        """Connect UI signals."""
        self.directory_edit.textChanged.connect(self._on_settings_changed)
        self.api_key_edit.textChanged.connect(self._on_settings_changed)
        self.anilist_api_key_edit.textChanged.connect(self._on_settings_changed)
        self.frequency_spin.valueChanged.connect(self._on_settings_changed)
    
    def _browse_directory(self):
        """Browse for media directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Media Directory",
            self.directory_edit.text() or str(Path.home())        )
        
        if directory:
            self.directory_edit.setText(directory)
    
    def _toggle_api_key_visibility(self, show: bool):
        """Toggle TMDB API key visibility."""
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password)
    
    def _toggle_anilist_api_key_visibility(self, show: bool):
        """Toggle AniList API key visibility."""
        self.anilist_api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password)
    
    def _on_settings_changed(self):
        """Handle settings change."""
        self.ok_button.setEnabled(False)
        self.validation_label.setText("Settings changed. Click 'Validate Settings' to verify.")
        self.validation_label.setStyleSheet("margin: 10px; font-style: italic; color: #666;")
    
    def _validate_settings(self):
        """Validate the current settings."""
        directory = self.directory_edit.text().strip()
        api_key = self.api_key_edit.text().strip()
        anilist_api_key = self.anilist_api_key_edit.text().strip()
        
        if not directory:
            QMessageBox.warning(self, "Validation Error", "Please select a media directory.")
            return
        
        # Start validation in background
        self.validate_button.setEnabled(False)
        self.validate_button.setText("Validating...")
        
        self.validation_worker = ValidationWorker(directory, api_key, anilist_api_key)
        self.validation_worker.validation_complete.connect(self._on_validation_complete)
        self.validation_worker.start()
    
    def _on_validation_complete(self, result):
        """Handle validation completion."""
        self.validate_button.setEnabled(True)
        self.validate_button.setText("Validate Settings")
        
        if result['directory_valid']:
            # Success - directory is valid
            stats = result.get('directory_stats', {})
            message = "✅ Validation successful!\n\n"
            message += f"Directory: {self.directory_edit.text()}\n"
            message += f"• Video files: {stats.get('video_files', 0)}\n"
            message += f"• TV show folders: {stats.get('tv_folders', 0)}\n"
            message += f"• Total folders: {stats.get('total_folders', 0)}\n\n"
            
            # Add API key validation results
            if result['tmdb_api_key_valid']:
                message += "✅ TMDB API key: Valid\n"
            elif self.api_key_edit.text().strip():
                message += "❌ TMDB API key: Invalid\n"
            else:
                message += "⚠️ TMDB API key: Not provided (some features will be limited)\n"
            
            if result['anilist_api_key_valid']:
                message += "✅ AniList API key: Valid\n"
            elif self.anilist_api_key_edit.text().strip():
                message += "❌ AniList API key: Invalid\n"
            else:
                message += "✅ AniList API key: Not required (using public API)\n"
            
            self.validation_label.setText(message)
            self.validation_label.setStyleSheet("margin: 10px; color: green;")
            self.ok_button.setEnabled(True)
            
        else:
            # Failure
            errors = []
            if not result['directory_valid']:
                errors.append(f"Directory: {result.get('error_message', 'Invalid directory')}")
            if not result['tmdb_api_key_valid'] and self.api_key_edit.text().strip():
                errors.append("TMDB API Key: Invalid or expired")
            if not result['anilist_api_key_valid'] and self.anilist_api_key_edit.text().strip():
                errors.append("AniList API Key: Invalid or expired")
            
            message = f"❌ Validation failed:\n" + "\n".join(f"• {error}" for error in errors)
            self.validation_label.setText(message)
            self.validation_label.setStyleSheet("margin: 10px; color: red;")
            self.ok_button.setEnabled(False)
    
    def _save_and_accept(self):
        """Save settings and accept dialog."""
        try:            # Update settings
            self.settings.media_directory = self.directory_edit.text().strip()
            self.settings.scan_frequency = self.frequency_spin.value()
            self.settings.tray_mode = self.tray_mode_check.isChecked()
            self.settings.api_keys.tmdb = self.api_key_edit.text().strip()
            self.settings.api_keys.anilist = self.anilist_api_key_edit.text().strip()
            
            # Update features
            self.settings.features.tv_shows = self.tv_shows_check.isChecked()
            self.settings.features.movies = self.movies_check.isChecked()
            self.settings.features.anime = self.anime_check.isChecked()
            
            # Save settings
            self.settings.save()
            
            logger.info("Settings saved successfully")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
            logger.error(f"Failed to save settings: {e}")
    
    def _load_existing_settings(self):
        """Load existing settings if available."""
        try:
            existing_settings = AppSettings.load()
            
            if existing_settings.media_directory:
                self.directory_edit.setText(existing_settings.media_directory)
              if existing_settings.api_keys.tmdb:
                self.api_key_edit.setText(existing_settings.api_keys.tmdb)
            
            if existing_settings.api_keys.anilist:
                self.anilist_api_key_edit.setText(existing_settings.api_keys.anilist)
            
            self.frequency_spin.setValue(existing_settings.scan_frequency)
            self.tray_mode_check.setChecked(existing_settings.tray_mode)
            
            self.tv_shows_check.setChecked(existing_settings.features.tv_shows)
            self.movies_check.setChecked(existing_settings.features.movies)
            self.anime_check.setChecked(existing_settings.features.anime)
            
        except Exception as e:
            logger.debug(f"No existing settings to load: {e}")
