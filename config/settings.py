"""
Application settings and configuration management.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field, validator


class APIKeys(BaseModel):
    """API keys configuration."""
    tmdb: Optional[str] = None
    anilist: Optional[str] = None
    
    def is_tmdb_configured(self) -> bool:
        """Check if TMDB API key is configured."""
        return self.tmdb is not None and len(self.tmdb.strip()) > 0
    
    def is_anilist_configured(self) -> bool:
        """Check if AniList API key is configured."""
        return self.anilist is not None and len(self.anilist.strip()) > 0


class Features(BaseModel):
    """Feature toggles."""
    tv_shows: bool = True
    movies: bool = True
    anime: bool = True


class AppSettings(BaseModel):
    """Main application settings."""
    media_directory: Optional[str] = None
    tray_mode: bool = True
    scan_frequency: int = Field(default=24, ge=1, le=168)  # 1-168 hours
    api_keys: APIKeys = Field(default_factory=APIKeys)
    features: Features = Field(default_factory=Features)
    last_scan: Optional[str] = None
    
    @validator('media_directory')
    def validate_media_directory(cls, v):
        """Validate that media directory exists."""
        if v is not None:
            path = Path(v)
            if not path.exists():
                raise ValueError(f"Media directory does not exist: {v}")
            if not path.is_dir():
                raise ValueError(f"Media directory is not a directory: {v}")
        return v
    
    def is_configured(self) -> bool:
        """Check if the application is properly configured."""
        return (
            self.media_directory is not None and
            self.api_keys.is_tmdb_configured()
        )
    
    @classmethod
    def get_config_path(cls) -> Path:
        """Get the path to the configuration file."""
        config_dir = Path(__file__).parent
        return config_dir / "config.json"
    
    @classmethod
    def load(cls) -> "AppSettings":
        """Load settings from file or create default."""
        config_path = cls.get_config_path()
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return cls(**data)
            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to load config: {e}")
                # Return default settings if loading fails
                return cls()
        
        # Create default settings
        return cls()
    
    def save(self) -> None:
        """Save settings to file."""
        config_path = self.get_config_path()
        
        try:
            # Ensure config directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save settings
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.dict(), f, indent=2, ensure_ascii=False)
            
            logging.getLogger(__name__).info(f"Settings saved to {config_path}")
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to save config: {e}")
            raise
    
    def get_cache_directory(self) -> Path:
        """Get the cache directory path."""
        project_root = Path(__file__).parent.parent
        cache_dir = project_root / "assets" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def get_ffmpeg_path(self) -> Optional[Path]:
        """Get the FFmpeg executable path."""
        project_root = Path(__file__).parent.parent
        ffmpeg_dir = project_root / "assets" / "ffmpeg"
        
        # Look for common FFmpeg executable names
        for name in ["ffmpeg.exe", "ffmpeg"]:
            ffmpeg_path = ffmpeg_dir / name
            if ffmpeg_path.exists():
                return ffmpeg_path
        
        return None
