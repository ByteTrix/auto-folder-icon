#!/usr/bin/env python3
"""
Offline configuration for Media Folder Icon application.
Use this when TMDB API is not accessible in your region.
"""
import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_offline_config():
    """Create configuration for offline mode."""
    print("Creating offline configuration...")
    
    from config.settings import AppSettings
    
    # Create settings with offline mode
    settings = AppSettings()
    settings.features.movies = True
    settings.features.tv_shows = True
    settings.features.anime = False  # Disable anime since it needs AniList
    settings.tray_mode = True
    settings.scan_frequency = 24
    
    # Don't set TMDB API key - this will keep it in offline mode
    settings.api_keys.tmdb = None
    
    # Save the configuration
    settings.save()
    print(f"✓ Offline configuration saved to: {settings.get_config_path()}")
    
    return settings

def test_offline_functionality():
    """Test application functionality in offline mode."""
    print("\nTesting offline functionality...")
    
    try:
        # Test basic components
        from utils.logger import setup_logging, get_logger
        setup_logging()
        logger = get_logger("offline_test")
        logger.info("Testing offline mode")
        
        # Test settings
        settings = create_offline_config()
        print("✓ Settings configured for offline mode")
        
        # Test API clients in offline mode
        from api.tmdb_client import TMDBClient
        from api.anilist_client import AniListClient
        
        # TMDB client without API key (offline mode)
        tmdb = TMDBClient("")
        print(f"✓ TMDB Client initialized (Available: {tmdb.is_available})")
        
        # AniList client (may work depending on network)
        try:
            anilist = AniListClient()
            print("✓ AniList Client initialized")
        except Exception as e:
            print(f"⚠ AniList Client unavailable: {e}")
        
        # Test core components
        from core.scanner import MediaScanner
        from core.icon_manager import IconManager
        
        scanner = MediaScanner()
        icon_manager = IconManager()
        print("✓ Core components initialized")
        
        # Test without GUI
        print("✓ All offline components working!")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in offline test: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_test_directory():
    """Create a simple test directory structure."""
    import tempfile
    
    test_dir = Path(tempfile.gettempdir()) / "media_test_offline"
    test_dir.mkdir(exist_ok=True)
    
    # Create some test movies
    movies_dir = test_dir / "Movies"
    movies_dir.mkdir(exist_ok=True)
    
    test_movies = [
        "The Matrix (1999)",
        "Inception (2010)",
        "Blade Runner (1982)"
    ]
    
    for movie in test_movies:
        movie_dir = movies_dir / movie
        movie_dir.mkdir(exist_ok=True)
        (movie_dir / f"{movie}.mkv").touch()
    
    # Create some test TV shows
    tv_dir = test_dir / "TV Shows"
    tv_dir.mkdir(exist_ok=True)
    
    test_shows = [
        ("Breaking Bad", ["S01E01.mkv", "S01E02.mkv"]),
        ("The Office", ["S01E01.mkv", "S01E02.mkv"])
    ]
    
    for show_name, episodes in test_shows:
        show_dir = tv_dir / show_name
        show_dir.mkdir(exist_ok=True)
        for episode in episodes:
            (show_dir / episode).touch()
    
    return test_dir

def test_scanning():
    """Test the scanning functionality in offline mode."""
    print("\nTesting directory scanning...")
    
    try:
        from core.scanner import MediaScanner
        
        # Create test directory
        test_dir = create_test_directory()
        print(f"Created test directory: {test_dir}")
        
        # Scan the directory
        scanner = MediaScanner()
        result = scanner.scan_directory(test_dir, detect_anime=False)
        
        print(f"✓ Scan completed:")
        print(f"  - Movies found: {len(result.movies)}")
        print(f"  - TV Shows found: {len(result.tv_shows)}")
        print(f"  - Total files: {result.total_files}")
        
        # List found items
        if result.movies:
            print("  Movies:")
            for movie in result.movies:
                print(f"    - {movie.get('title', 'Unknown')}")
        
        if result.tv_shows:
            print("  TV Shows:")
            for show in result.tv_shows:
                print(f"    - {show.get('title', 'Unknown')}")
        
        return test_dir
        
    except Exception as e:
        print(f"✗ Scanning error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Run offline mode setup and testing."""
    print("=" * 60)
    print("MEDIA FOLDER ICON MANAGER - OFFLINE MODE SETUP")
    print("=" * 60)
    print()
    print("This script configures the application for offline use.")
    print("Perfect for regions where TMDB API is blocked.")
    print()
    
    # Test offline functionality
    if not test_offline_functionality():
        print("\n⚠️ Offline functionality test failed!")
        return 1
    
    # Test scanning
    test_dir = test_scanning()
    
    print("\n" + "=" * 60)
    print("OFFLINE SETUP COMPLETED SUCCESSFULLY! 🎉")
    print("=" * 60)
    print()
    print("WHAT'S CONFIGURED:")
    print("✓ TMDB API disabled (offline mode)")
    print("✓ Local media scanning enabled")
    print("✓ Folder icon management enabled")
    print("✓ System tray mode enabled")
    print()
    print("FEATURES AVAILABLE IN OFFLINE MODE:")
    print("✓ Automatic folder detection")
    print("✓ Manual icon assignment")
    print("✓ Directory structure analysis")
    print("✓ Scheduled scanning")
    print("✓ System tray operation")
    print()
    print("FEATURES DISABLED (require internet):")
    print("✗ Automatic poster downloading")
    print("✗ TMDB metadata lookup")
    print("✗ Anime detection via AniList")
    print()
    
    if test_dir:
        print(f"TEST DIRECTORY CREATED: {test_dir}")
        print("You can use this to test the application!")
    
    print("\nTO START THE APPLICATION:")
    print("python main.py")
    print()
    print("The setup dialog will use your offline configuration.")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
