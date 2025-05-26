"""
Main application window with tabbed interface for managing media.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QFormLayout, QLineEdit, QSpinBox,
    QCheckBox, QMessageBox, QSplitter, QHeaderView, QStatusBar,
    QMenuBar, QMenu, QToolBar, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QAction, QIcon, QPixmap

from config.settings import AppSettings
from core.scanner import MediaScanner
from core.icon_manager import IconManager
from core.thumbnail_embedder import ThumbnailEmbedder
from core.scheduler import TaskScheduler
from api.tmdb_client import TMDBClient
from utils.logger import add_gui_logging, remove_gui_logging


logger = logging.getLogger(__name__)


class ScanWorker(QThread):
    """Worker thread for performing scans."""
    
    scan_progress = Signal(int, int, str)  # current, total, message
    scan_complete = Signal(object)  # scan result
    scan_error = Signal(str)  # error message
    
    def __init__(self, scanner: MediaScanner, directory: Path, detect_anime: bool = True):
        super().__init__()
        self.scanner = scanner
        self.directory = directory
        self.detect_anime = detect_anime
    
    def run(self):
        """Run the scan in background."""
        try:
            result = self.scanner.scan_directory(self.directory, self.detect_anime)
            self.scan_complete.emit(result)
        except Exception as e:
            logger.error(f"Scan worker error: {e}")
            self.scan_error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.scan_worker = None
        
        # Initialize components
        self._init_api_clients()
        self._init_core_components()
        self._init_ui()
        self._init_scheduler()
        self._connect_signals()
        
        # Setup GUI logging
        add_gui_logging(self.log_text)
        
        logger.info("Main window initialized")
    
    def _init_api_clients(self):
        """Initialize API clients."""
        self.tmdb_client = None
        if self.settings.api_keys.tmdb:
            self.tmdb_client = TMDBClient(self.settings.api_keys.tmdb)
    
    def _init_core_components(self):
        """Initialize core components."""
        self.scanner = MediaScanner()
        
        cache_dir = self.settings.get_cache_directory()
        self.icon_manager = IconManager(self.tmdb_client, cache_dir)
        
        ffmpeg_path = self.settings.get_ffmpeg_path()
        self.thumbnail_embedder = ThumbnailEmbedder(self.tmdb_client, ffmpeg_path, cache_dir)
    
    def _init_scheduler(self):
        """Initialize task scheduler."""
        self.scheduler = TaskScheduler(self.settings, self.icon_manager, self.thumbnail_embedder)
        
        # Set callbacks
        self.scheduler.set_callbacks(
            scan_started=self._on_scan_started,
            scan_completed=self._on_scan_completed,
            scan_progress=self._on_scan_progress,
            scan_error=self._on_scan_error
        )
        
        if self.settings.media_directory:
            self.scheduler.start()
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Media Folder Icon Manager")
        self.setMinimumSize(1000, 700)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create toolbar
        self._create_toolbar()
        
        # Create status bar
        self._create_status_bar()
        
        # Create main content
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # Top section - tabs
        self.tab_widget = QTabWidget()
        splitter.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_overview_tab()
        self._create_movies_tab()
        self._create_tv_shows_tab()
        self._create_anime_tab()
        self._create_settings_tab()
        
        # Bottom section - logs
        log_group = QGroupBox("Application Logs")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        splitter.addWidget(log_group)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
    
    def _create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        scan_action = QAction("Start Scan", self)
        scan_action.setShortcut("Ctrl+S")
        scan_action.triggered.connect(self._start_manual_scan)
        file_menu.addAction(scan_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        clean_cache_action = QAction("Clean Cache", self)
        clean_cache_action.triggered.connect(self._clean_cache)
        tools_menu.addAction(clean_cache_action)
        
        validate_action = QAction("Validate Settings", self)
        validate_action.triggered.connect(self._validate_settings)
        tools_menu.addAction(validate_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self):
        """Create the toolbar."""
        toolbar = self.addToolBar("Main")
        
        # Scan button
        self.scan_button = QPushButton("Start Scan")
        self.scan_button.clicked.connect(self._start_manual_scan)
        toolbar.addWidget(self.scan_button)
        
        toolbar.addSeparator()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        toolbar.addWidget(self.progress_bar)
    
    def _create_status_bar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Last scan label
        self.last_scan_label = QLabel()
        self.status_bar.addPermanentWidget(self.last_scan_label)
        
        self._update_status()
    
    def _create_overview_tab(self):
        """Create the overview tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Statistics group
        stats_group = QGroupBox("Media Statistics")
        stats_layout = QFormLayout(stats_group)
        
        self.stats_movies = QLabel("0")
        self.stats_tv_shows = QLabel("0")
        self.stats_anime = QLabel("0")
        self.stats_last_scan = QLabel("Never")
        
        stats_layout.addRow("Movies:", self.stats_movies)
        stats_layout.addRow("TV Shows:", self.stats_tv_shows)
        stats_layout.addRow("Anime:", self.stats_anime)
        stats_layout.addRow("Last Scan:", self.stats_last_scan)
        
        layout.addWidget(stats_group)
        
        # Quick actions group
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        scan_now_btn = QPushButton("Scan Media Directory")
        scan_now_btn.clicked.connect(self._start_manual_scan)
        actions_layout.addWidget(scan_now_btn)
        
        open_media_btn = QPushButton("Open Media Directory")
        open_media_btn.clicked.connect(self._open_media_directory)
        actions_layout.addWidget(open_media_btn)
        
        layout.addWidget(actions_group)
        
        # Cache statistics group
        cache_group = QGroupBox("Cache Statistics")
        cache_layout = QFormLayout(cache_group)
        
        self.cache_posters = QLabel("0")
        self.cache_icons = QLabel("0")
        self.cache_size = QLabel("0 MB")
        
        cache_layout.addRow("Cached Posters:", self.cache_posters)
        cache_layout.addRow("Cached Icons:", self.cache_icons)
        cache_layout.addRow("Cache Size:", self.cache_size)
        
        clean_cache_btn = QPushButton("Clean Cache")
        clean_cache_btn.clicked.connect(self._clean_cache)
        cache_layout.addRow("", clean_cache_btn)
        
        layout.addWidget(cache_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Overview")
    
    def _create_movies_tab(self):
        """Create the movies tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        embed_all_btn = QPushButton("Embed All Thumbnails")
        embed_all_btn.clicked.connect(self._embed_all_thumbnails)
        controls_layout.addWidget(embed_all_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Movies table
        self.movies_table = QTableWidget()
        self.movies_table.setColumnCount(4)
        self.movies_table.setHorizontalHeaderLabels(["Title", "Year", "Path", "Has Thumbnail"])
        
        header = self.movies_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        
        layout.addWidget(self.movies_table)
        
        self.tab_widget.addTab(tab, "Movies")
    
    def _create_tv_shows_tab(self):
        """Create the TV shows tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        set_all_icons_btn = QPushButton("Set All TV Show Icons")
        set_all_icons_btn.clicked.connect(self._set_all_tv_icons)
        controls_layout.addWidget(set_all_icons_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # TV shows table
        self.tv_shows_table = QTableWidget()
        self.tv_shows_table.setColumnCount(3)
        self.tv_shows_table.setHorizontalHeaderLabels(["Title", "Path", "Has Icon"])
        
        header = self.tv_shows_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        
        layout.addWidget(self.tv_shows_table)
        
        self.tab_widget.addTab(tab, "TV Shows")
    
    def _create_anime_tab(self):
        """Create the anime tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        set_all_anime_icons_btn = QPushButton("Set All Anime Icons")
        set_all_anime_icons_btn.clicked.connect(self._set_all_anime_icons)
        controls_layout.addWidget(set_all_anime_icons_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Anime table
        self.anime_table = QTableWidget()
        self.anime_table.setColumnCount(3)
        self.anime_table.setHorizontalHeaderLabels(["Title", "Path", "Has Icon"])
        
        header = self.anime_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        
        layout.addWidget(self.anime_table)
        
        self.tab_widget.addTab(tab, "Anime")
    
    def _create_settings_tab(self):
        """Create the settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Media directory group
        media_group = QGroupBox("Media Directory")
        media_layout = QFormLayout(media_group)
        
        self.media_dir_edit = QLineEdit(self.settings.media_directory or "")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_media_directory)
        
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.media_dir_edit)
        dir_layout.addWidget(browse_btn)
        
        media_layout.addRow("Directory:", dir_layout)
        layout.addWidget(media_group)
        
        # Scan settings group
        scan_group = QGroupBox("Scan Settings")
        scan_layout = QFormLayout(scan_group)
        
        self.frequency_spin = QSpinBox()
        self.frequency_spin.setRange(1, 168)
        self.frequency_spin.setValue(self.settings.scan_frequency)
        self.frequency_spin.setSuffix(" hours")
        
        self.tray_mode_check = QCheckBox()
        self.tray_mode_check.setChecked(self.settings.tray_mode)
        
        scan_layout.addRow("Frequency:", self.frequency_spin)
        scan_layout.addRow("Tray Mode:", self.tray_mode_check)
        layout.addWidget(scan_group)
        
        # Features group
        features_group = QGroupBox("Features")
        features_layout = QVBoxLayout(features_group)
        
        self.tv_shows_check = QCheckBox("Set folder icons for TV Shows")
        self.tv_shows_check.setChecked(self.settings.features.tv_shows)
        
        self.movies_check = QCheckBox("Embed thumbnails in Movie files")
        self.movies_check.setChecked(self.settings.features.movies)
        
        self.anime_check = QCheckBox("Set folder icons for Anime")
        self.anime_check.setChecked(self.settings.features.anime)
        
        features_layout.addWidget(self.tv_shows_check)
        features_layout.addWidget(self.movies_check)
        features_layout.addWidget(self.anime_check)
        
        layout.addWidget(features_group)
        
        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Settings")
    
    def _connect_signals(self):
        """Connect UI signals."""
        # Timer for updating status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(5000)  # Update every 5 seconds
    
    def _start_manual_scan(self):
        """Start a manual media scan."""
        if not self.settings.media_directory:
            QMessageBox.warning(self, "Error", "Please set a media directory first.")
            return
        
        if self.scan_worker and self.scan_worker.isRunning():
            QMessageBox.information(self, "Scan In Progress", "A scan is already running.")
            return
        
        # Start scan worker
        self.scan_worker = ScanWorker(
            self.scanner,
            Path(self.settings.media_directory),
            self.settings.features.anime
        )
        
        self.scan_worker.scan_progress.connect(self._on_scan_progress)
        self.scan_worker.scan_complete.connect(self._on_manual_scan_complete)
        self.scan_worker.scan_error.connect(self._on_scan_error)
        
        self.scan_worker.start()
        
        # Update UI
        self.scan_button.setEnabled(False)
        self.scan_button.setText("Scanning...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        logger.info("Manual scan started")
    
    def _on_scan_started(self, message: str):
        """Handle scan started event."""
        self.status_label.setText(message)
        logger.info(message)
    
    def _on_scan_progress(self, current: int, total: int, message: str):
        """Handle scan progress update."""
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        
        self.status_label.setText(f"{message} ({current}/{total})")
    
    def _on_manual_scan_complete(self, scan_result):
        """Handle manual scan completion."""
        self._on_scan_completed(scan_result)
        
        # Reset UI
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Start Scan")
        self.progress_bar.setVisible(False)
    
    def _on_scan_completed(self, scan_result):
        """Handle scan completion."""
        # Update tables
        self._update_movies_table(scan_result.movies)
        self._update_tv_shows_table(scan_result.tv_shows)
        self._update_anime_table(scan_result.anime)
        
        # Update statistics
        self._update_statistics(scan_result)
        
        self.status_label.setText("Scan completed")
        logger.info(f"Scan completed: {scan_result}")
    
    def _on_scan_error(self, error_message: str):
        """Handle scan error."""
        QMessageBox.critical(self, "Scan Error", f"Scan failed: {error_message}")
        
        # Reset UI
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Start Scan")
        self.progress_bar.setVisible(False)
        
        self.status_label.setText("Scan failed")
        logger.error(f"Scan error: {error_message}")
    
    def _update_movies_table(self, movies):
        """Update the movies table."""
        self.movies_table.setRowCount(len(movies))
        
        for row, movie in enumerate(movies):
            self.movies_table.setItem(row, 0, QTableWidgetItem(movie['title']))
            self.movies_table.setItem(row, 1, QTableWidgetItem(str(movie.get('year', ''))))
            self.movies_table.setItem(row, 2, QTableWidgetItem(str(movie['path'])))
            
            # Check if has thumbnail
            has_thumb = self.thumbnail_embedder.has_embedded_thumbnail(movie['path'])
            self.movies_table.setItem(row, 3, QTableWidgetItem("Yes" if has_thumb else "No"))
    
    def _update_tv_shows_table(self, tv_shows):
        """Update the TV shows table."""
        self.tv_shows_table.setRowCount(len(tv_shows))
        
        for row, show in enumerate(tv_shows):
            self.tv_shows_table.setItem(row, 0, QTableWidgetItem(show['title']))
            self.tv_shows_table.setItem(row, 1, QTableWidgetItem(str(show['path'])))
            
            # Check if has icon
            from utils.file_utils import has_custom_icon
            has_icon = has_custom_icon(show['path'])
            self.tv_shows_table.setItem(row, 2, QTableWidgetItem("Yes" if has_icon else "No"))
    
    def _update_anime_table(self, anime):
        """Update the anime table."""
        self.anime_table.setRowCount(len(anime))
        
        for row, item in enumerate(anime):
            self.anime_table.setItem(row, 0, QTableWidgetItem(item['title']))
            self.anime_table.setItem(row, 1, QTableWidgetItem(str(item['path'])))
            
            # Check if has icon
            from utils.file_utils import has_custom_icon
            has_icon = has_custom_icon(item['path'])
            self.anime_table.setItem(row, 2, QTableWidgetItem("Yes" if has_icon else "No"))
    
    def _update_statistics(self, scan_result):
        """Update statistics display."""
        self.stats_movies.setText(str(len(scan_result.movies)))
        self.stats_tv_shows.setText(str(len(scan_result.tv_shows)))
        self.stats_anime.setText(str(len(scan_result.anime)))
        self.stats_last_scan.setText(scan_result.scan_time.strftime("%Y-%m-%d %H:%M:%S"))
        
        # Update cache stats
        cache_stats = self.icon_manager.get_cache_stats()
        self.cache_posters.setText(str(cache_stats['poster_count']))
        self.cache_icons.setText(str(cache_stats['icon_count']))
        self.cache_size.setText(f"{cache_stats['total_size_mb']} MB")
    
    def _update_status(self):
        """Update status bar."""
        try:
            if self.settings.last_scan:
                last_scan = datetime.fromisoformat(self.settings.last_scan)
                self.last_scan_label.setText(f"Last scan: {last_scan.strftime('%H:%M %d/%m')}")
            else:
                self.last_scan_label.setText("Last scan: Never")
                
        except Exception as e:
            logger.debug(f"Failed to update status: {e}")
    
    def _browse_media_directory(self):
        """Browse for media directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Media Directory",
            self.media_dir_edit.text() or str(Path.home())
        )
        
        if directory:
            self.media_dir_edit.setText(directory)
    
    def _save_settings(self):
        """Save current settings."""
        try:
            # Update settings
            self.settings.media_directory = self.media_dir_edit.text().strip()
            self.settings.scan_frequency = self.frequency_spin.value()
            self.settings.tray_mode = self.tray_mode_check.isChecked()
            
            self.settings.features.tv_shows = self.tv_shows_check.isChecked()
            self.settings.features.movies = self.movies_check.isChecked()
            self.settings.features.anime = self.anime_check.isChecked()
            
            # Save to file
            self.settings.save()
            
            # Update scheduler
            if hasattr(self, 'scheduler'):
                self.scheduler.update_schedule(self.settings.scan_frequency)
            
            QMessageBox.information(self, "Settings", "Settings saved successfully!")
            logger.info("Settings saved")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
            logger.error(f"Failed to save settings: {e}")
    
    def _embed_all_thumbnails(self):
        """Embed thumbnails in all movies."""
        # This would be implemented as a background task
        QMessageBox.information(self, "Info", "This feature will be implemented to run in background")
    
    def _set_all_tv_icons(self):
        """Set icons for all TV shows."""
        # This would be implemented as a background task
        QMessageBox.information(self, "Info", "This feature will be implemented to run in background")
    
    def _set_all_anime_icons(self):
        """Set icons for all anime."""
        # This would be implemented as a background task
        QMessageBox.information(self, "Info", "This feature will be implemented to run in background")
    
    def _open_media_directory(self):
        """Open media directory in file explorer."""
        if self.settings.media_directory:
            import subprocess
            subprocess.Popen(['explorer', self.settings.media_directory])
    
    def _clean_cache(self):
        """Clean cache files."""
        try:
            deleted_count = self.icon_manager.clean_icon_cache()
            QMessageBox.information(self, "Cache Cleaned", f"Deleted {deleted_count} cache files")
            
            # Update cache stats
            cache_stats = self.icon_manager.get_cache_stats()
            self.cache_posters.setText(str(cache_stats['poster_count']))
            self.cache_icons.setText(str(cache_stats['icon_count']))
            self.cache_size.setText(f"{cache_stats['total_size_mb']} MB")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clean cache: {e}")
    
    def _validate_settings(self):
        """Validate current settings."""
        # This would implement settings validation
        QMessageBox.information(self, "Validation", "Settings validation feature coming soon")
    
    def _show_about(self):
        """Show about dialog."""
        about_text = """
        <h3>Media Folder Icon Manager</h3>
        <p>Version 1.0</p>
        
        <p>Automatically sets folder icons for TV shows and anime,<br>
        and embeds poster thumbnails in movie files.</p>
        
        <p><b>Features:</b></p>
        <ul>
        <li>Automatic media directory scanning</li>
        <li>Custom folder icons for TV shows and anime</li>
        <li>Poster thumbnail embedding in movies</li>
        <li>Background operation with system tray</li>
        </ul>
        """
        
        QMessageBox.about(self, "About", about_text)
    
    def show_settings(self):
        """Show settings tab."""
        self.tab_widget.setCurrentIndex(4)  # Settings tab
        self.show()
        self.raise_()
        self.activateWindow()
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.settings.tray_mode:
            # Hide to tray instead of closing
            event.ignore()
            self.hide()
            logger.info("Window hidden to tray")
        else:
            # Actually close the application
            remove_gui_logging()
            if hasattr(self, 'scheduler'):
                self.scheduler.stop()
            event.accept()
            logger.info("Application closing")
