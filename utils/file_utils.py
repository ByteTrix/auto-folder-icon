"""
File system utilities for media scanning and folder operations.
"""

import os
import re
import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import ctypes
from ctypes import wintypes


logger = logging.getLogger(__name__)


# Windows API constants
SHGFI_ICON = 0x100
SHGFI_ICONLOCATION = 0x1000
SHGetFileInfo = ctypes.windll.shell32.SHGetFileInfoW


def is_video_file(file_path: Path) -> bool:
    """
    Check if a file is a video file based on extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if it's a video file, False otherwise
    """
    video_extensions = {
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ts', '.mts'
    }
    return file_path.suffix.lower() in video_extensions


def extract_year_from_filename(filename: str) -> Optional[int]:
    """
    Extract year from movie filename.
    
    Args:
        filename: Movie filename
        
    Returns:
        Year as integer or None if not found
    """
    # Look for 4-digit year in parentheses or brackets
    year_patterns = [
        r'\((\d{4})\)',  # (2010)
        r'\[(\d{4})\]',  # [2010]
        r'\.(\d{4})\.',  # .2010.
        r'\s(\d{4})\s',  # 2010 
        r'\.(\d{4})$',   # .2010 (at end)
    ]
    
    for pattern in year_patterns:
        match = re.search(pattern, filename)
        if match:
            year = int(match.group(1))
            # Sanity check: reasonable movie year range
            if 1900 <= year <= 2030:
                return year
    
    return None


def clean_title(title: str) -> str:
    """
    Clean movie/TV show title for API searches.
    
    Args:
        title: Raw title string
        
    Returns:
        Cleaned title string
    """
    # Remove year and extra info in parentheses/brackets
    title = re.sub(r'\s*[\(\[].*?[\)\]]', '', title)
    
    # Remove common video quality indicators
    quality_terms = [
        'bluray', 'bdrip', 'dvdrip', 'webrip', 'hdtv', 'hdcam',
        '720p', '1080p', '4k', 'uhd', 'x264', 'x265', 'hevc',
        'aac', 'dts', 'ac3', 'extended', 'unrated', 'directors.cut'
    ]
    
    for term in quality_terms:
        title = re.sub(rf'\b{re.escape(term)}\b', '', title, flags=re.IGNORECASE)
    
    # Clean up extra spaces and dots
    title = re.sub(r'[\.\-_]+', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    
    return title.strip()


def scan_movies(directory: Path) -> List[Dict[str, Any]]:
    """
    Scan directory for movie files.
    
    Args:
        directory: Directory to scan
        
    Returns:
        List of movie information dictionaries
    """
    movies = []
    
    try:
        for file_path in directory.rglob('*'):
            if file_path.is_file() and is_video_file(file_path):
                filename = file_path.stem
                year = extract_year_from_filename(filename)
                title = clean_title(filename)
                
                if title:  # Only add if we could extract a title
                    movies.append({
                        'path': file_path,
                        'filename': filename,
                        'title': title,
                        'year': year,
                        'directory': file_path.parent
                    })
                    
        logger.info(f"Found {len(movies)} movies in {directory}")
        return movies
        
    except Exception as e:
        logger.error(f"Failed to scan movies in {directory}: {e}")
        return []


def scan_tv_shows(directory: Path) -> List[Dict[str, Any]]:
    """
    Scan directory for TV show folders.
    
    Args:
        directory: Directory to scan
        
    Returns:
        List of TV show information dictionaries
    """
    tv_shows = []
    
    try:
        # Look for show directories (containing season folders)
        for show_dir in directory.iterdir():
            if not show_dir.is_dir():
                continue
                
            # Check if this directory contains season folders
            season_folders = []
            for item in show_dir.iterdir():
                if item.is_dir() and re.search(r'season\s*\d+', item.name, re.IGNORECASE):
                    season_folders.append(item)
            
            if season_folders:
                # This looks like a TV show directory
                title = clean_title(show_dir.name)
                tv_shows.append({
                    'path': show_dir,
                    'title': title,
                    'season_folders': season_folders
                })
        
        logger.info(f"Found {len(tv_shows)} TV shows in {directory}")
        return tv_shows
        
    except Exception as e:
        logger.error(f"Failed to scan TV shows in {directory}: {e}")
        return []


def create_desktop_ini(folder_path: Path, icon_path: Path) -> bool:
    """
    Create desktop.ini file to set custom folder icon.
    
    Args:
        folder_path: Path to the folder
        icon_path: Path to the icon file (.ico)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        desktop_ini_path = folder_path / "desktop.ini"
        
        # Create desktop.ini content
        ini_content = f"""[.ShellClassInfo]
IconResource={icon_path.as_posix()},0
[ViewState]
Mode=
Vid=
FolderType=Generic
"""
        
        # Write desktop.ini file
        with open(desktop_ini_path, 'w', encoding='utf-8') as f:
            f.write(ini_content)
        
        # Set file attributes: hidden and system
        ctypes.windll.kernel32.SetFileAttributesW(
            str(desktop_ini_path),
            0x2 | 0x4  # FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
        )
        
        # Set folder attributes: read-only to enable custom icon
        ctypes.windll.kernel32.SetFileAttributesW(
            str(folder_path),
            0x1  # FILE_ATTRIBUTE_READONLY
        )
        
        logger.info(f"Created desktop.ini for {folder_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create desktop.ini for {folder_path}: {e}")
        return False


def refresh_folder_icon(folder_path: Path) -> bool:
    """
    Refresh folder icon in Windows Explorer.
    
    Args:
        folder_path: Path to the folder
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Use SHChangeNotify to refresh the folder
        ctypes.windll.shell32.SHChangeNotify(
            0x8000000,  # SHCNE_ASSOCCHANGED
            0x1000,     # SHCNF_FLUSH
            None,
            None
        )
        
        # Also try to refresh the specific folder
        ctypes.windll.shell32.SHChangeNotify(
            0x40,       # SHCNE_UPDATEDIR
            0x0000,     # SHCNF_PATH
            str(folder_path),
            None
        )
        
        logger.debug(f"Refreshed folder icon for {folder_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to refresh folder icon for {folder_path}: {e}")
        return False


def has_custom_icon(folder_path: Path) -> bool:
    """
    Check if folder already has a custom icon.
    
    Args:
        folder_path: Path to the folder
        
    Returns:
        True if folder has custom icon, False otherwise
    """
    desktop_ini_path = folder_path / "desktop.ini"
    return desktop_ini_path.exists()


def get_safe_filename(title: str) -> str:
    """
    Convert title to safe filename for caching.
    
    Args:
        title: Original title
        
    Returns:
        Safe filename string
    """
    # Remove or replace unsafe characters
    safe_chars = re.sub(r'[<>:"/\\|?*]', '_', title)
    safe_chars = re.sub(r'\s+', '_', safe_chars)
    safe_chars = safe_chars.strip('._')
    
    # Limit length
    if len(safe_chars) > 100:
        safe_chars = safe_chars[:100]
    
    return safe_chars
