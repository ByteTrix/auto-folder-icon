"""
Background task scheduling and automation.
"""

import logging
from datetime import datetime, timedelta
from typing import Callable, Optional
from threading import Thread, Event
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from config.settings import AppSettings
from core.scanner import MediaScanner
from core.icon_manager import IconManager
from core.thumbnail_embedder import ThumbnailEmbedder


logger = logging.getLogger(__name__)


class TaskScheduler:
    """Manages background tasks and scheduling."""
    
    def __init__(self, settings: AppSettings, icon_manager: IconManager, thumbnail_embedder: ThumbnailEmbedder):
        """
        Initialize the task scheduler.
        
        Args:
            settings: Application settings
            icon_manager: Icon manager instance
            thumbnail_embedder: Thumbnail embedder instance
        """
        self.settings = settings
        self.icon_manager = icon_manager
        self.thumbnail_embedder = thumbnail_embedder
        self.scanner = MediaScanner()
        
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self._scan_in_progress = False
        
        # Callbacks for UI updates
        self.scan_started_callback: Optional[Callable] = None
        self.scan_completed_callback: Optional[Callable] = None
        self.scan_progress_callback: Optional[Callable] = None
        self.scan_error_callback: Optional[Callable] = None
    
    def start(self) -> None:
        """Start the scheduler."""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            self._schedule_periodic_scan()
            logger.info("Task scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Task scheduler stopped")
    
    def _schedule_periodic_scan(self) -> None:
        """Schedule periodic media scanning."""
        if not self.settings.media_directory:
            logger.warning("No media directory configured, skipping periodic scan scheduling")
            return
        
        # Remove existing scan job if any
        try:
            self.scheduler.remove_job('periodic_scan')
        except:
            pass
        
        # Schedule new scan job
        trigger = IntervalTrigger(hours=self.settings.scan_frequency)
        self.scheduler.add_job(
            self._perform_scheduled_scan,
            trigger=trigger,
            id='periodic_scan',
            name='Periodic Media Scan',
            max_instances=1  # Prevent overlapping scans
        )
        
        logger.info(f"Scheduled periodic scan every {self.settings.scan_frequency} hours")
    
    def _perform_scheduled_scan(self) -> None:
        """Perform a scheduled media scan."""
        if self._scan_in_progress:
            logger.warning("Scan already in progress, skipping scheduled scan")
            return
        
        logger.info("Starting scheduled media scan")
        
        try:
            self._scan_in_progress = True
            
            if self.scan_started_callback:
                self.scan_started_callback("Scheduled scan started")
            
            # Perform the scan
            media_directory = Path(self.settings.media_directory)
            scan_result = self.scanner.scan_directory(media_directory, detect_anime=self.settings.features.anime)
            
            # Process results
            self._process_scan_results(scan_result)
            
            # Update last scan time
            self.settings.last_scan = datetime.now().isoformat()
            self.settings.save()
            
            if self.scan_completed_callback:
                self.scan_completed_callback(scan_result)
            
            logger.info("Scheduled scan completed successfully")
            
        except Exception as e:
            logger.error(f"Scheduled scan failed: {e}")
            if self.scan_error_callback:
                self.scan_error_callback(str(e))
        finally:
            self._scan_in_progress = False
    
    def manual_scan(self, progress_callback: Optional[Callable] = None) -> None:
        """
        Perform a manual media scan.
        
        Args:
            progress_callback: Callback for progress updates
        """
        if self._scan_in_progress:
            logger.warning("Scan already in progress")
            return
        
        def scan_worker():
            try:
                self._scan_in_progress = True
                
                if self.scan_started_callback:
                    self.scan_started_callback("Manual scan started")
                
                # Perform the scan
                media_directory = Path(self.settings.media_directory)
                scan_result = self.scanner.scan_directory(media_directory, detect_anime=self.settings.features.anime)
                
                # Process results with progress callback
                self._process_scan_results(scan_result, progress_callback)
                
                # Update last scan time
                self.settings.last_scan = datetime.now().isoformat()
                self.settings.save()
                
                if self.scan_completed_callback:
                    self.scan_completed_callback(scan_result)
                
                logger.info("Manual scan completed successfully")
                
            except Exception as e:
                logger.error(f"Manual scan failed: {e}")
                if self.scan_error_callback:
                    self.scan_error_callback(str(e))
            finally:
                self._scan_in_progress = False
        
        # Run scan in background thread
        scan_thread = Thread(target=scan_worker, daemon=True)
        scan_thread.start()
    
    def _process_scan_results(self, scan_result, progress_callback: Optional[Callable] = None) -> None:
        """
        Process scan results by setting icons and embedding thumbnails.
        
        Args:
            scan_result: Results from media scan
            progress_callback: Callback for progress updates
        """
        total_tasks = 0
        completed_tasks = 0
        
        # Count total tasks
        if self.settings.features.tv_shows:
            total_tasks += len(scan_result.tv_shows)
        if self.settings.features.anime:
            total_tasks += len(scan_result.anime)
        if self.settings.features.movies:
            total_tasks += len(scan_result.movies)
        
        def update_progress(message: str):
            nonlocal completed_tasks
            completed_tasks += 1
            if progress_callback:
                progress_callback(completed_tasks, total_tasks, message)
        
        # Set TV show icons
        if self.settings.features.tv_shows and scan_result.tv_shows:
            logger.info(f"Setting icons for {len(scan_result.tv_shows)} TV shows")
            for tv_show in scan_result.tv_shows:
                try:
                    self.icon_manager.set_tv_show_icon(
                        tv_show['path'],
                        tv_show['title'],
                        tv_show.get('year')
                    )
                    update_progress(f"Set icon for TV show: {tv_show['title']}")
                except Exception as e:
                    logger.error(f"Failed to set icon for {tv_show['title']}: {e}")
                    update_progress(f"Failed to set icon for: {tv_show['title']}")
        
        # Set anime icons
        if self.settings.features.anime and scan_result.anime:
            logger.info(f"Setting icons for {len(scan_result.anime)} anime")
            for anime in scan_result.anime:
                try:
                    self.icon_manager.set_anime_icon(
                        anime['path'],
                        anime['title'],
                        anime.get('year')
                    )
                    update_progress(f"Set icon for anime: {anime['title']}")
                except Exception as e:
                    logger.error(f"Failed to set icon for {anime['title']}: {e}")
                    update_progress(f"Failed to set icon for: {anime['title']}")
        
        # Embed movie thumbnails
        if self.settings.features.movies and scan_result.movies:
            logger.info(f"Embedding thumbnails for {len(scan_result.movies)} movies")
            for movie in scan_result.movies:
                try:
                    self.thumbnail_embedder.embed_movie_thumbnail(
                        movie['path'],
                        movie['title'],
                        movie.get('year')
                    )
                    update_progress(f"Embedded thumbnail for: {movie['title']}")
                except Exception as e:
                    logger.error(f"Failed to embed thumbnail for {movie['title']}: {e}")
                    update_progress(f"Failed to embed thumbnail for: {movie['title']}")
    
    def schedule_cache_cleanup(self) -> None:
        """Schedule periodic cache cleanup."""
        try:
            self.scheduler.remove_job('cache_cleanup')
        except:
            pass
        
        # Schedule cleanup weekly
        trigger = CronTrigger(day_of_week=0, hour=2)  # Sunday 2 AM
        self.scheduler.add_job(
            self._cleanup_cache,
            trigger=trigger,
            id='cache_cleanup',
            name='Weekly Cache Cleanup'
        )
        
        logger.info("Scheduled weekly cache cleanup")
    
    def _cleanup_cache(self) -> None:
        """Clean up old cache files."""
        try:
            deleted_count = self.icon_manager.clean_icon_cache(max_age_days=30)
            logger.info(f"Cache cleanup completed: {deleted_count} files deleted")
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
    
    def update_schedule(self, new_frequency: int) -> None:
        """
        Update scan frequency.
        
        Args:
            new_frequency: New scan frequency in hours
        """
        self.settings.scan_frequency = new_frequency
        self._schedule_periodic_scan()
        logger.info(f"Updated scan frequency to {new_frequency} hours")
    
    def get_next_scan_time(self) -> Optional[datetime]:
        """
        Get the next scheduled scan time.
        
        Returns:
            Next scan datetime or None if not scheduled
        """
        try:
            job = self.scheduler.get_job('periodic_scan')
            if job:
                return job.next_run_time
        except:
            pass
        return None
    
    def is_scan_in_progress(self) -> bool:
        """
        Check if a scan is currently in progress.
        
        Returns:
            True if scan is in progress, False otherwise
        """
        return self._scan_in_progress
    
    def set_callbacks(self, 
                     scan_started: Optional[Callable] = None,
                     scan_completed: Optional[Callable] = None,
                     scan_progress: Optional[Callable] = None,
                     scan_error: Optional[Callable] = None) -> None:
        """
        Set callback functions for scan events.
        
        Args:
            scan_started: Called when scan starts
            scan_completed: Called when scan completes
            scan_progress: Called for progress updates
            scan_error: Called when scan encounters error
        """
        self.scan_started_callback = scan_started
        self.scan_completed_callback = scan_completed
        self.scan_progress_callback = scan_progress
        self.scan_error_callback = scan_error
