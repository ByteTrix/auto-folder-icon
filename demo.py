#!/usr/bin/env python3
"""
Demo script for the Media Folder Icon application.
Creates sample data and demonstrates key features.
"""
import sys
import os
import tempfile
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_demo_media_structure():
    """Create a demo media directory structure for testing."""
    print("Creating demo media directory structure...")
    
    # Create a temporary directory for demo
    demo_dir = Path(tempfile.gettempdir()) / "media_icon_demo"
    demo_dir.mkdir(exist_ok=True)
    
    # Create movie directories
    movies_dir = demo_dir / "Movies"
    movies_dir.mkdir(exist_ok=True)
    
    # Sample movies
    movie_samples = [
        "Inception (2010)",
        "The Dark Knight (2008)",
        "Interstellar (2014)", 
        "The Matrix (1999)",
        "Blade Runner 2049 (2017)"
    ]
    
    for movie in movie_samples:
        movie_dir = movies_dir / movie
        movie_dir.mkdir(exist_ok=True)
        # Create a sample video file
        (movie_dir / f"{movie}.mkv").touch()
        
    # Create TV Shows directories
    tv_dir = demo_dir / "TV Shows"
    tv_dir.mkdir(exist_ok=True)
    
    # Sample TV shows
    tv_samples = [
        ("Breaking Bad", ["S01E01.mkv", "S01E02.mkv", "S02E01.mkv"]),
        ("Stranger Things", ["S01E01.mkv", "S01E02.mkv", "S02E01.mkv"]),
        ("The Office", ["S01E01.mkv", "S01E02.mkv", "S03E01.mkv"]),
        ("Game of Thrones", ["S01E01.mkv", "S01E02.mkv", "S08E06.mkv"])
    ]
    
    for show_name, episodes in tv_samples:
        show_dir = tv_dir / show_name
        show_dir.mkdir(exist_ok=True)
        for episode in episodes:
            (show_dir / episode).touch()
    
    # Create Anime directories
    anime_dir = demo_dir / "Anime"
    anime_dir.mkdir(exist_ok=True)
    
    # Sample anime
    anime_samples = [
        ("Attack on Titan", ["S01E01.mkv", "S01E02.mkv", "S02E01.mkv"]),
        ("Death Note", ["E01.mkv", "E02.mkv", "E37.mkv"]),
        ("One Piece", ["E001.mkv", "E002.mkv", "E1000.mkv"]),
        ("Demon Slayer", ["S01E01.mkv", "S01E02.mkv", "S02E01.mkv"])
    ]
    
    for anime_name, episodes in anime_samples:
        anime_show_dir = anime_dir / anime_name
        anime_show_dir.mkdir(exist_ok=True)
        for episode in episodes:
            (anime_show_dir / episode).touch()
    
    print(f"✓ Demo media structure created at: {demo_dir}")
    return demo_dir

def demonstrate_api_clients():
    """Demonstrate API client functionality."""
    print("\nTesting API Clients...")
    
    try:
        from api.tmdb_client import TMDBClient
        from api.anilist_client import AniListClient
        
        # Test TMDB client (without API key for demo)
        print("  Testing TMDB Client...")
        tmdb = TMDBClient("")
        
        # Test AniList client
        print("  Testing AniList Client...")
        anilist = AniListClient()
        
        print("  ✓ API clients initialized successfully")
        print("  Note: To use TMDB features, configure your API key in settings")
        
    except Exception as e:
        print(f"  ✗ API client error: {e}")

def demonstrate_media_scanning():
    """Demonstrate media scanning functionality."""
    print("\nTesting Media Scanner...")
    
    try:
        from core.scanner import MediaScanner
        
        # Create demo structure
        demo_dir = create_demo_media_structure()
        
        # Initialize scanner
        scanner = MediaScanner()
        
        # Scan the demo directory
        print(f"  Scanning: {demo_dir}")
        result = scanner.scan_directory(demo_dir, detect_anime=False)
        
        print(f"  ✓ Scan Results:")
        print(f"    - Movies: {len(result.movies)}")
        print(f"    - TV Shows: {len(result.tv_shows)}")
        print(f"    - Total Files: {result.total_files}")
        print(f"    - Scan Time: {result.scan_time}")
        
        # Print some found items
        if result.movies:
            print("  Sample Movies Found:")
            for movie in result.movies[:3]:
                print(f"    - {movie.get('title', 'Unknown')}")
        
        if result.tv_shows:
            print("  Sample TV Shows Found:")
            for show in result.tv_shows[:3]:
                print(f"    - {show.get('title', 'Unknown')}")
        
        return demo_dir
        
    except Exception as e:
        print(f"  ✗ Media scanning error: {e}")
        import traceback
        traceback.print_exc()
        return None

def demonstrate_icon_management():
    """Demonstrate icon management functionality."""
    print("\nTesting Icon Manager...")
    
    try:
        from core.icon_manager import IconManager
        from utils.image_utils import ImageProcessor
        
        # Initialize components
        icon_manager = IconManager()
        image_processor = ImageProcessor()
        
        print("  ✓ Icon Manager initialized")
        print("  ✓ Image Processor initialized")
        print("  Note: Icon setting requires Windows and proper folder structure")
        
    except Exception as e:
        print(f"  ✗ Icon management error: {e}")

def demonstrate_settings():
    """Demonstrate settings functionality."""
    print("\nTesting Settings Management...")
    
    try:
        from config.settings import AppSettings
        
        # Create settings
        settings = AppSettings()
        
        print("  ✓ Default settings loaded:")
        print(f"    - Scan Frequency: {settings.scan_frequency} hours")
        print(f"    - Tray Mode: {settings.tray_mode}")
        print(f"    - Features: Movies={settings.features.movies}, TV={settings.features.tv_shows}, Anime={settings.features.anime}")
        
        # Test saving/loading
        config_path = settings.get_config_path()
        print(f"    - Config Path: {config_path}")
        
        if not config_path.exists():
            print("  Creating default configuration file...")
            settings.save()
            print("  ✓ Configuration saved")
        
    except Exception as e:
        print(f"  ✗ Settings error: {e}")

def print_usage_instructions():
    """Print usage instructions for the application."""
    print("\n" + "=" * 60)
    print("MEDIA FOLDER ICON MANAGER - USAGE INSTRUCTIONS")
    print("=" * 60)
    print()
    print("1. FIRST TIME SETUP:")
    print("   python main.py")
    print("   - Configure your media directory")
    print("   - Set TMDB API key (optional but recommended)")
    print("   - Choose enabled features")
    print()
    print("2. SUPPORTED MEDIA STRUCTURE:")
    print("   Movies/")
    print("   ├── Movie Name (Year)/")
    print("   │   └── Movie Name (Year).mkv")
    print("   TV Shows/")
    print("   ├── Show Name/")
    print("   │   ├── S01E01.mkv")
    print("   │   └── S01E02.mkv")
    print("   Anime/")
    print("   ├── Anime Name/")
    print("   │   ├── E01.mkv")
    print("   │   └── E02.mkv")
    print()
    print("3. FEATURES:")
    print("   ✓ Automatic folder icon setting")
    print("   ✓ TMDB metadata integration")
    print("   ✓ AniList anime detection")
    print("   ✓ System tray background mode")
    print("   ✓ Scheduled scanning")
    print("   ✓ FFmpeg thumbnail embedding")
    print()
    print("4. API KEYS (Optional):")
    print("   - TMDB: Get from https://www.themoviedb.org/settings/api")
    print("   - AniList: No key required (GraphQL public API)")
    print()
    print("5. DEPENDENCIES:")
    print("   - FFmpeg: Place ffmpeg.exe in assets/ffmpeg/")
    print("   - Windows: Required for folder icon functionality")
    print("=" * 60)

def main():
    """Run the comprehensive demo."""
    print("=" * 60)
    print("MEDIA FOLDER ICON MANAGER - COMPREHENSIVE DEMO")
    print("=" * 60)
    
    # Test all components
    demonstrate_settings()
    demonstrate_api_clients()
    demo_dir = demonstrate_media_scanning()
    demonstrate_icon_management()
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETED SUCCESSFULLY! 🎉")
    
    if demo_dir:
        print(f"\nDemo media directory created at: {demo_dir}")
        print("You can use this directory to test the application.")
    
    print_usage_instructions()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
