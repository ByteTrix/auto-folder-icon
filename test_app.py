#!/usr/bin/env python3
"""
Test script to validate the Media Folder Icon application components.
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all modules can be imported without errors."""
    print("Testing imports...")
    
    try:
        # Test config imports
        from config.settings import AppSettings, APISettings, DirectorySettings
        print("✓ Config modules imported successfully")
        
        # Test API clients
        from api.tmdb_client import TMDBClient
        from api.anilist_client import AniListClient
        print("✓ API client modules imported successfully")
        
        # Test core modules
        from core.scanner import MediaScanner
        from core.icon_manager import IconManager
        from core.thumbnail_embedder import ThumbnailEmbedder
        from core.scheduler import TaskScheduler
        print("✓ Core modules imported successfully")
        
        # Test UI modules
        from ui.setup_dialog import SetupDialog
        from ui.main_window import MainWindow
        from ui.tray_manager import TrayManager
        print("✓ UI modules imported successfully")
        
        # Test utility modules
        from utils.logger import get_logger
        from utils.image_utils import ImageProcessor
        from utils.file_utils import FileOperations
        print("✓ Utility modules imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_config():
    """Test configuration loading and validation."""
    print("\nTesting configuration...")
    
    try:
        from config.settings import AppSettings
        
        # Test default settings creation
        settings = AppSettings()
        print(f"✓ Default settings created: {type(settings)}")
        
        # Test some basic validations
        assert settings.directories.scan_interval >= 1, "Scan interval should be at least 1 minute"
        assert settings.api.tmdb_api_key == "", "Default TMDB API key should be empty"
        print("✓ Settings validation passed")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_logger():
    """Test logging functionality."""
    print("\nTesting logger...")
    
    try:
        from utils.logger import get_logger
        
        logger = get_logger("test")
        logger.info("Test log message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        print("✓ Logger working correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Logger test failed: {e}")
        return False

def test_api_clients():
    """Test API client initialization."""
    print("\nTesting API clients...")
    
    try:
        from api.tmdb_client import TMDBClient
        from api.anilist_client import AniListClient
        
        # Test TMDB client (without API key)
        tmdb_client = TMDBClient("")
        print("✓ TMDB client initialized")
        
        # Test AniList client
        anilist_client = AniListClient()
        print("✓ AniList client initialized")
        
        return True
        
    except Exception as e:
        print(f"✗ API client test failed: {e}")
        return False

def test_image_utils():
    """Test image utility functions."""
    print("\nTesting image utilities...")
    
    try:
        from utils.image_utils import ImageProcessor
        
        processor = ImageProcessor()
        print("✓ Image processor initialized")
        
        return True
        
    except Exception as e:
        print(f"✗ Image utilities test failed: {e}")
        return False

def test_file_utils():
    """Test file utility functions."""
    print("\nTesting file utilities...")
    
    try:
        from utils.file_utils import FileOperations
        
        file_ops = FileOperations()
        print("✓ File operations initialized")
        
        return True
        
    except Exception as e:
        print(f"✗ File utilities test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Media Folder Icon Application - Component Tests")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_config,
        test_logger,
        test_api_clients,
        test_image_utils,
        test_file_utils,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test_func.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"Tests completed: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The application components are working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
