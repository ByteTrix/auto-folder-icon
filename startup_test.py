#!/usr/bin/env python3
"""
Simple startup test for the Media Folder Icon application.
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_basic_functionality():
    """Test basic application functionality without GUI."""
    print("Testing basic application components...")
    
    try:        # Test configuration
        from config.settings import AppSettings
        settings = AppSettings()
        print(f"✓ Settings loaded: scan_frequency={settings.scan_frequency}h")
        
        # Test logger
        from utils.logger import get_logger
        logger = get_logger("startup_test")
        logger.info("Startup test initiated")
        print("✓ Logger initialized")
        
        # Test API clients (without keys)
        from api.tmdb_client import TMDBClient
        from api.anilist_client import AniListClient
        
        tmdb = TMDBClient("")
        anilist = AniListClient()
        print("✓ API clients initialized")
          # Test core components
        from core.scanner import MediaScanner
        from core.icon_manager import IconManager
        
        scanner = MediaScanner()
        icon_manager = IconManager()
        print("✓ Core components initialized")
        
        print("\n🎉 All basic components working correctly!")
        return True
        
    except Exception as e:
        print(f"✗ Error during basic functionality test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_components():
    """Test GUI components (requires display)."""
    print("\nTesting GUI components...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from config.settings import AppSettings
        
        # Create QApplication instance
        app = QApplication(sys.argv)
          # Test setup dialog
        from ui.setup_dialog import SetupDialog
        settings = AppSettings()
        
        # Create but don't show the dialog
        dialog = SetupDialog()
        print("✓ Setup dialog created")
        
        # Test main window
        from ui.main_window import MainWindow
        main_window = MainWindow(settings)
        print("✓ Main window created")
        
        print("✓ GUI components initialized successfully")
        
        # Clean up
        app.quit()
        return True
        
    except Exception as e:
        print(f"✗ Error during GUI test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run startup tests."""
    print("=" * 60)
    print("Media Folder Icon Application - Startup Test")
    print("=" * 60)
    
    # Test basic functionality first
    if not test_basic_functionality():
        print("\n⚠️ Basic functionality test failed!")
        return 1
    
    # Test GUI components
    if not test_gui_components():
        print("\n⚠️ GUI components test failed!")
        return 1
    
    print("\n" + "=" * 60)
    print("🚀 All startup tests passed! Application is ready to run.")
    print("\nTo start the full application, run:")
    print("python main.py")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
