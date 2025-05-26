"""
Directory scanning and media detection functionality.
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from utils.file_utils import scan_movies, scan_tv_shows, is_video_file, clean_title
from api.anilist_client import AniListClient


logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Results from a directory scan."""
    movies: List[Dict[str, Any]]
    tv_shows: List[Dict[str, Any]]
    anime: List[Dict[str, Any]]
    scan_time: datetime
    total_files: int
    
    def __str__(self) -> str:
        return (f"Scan completed: {len(self.movies)} movies, "
                f"{len(self.tv_shows)} TV shows, {len(self.anime)} anime")


class MediaScanner:
    """Scans directories for movies, TV shows, and anime."""
    
    def __init__(self):
        """Initialize the media scanner."""
        self.anilist_client = AniListClient()
        self._anime_cache = {}  # Cache anime detection results
    
    def scan_directory(self, directory: Path, detect_anime: bool = True) -> ScanResult:
        """
        Scan a directory for all media types.
        
        Args:
            directory: Directory to scan
            detect_anime: Whether to detect anime (requires API calls)
            
        Returns:
            ScanResult containing all found media
        """
        logger.info(f"Starting media scan of: {directory}")
        scan_start = datetime.now()
        
        # Scan for movies and TV shows
        movies = scan_movies(directory)
        tv_shows = scan_tv_shows(directory)
        
        # Detect anime from the results
        anime = []
        if detect_anime:
            anime = self._detect_anime(movies + tv_shows)
        
        # Remove anime from movies/TV shows lists to avoid duplicates
        if anime:
            anime_titles = {item['title'].lower() for item in anime}
            movies = [m for m in movies if m['title'].lower() not in anime_titles]
            tv_shows = [tv for tv in tv_shows if tv['title'].lower() not in anime_titles]
        
        # Count total files
        total_files = sum(1 for _ in directory.rglob('*') if _.is_file())
        
        result = ScanResult(
            movies=movies,
            tv_shows=tv_shows,
            anime=anime,
            scan_time=scan_start,
            total_files=total_files
        )
        
        logger.info(str(result))
        return result
    
    def _detect_anime(self, media_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect which media items are anime using AniList API.
        
        Args:
            media_items: List of media items (movies + TV shows)
            
        Returns:
            List of anime items
        """
        anime = []
        
        logger.info(f"Checking {len(media_items)} items for anime...")
        
        for item in media_items:
            title = item['title']
            
            # Check cache first
            if title.lower() in self._anime_cache:
                if self._anime_cache[title.lower()]:
                    anime.append(item)
                continue
            
            # Check with AniList API
            try:
                is_anime = self.anilist_client.is_likely_anime(title)
                self._anime_cache[title.lower()] = is_anime
                
                if is_anime:
                    logger.info(f"Detected anime: {title}")
                    anime.append(item)
                    
            except Exception as e:
                logger.warning(f"Failed to check anime status for '{title}': {e}")
                # Cache as non-anime to avoid repeated failures
                self._anime_cache[title.lower()] = False
        
        return anime
    
    def scan_movies_only(self, directory: Path) -> List[Dict[str, Any]]:
        """
        Scan directory for movies only.
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of movie information
        """
        return scan_movies(directory)
    
    def scan_tv_shows_only(self, directory: Path) -> List[Dict[str, Any]]:
        """
        Scan directory for TV shows only.
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of TV show information
        """
        return scan_tv_shows(directory)
    
    def quick_scan(self, directory: Path) -> Dict[str, int]:
        """
        Perform a quick scan to get counts without detailed analysis.
        
        Args:
            directory: Directory to scan
            
        Returns:
            Dictionary with counts of different media types
        """
        logger.info(f"Quick scan of: {directory}")
        
        video_files = 0
        tv_folders = 0
        total_folders = 0
        
        try:
            for item in directory.rglob('*'):
                if item.is_file() and is_video_file(item):
                    video_files += 1
                elif item.is_dir():
                    total_folders += 1
                    # Check if it looks like a TV show folder
                    if any(re.search(r'season\s*\d+', sub.name, re.IGNORECASE) 
                          for sub in item.iterdir() if sub.is_dir()):
                        tv_folders += 1
        
        except Exception as e:
            logger.error(f"Quick scan failed: {e}")
            return {'error': True}
        
        return {
            'video_files': video_files,
            'tv_folders': tv_folders,
            'total_folders': total_folders
        }
    
    def validate_directory(self, directory: Path) -> Dict[str, Any]:
        """
        Validate if directory is suitable for media scanning.
        
        Args:
            directory: Directory to validate
            
        Returns:
            Validation result dictionary
        """
        if not directory.exists():
            return {
                'valid': False,
                'error': 'Directory does not exist'
            }
        
        if not directory.is_dir():
            return {
                'valid': False,
                'error': 'Path is not a directory'
            }
        
        try:
            # Try to list directory contents
            list(directory.iterdir())
        except PermissionError:
            return {
                'valid': False,
                'error': 'Permission denied'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': f'Cannot access directory: {e}'
            }
        
        # Check if directory contains media files
        quick_scan = self.quick_scan(directory)
        if quick_scan.get('error'):
            return {
                'valid': False,
                'error': 'Failed to scan directory'
            }
        
        return {
            'valid': True,
            'stats': quick_scan
        }
