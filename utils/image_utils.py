"""
Image processing utilities for poster and icon management.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageOps
import requests
from io import BytesIO


logger = logging.getLogger(__name__)


def download_image(url: str, timeout: int = 30) -> Optional[Image.Image]:
    """
    Download an image from URL and return as PIL Image.
    
    Args:
        url: Image URL to download
        timeout: Request timeout in seconds
        
    Returns:
        PIL Image object or None if failed
    """
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Load image from response content
        image = Image.open(BytesIO(response.content))
        return image
        
    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")
        return None


def create_folder_icon(image: Image.Image, output_path: Path, sizes: Tuple[int, ...] = (16, 32, 48, 64, 128, 256)) -> bool:
    """
    Create a Windows .ico file from a poster image.
    
    Args:
        image: Source PIL Image
        output_path: Path to save the .ico file
        sizes: Icon sizes to include in the .ico file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare images for different sizes
        icon_images = []
        
        for size in sizes:
            # Resize image maintaining aspect ratio
            resized = ImageOps.fit(image, (size, size), Image.Resampling.LANCZOS)
            
            # Convert to RGBA if not already
            if resized.mode != 'RGBA':
                resized = resized.convert('RGBA')
            
            icon_images.append(resized)
        
        # Save as .ico file
        icon_images[0].save(
            output_path,
            format='ICO',
            sizes=[(img.width, img.height) for img in icon_images],
            append_images=icon_images[1:]
        )
        
        logger.info(f"Created folder icon: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create folder icon {output_path}: {e}")
        return False


def resize_for_thumbnail(image: Image.Image, max_size: Tuple[int, int] = (300, 300)) -> Image.Image:
    """
    Resize image for use as video thumbnail.
    
    Args:
        image: Source PIL Image
        max_size: Maximum size (width, height)
        
    Returns:
        Resized PIL Image
    """
    try:
        # Calculate new size maintaining aspect ratio
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB (remove alpha channel if present)
        if image.mode in ('RGBA', 'LA'):
            # Create white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'RGBA':
                background.paste(image, mask=image.split()[-1])  # Use alpha as mask
            else:
                background.paste(image)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        return image
        
    except Exception as e:
        logger.error(f"Failed to resize image for thumbnail: {e}")
        return image


def cache_poster(image: Image.Image, cache_dir: Path, filename: str) -> Optional[Path]:
    """
    Cache a poster image to disk.
    
    Args:
        image: PIL Image to cache
        cache_dir: Cache directory path
        filename: Filename to save as (without extension)
        
    Returns:
        Path to cached image or None if failed
    """
    try:
        # Ensure cache directory exists
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as JPEG
        cache_path = cache_dir / f"{filename}.jpg"
        
        # Convert to RGB if needed
        if image.mode in ('RGBA', 'LA'):
            # Create white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'RGBA':
                background.paste(image, mask=image.split()[-1])
            else:
                background.paste(image)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        image.save(cache_path, 'JPEG', quality=90, optimize=True)
        
        logger.debug(f"Cached poster: {cache_path}")
        return cache_path
        
    except Exception as e:
        logger.error(f"Failed to cache poster {filename}: {e}")
        return None


def get_cached_poster(cache_dir: Path, filename: str) -> Optional[Path]:
    """
    Get a cached poster image if it exists.
    
    Args:
        cache_dir: Cache directory path
        filename: Filename to look for (without extension)
        
    Returns:
        Path to cached image or None if not found
    """
    cache_path = cache_dir / f"{filename}.jpg"
    if cache_path.exists():
        return cache_path
    return None


def clean_cache(cache_dir: Path, max_age_days: int = 30) -> int:
    """
    Clean old cached images.
    
    Args:
        cache_dir: Cache directory path
        max_age_days: Maximum age in days for cached files
        
    Returns:
        Number of files deleted
    """
    try:
        import time
        
        if not cache_dir.exists():
            return 0
        
        max_age_seconds = max_age_days * 24 * 60 * 60
        current_time = time.time()
        deleted_count = 0
        
        for file_path in cache_dir.glob("*.jpg"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old cache file: {file_path}")
        
        logger.info(f"Cleaned {deleted_count} old cache files")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Failed to clean cache: {e}")
        return 0
