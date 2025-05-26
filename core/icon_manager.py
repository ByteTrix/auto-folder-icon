"""
Folder icon management for setting custom icons on Windows folders.
"""

import logging
from pathlib import Path
from typing import Optional
from PIL import Image

from utils.file_utils import create_desktop_ini, refresh_folder_icon, has_custom_icon, get_safe_filename
from utils.image_utils import download_image, create_folder_icon, cache_poster, get_cached_poster
from api.tmdb_client import TMDBClient
from api.anilist_client import AniListClient


logger = logging.getLogger(__name__)


class IconManager:
    """Manages folder icons for TV shows and anime."""
    
    def __init__(self, tmdb_client: Optional[TMDBClient] = None, cache_dir: Optional[Path] = None):
        """
        Initialize the icon manager.
        
        Args:
            tmdb_client: TMDB client for fetching posters
            cache_dir: Directory for caching posters and icons
        """
        self.tmdb_client = tmdb_client
        self.anilist_client = AniListClient()
        self.cache_dir = cache_dir or Path("assets/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different cache types
        self.poster_cache_dir = self.cache_dir / "posters"
        self.icon_cache_dir = self.cache_dir / "icons"
        self.poster_cache_dir.mkdir(exist_ok=True)
        self.icon_cache_dir.mkdir(exist_ok=True)
    
    def set_tv_show_icon(self, folder_path: Path, title: str, year: Optional[int] = None, force: bool = False) -> bool:
        """
        Set folder icon for a TV show.
        
        Args:
            folder_path: Path to the TV show folder
            title: TV show title
            year: First air year (optional)
            force: Force update even if icon already exists
            
        Returns:
            True if successful, False otherwise
        """
        if not force and has_custom_icon(folder_path):
            logger.info(f"TV show {title} already has custom icon, skipping")
            return True
        
        logger.info(f"Setting icon for TV show: {title}")
        
        # Get poster URL from TMDB
        if not self.tmdb_client:
            logger.error("TMDB client not available")
            return False
        
        poster_url = self.tmdb_client.get_tv_poster(title, year)
        if not poster_url:
            logger.warning(f"No poster found for TV show: {title}")
            return False
        
        return self._create_and_set_icon(folder_path, title, poster_url, "tv")
    
    def set_anime_icon(self, folder_path: Path, title: str, year: Optional[int] = None, force: bool = False) -> bool:
        """
        Set folder icon for an anime.
        
        Args:
            folder_path: Path to the anime folder
            title: Anime title
            year: Season year (optional)
            force: Force update even if icon already exists
            
        Returns:
            True if successful, False otherwise
        """
        if not force and has_custom_icon(folder_path):
            logger.info(f"Anime {title} already has custom icon, skipping")
            return True
        
        logger.info(f"Setting icon for anime: {title}")
        
        # Get poster URL from AniList
        poster_url = self.anilist_client.get_anime_poster(title, year)
        if not poster_url:
            logger.warning(f"No poster found for anime: {title}")
            return False
        
        return self._create_and_set_icon(folder_path, title, poster_url, "anime")
    
    def _create_and_set_icon(self, folder_path: Path, title: str, poster_url: str, media_type: str) -> bool:
        """
        Create icon from poster and set it for the folder.
        
        Args:
            folder_path: Path to the folder
            title: Media title
            poster_url: URL to the poster image
            media_type: Type of media (tv, anime)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create safe filename for caching
            safe_title = get_safe_filename(title)
            cache_key = f"{media_type}_{safe_title}"
            
            # Check if icon is already cached
            icon_path = self.icon_cache_dir / f"{cache_key}.ico"
            
            if not icon_path.exists():
                # Download and cache poster
                logger.debug(f"Downloading poster from: {poster_url}")
                poster_image = download_image(poster_url)
                if not poster_image:
                    return False
                
                # Cache the poster
                poster_cache_path = cache_poster(poster_image, self.poster_cache_dir, cache_key)
                if not poster_cache_path:
                    return False
                
                # Create icon from poster
                logger.debug(f"Creating icon: {icon_path}")
                if not create_folder_icon(poster_image, icon_path):
                    return False
            else:
                logger.debug(f"Using cached icon: {icon_path}")
            
            # Create desktop.ini and set folder attributes
            if not create_desktop_ini(folder_path, icon_path):
                return False
            
            # Refresh folder icon in Explorer
            refresh_folder_icon(folder_path)
            
            logger.info(f"Successfully set icon for {media_type}: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set icon for {title}: {e}")
            return False
    
    def remove_icon(self, folder_path: Path) -> bool:
        """
        Remove custom icon from folder.
        
        Args:
            folder_path: Path to the folder
            
        Returns:
            True if successful, False otherwise
        """
        try:
            desktop_ini_path = folder_path / "desktop.ini"
            
            if desktop_ini_path.exists():
                # Remove desktop.ini file
                desktop_ini_path.unlink()
                logger.info(f"Removed desktop.ini from {folder_path}")
            
            # Remove read-only attribute from folder
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(folder_path), 0x80)  # FILE_ATTRIBUTE_NORMAL
            
            # Refresh folder icon
            refresh_folder_icon(folder_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove icon from {folder_path}: {e}")
            return False
    
    def batch_set_icons(self, items: list, media_type: str, progress_callback=None) -> dict:
        """
        Set icons for multiple items in batch.
        
        Args:
            items: List of media items
            media_type: Type of media (tv_shows, anime)
            progress_callback: Callback function for progress updates
            
        Returns:
            Dictionary with success/failure counts
        """
        total = len(items)
        successful = 0
        failed = 0
        
        logger.info(f"Starting batch icon setting for {total} {media_type}")
        
        for i, item in enumerate(items):
            try:
                folder_path = item['path']
                title = item['title']
                year = item.get('year')
                
                if media_type == 'tv_shows':
                    success = self.set_tv_show_icon(folder_path, title, year)
                elif media_type == 'anime':
                    success = self.set_anime_icon(folder_path, title, year)
                else:
                    success = False
                
                if success:
                    successful += 1
                else:
                    failed += 1
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(i + 1, total, title, success)
                    
            except Exception as e:
                logger.error(f"Error processing {item.get('title', 'unknown')}: {e}")
                failed += 1
        
        result = {
            'total': total,
            'successful': successful,
            'failed': failed
        }
        
        logger.info(f"Batch complete: {successful}/{total} successful")
        return result
    
    def clean_icon_cache(self, max_age_days: int = 30) -> int:
        """
        Clean old cached icons and posters.
        
        Args:
            max_age_days: Maximum age in days for cached files
            
        Returns:
            Number of files deleted
        """
        from utils.image_utils import clean_cache
        
        poster_deleted = clean_cache(self.poster_cache_dir, max_age_days)
        icon_deleted = clean_cache(self.icon_cache_dir, max_age_days)
        
        total_deleted = poster_deleted + icon_deleted
        logger.info(f"Cache cleanup completed: {total_deleted} files deleted")
        return total_deleted
    
    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            poster_count = len(list(self.poster_cache_dir.glob("*.jpg")))
            icon_count = len(list(self.icon_cache_dir.glob("*.ico")))
            
            # Calculate cache size
            poster_size = sum(f.stat().st_size for f in self.poster_cache_dir.glob("*.jpg"))
            icon_size = sum(f.stat().st_size for f in self.icon_cache_dir.glob("*.ico"))
            total_size = poster_size + icon_size
            
            return {
                'poster_count': poster_count,
                'icon_count': icon_count,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'poster_size_mb': round(poster_size / (1024 * 1024), 2),
                'icon_size_mb': round(icon_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                'poster_count': 0,
                'icon_count': 0,
                'total_size_mb': 0,
                'poster_size_mb': 0,
                'icon_size_mb': 0
            }
