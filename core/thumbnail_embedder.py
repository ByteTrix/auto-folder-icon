"""
Thumbnail embedding functionality for movie files using FFmpeg.
"""

import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image

from utils.file_utils import is_video_file, get_safe_filename
from utils.image_utils import download_image, resize_for_thumbnail, cache_poster
from api.tmdb_client import TMDBClient


logger = logging.getLogger(__name__)


class ThumbnailEmbedder:
    """Embeds poster thumbnails into movie files using FFmpeg."""
    
    def __init__(self, tmdb_client: Optional[TMDBClient] = None, ffmpeg_path: Optional[Path] = None, cache_dir: Optional[Path] = None):
        """
        Initialize the thumbnail embedder.
        
        Args:
            tmdb_client: TMDB client for fetching posters
            ffmpeg_path: Path to FFmpeg executable
            cache_dir: Directory for caching thumbnails
        """
        self.tmdb_client = tmdb_client
        self.ffmpeg_path = ffmpeg_path
        self.cache_dir = cache_dir or Path("assets/cache")
        
        # Create thumbnail cache directory
        self.thumbnail_cache_dir = self.cache_dir / "thumbnails"
        self.thumbnail_cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._validate_ffmpeg()
    
    def _validate_ffmpeg(self) -> bool:
        """
        Validate that FFmpeg is available.
        
        Returns:
            True if FFmpeg is available, False otherwise
        """
        if self.ffmpeg_path and self.ffmpeg_path.exists():
            return True
        
        # Try to find FFmpeg in PATH
        ffmpeg_exe = shutil.which("ffmpeg")
        if ffmpeg_exe:
            self.ffmpeg_path = Path(ffmpeg_exe)
            return True
        
        logger.warning("FFmpeg not found. Thumbnail embedding will not be available.")
        return False
    
    def embed_movie_thumbnail(self, movie_path: Path, title: str, year: Optional[int] = None, backup: bool = True) -> bool:
        """
        Embed poster thumbnail into movie file.
        
        Args:
            movie_path: Path to the movie file
            title: Movie title
            year: Release year (optional)
            backup: Whether to create backup of original file
            
        Returns:
            True if successful, False otherwise
        """
        if not self.ffmpeg_path:
            logger.error("FFmpeg not available")
            return False
        
        if not self.tmdb_client:
            logger.error("TMDB client not available")
            return False
        
        if not is_video_file(movie_path):
            logger.error(f"Not a video file: {movie_path}")
            return False
        
        logger.info(f"Embedding thumbnail for movie: {title}")
        
        try:
            # Get poster from TMDB
            poster_url = self.tmdb_client.get_movie_poster(title, year)
            if not poster_url:
                logger.warning(f"No poster found for movie: {title}")
                return False
            
            # Download and prepare thumbnail
            thumbnail_path = self._prepare_thumbnail(title, poster_url)
            if not thumbnail_path:
                return False
            
            # Embed thumbnail using FFmpeg
            return self._embed_with_ffmpeg(movie_path, thumbnail_path, backup)
            
        except Exception as e:
            logger.error(f"Failed to embed thumbnail for {title}: {e}")
            return False
    
    def _prepare_thumbnail(self, title: str, poster_url: str) -> Optional[Path]:
        """
        Download and prepare thumbnail image.
        
        Args:
            title: Movie title
            poster_url: URL to poster image
            
        Returns:
            Path to prepared thumbnail or None if failed
        """
        try:
            safe_title = get_safe_filename(title)
            thumbnail_path = self.thumbnail_cache_dir / f"{safe_title}_thumb.jpg"
            
            # Check if thumbnail is already cached
            if thumbnail_path.exists():
                logger.debug(f"Using cached thumbnail: {thumbnail_path}")
                return thumbnail_path
            
            # Download poster image
            poster_image = download_image(poster_url)
            if not poster_image:
                return None
            
            # Resize for thumbnail embedding
            thumbnail_image = resize_for_thumbnail(poster_image, (400, 600))
            
            # Save thumbnail
            thumbnail_image.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
            
            logger.debug(f"Created thumbnail: {thumbnail_path}")
            return thumbnail_path
            
        except Exception as e:
            logger.error(f"Failed to prepare thumbnail for {title}: {e}")
            return None
    
    def _embed_with_ffmpeg(self, video_path: Path, thumbnail_path: Path, backup: bool = True) -> bool:
        """
        Use FFmpeg to embed thumbnail into video file.
        
        Args:
            video_path: Path to video file
            thumbnail_path: Path to thumbnail image
            backup: Whether to create backup
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup if requested
            if backup:
                backup_path = video_path.with_suffix(f".backup{video_path.suffix}")
                if not backup_path.exists():
                    shutil.copy2(video_path, backup_path)
                    logger.debug(f"Created backup: {backup_path}")
            
            # Create temporary output file
            temp_output = video_path.with_suffix(f".temp{video_path.suffix}")
            
            # Build FFmpeg command
            cmd = [
                str(self.ffmpeg_path),
                "-i", str(video_path),          # Input video
                "-i", str(thumbnail_path),      # Input thumbnail
                "-map", "0",                    # Map all streams from first input
                "-map", "1",                    # Map thumbnail from second input
                "-c", "copy",                   # Copy streams without re-encoding
                "-c:v:1", "mjpeg",             # Encode thumbnail as MJPEG
                "-disposition:v:1", "attached_pic",  # Mark as attached picture
                "-y",                           # Overwrite output file
                str(temp_output)
            ]
            
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg failed: {result.stderr}")
                if temp_output.exists():
                    temp_output.unlink()
                return False
            
            # Replace original file with new one
            if temp_output.exists():
                video_path.unlink()
                temp_output.rename(video_path)
                logger.info(f"Successfully embedded thumbnail in: {video_path}")
                return True
            else:
                logger.error("FFmpeg output file not created")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg operation timed out")
            return False
        except Exception as e:
            logger.error(f"FFmpeg embedding failed: {e}")
            return False
    
    def has_embedded_thumbnail(self, video_path: Path) -> bool:
        """
        Check if video file already has an embedded thumbnail.
        
        Args:
            video_path: Path to video file
            
        Returns:
            True if has thumbnail, False otherwise
        """
        if not self.ffmpeg_path or not is_video_file(video_path):
            return False
        
        try:
            cmd = [
                str(self.ffmpeg_path),
                "-i", str(video_path),
                "-f", "null", "-"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check for attached_pic in the output
            return "attached_pic" in result.stderr.lower()
            
        except Exception as e:
            logger.debug(f"Failed to check for embedded thumbnail: {e}")
            return False
    
    def batch_embed_thumbnails(self, movies: List[Dict[str, Any]], progress_callback=None) -> Dict[str, int]:
        """
        Embed thumbnails for multiple movies in batch.
        
        Args:
            movies: List of movie dictionaries
            progress_callback: Callback for progress updates
            
        Returns:
            Dictionary with success/failure counts
        """
        total = len(movies)
        successful = 0
        failed = 0
        skipped = 0
        
        logger.info(f"Starting batch thumbnail embedding for {total} movies")
        
        for i, movie in enumerate(movies):
            try:
                movie_path = movie['path']
                title = movie['title']
                year = movie.get('year')
                
                # Skip if already has thumbnail
                if self.has_embedded_thumbnail(movie_path):
                    logger.debug(f"Movie already has thumbnail: {title}")
                    skipped += 1
                else:
                    success = self.embed_movie_thumbnail(movie_path, title, year)
                    if success:
                        successful += 1
                    else:
                        failed += 1
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(i + 1, total, title, success if not self.has_embedded_thumbnail(movie_path) else None)
                    
            except Exception as e:
                logger.error(f"Error processing {movie.get('title', 'unknown')}: {e}")
                failed += 1
        
        result = {
            'total': total,
            'successful': successful,
            'failed': failed,
            'skipped': skipped
        }
        
        logger.info(f"Batch embedding complete: {successful}/{total} successful, {skipped} skipped")
        return result
    
    def extract_thumbnail(self, video_path: Path, output_path: Path) -> bool:
        """
        Extract embedded thumbnail from video file.
        
        Args:
            video_path: Path to video file
            output_path: Path to save extracted thumbnail
            
        Returns:
            True if successful, False otherwise
        """
        if not self.ffmpeg_path:
            return False
        
        try:
            cmd = [
                str(self.ffmpeg_path),
                "-i", str(video_path),
                "-an", "-vcodec", "copy",
                "-f", "image2",
                "-y",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            return result.returncode == 0 and output_path.exists()
            
        except Exception as e:
            logger.error(f"Failed to extract thumbnail: {e}")
            return False
