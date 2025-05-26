# Media Folder Icon Manager

A Python-based Windows application that automatically sets folder icons for TV Shows and Anime, and embeds poster thumbnails in movie files.

## Features

- 🎬 Automatically scan media directories
- 🖼️ Set custom folder icons for TV Shows and Anime
- 📽️ Embed poster thumbnails in movie files
- 🔧 System tray integration
- ⚙️ Modern configuration GUI
- 📊 Real-time logging and status updates

## Tech Stack

- **GUI**: PySide6 (Qt6 bindings)
- **System Tray**: pystray + Pillow
- **Background Processing**: threading, APScheduler
- **APIs**: TMDB, AniList GraphQL
- **Image Processing**: Pillow
- **Video Processing**: FFmpeg
- **Configuration**: JSON + pydantic

## Installation

1. Clone this repository
2. Install Python 3.8+ 
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Download FFmpeg binary and place in `assets/` folder
5. Run the application:
   ```bash
   python main.py
   ```

## Project Structure

```
media_folder_icon_manager/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── config/
│   ├── __init__.py
│   ├── settings.py        # Configuration models
│   └── config.json        # User settings (generated)
├── ui/
│   ├── __init__.py
│   ├── main_window.py     # Main application window
│   ├── setup_dialog.py    # Initial setup dialog
│   └── tray_manager.py    # System tray functionality
├── core/
│   ├── __init__.py
│   ├── scanner.py         # Directory scanning logic
│   ├── icon_manager.py    # Folder icon operations
│   ├── thumbnail_embedder.py  # Movie thumbnail embedding
│   └── scheduler.py       # Background task scheduling
├── api/
│   ├── __init__.py
│   ├── tmdb_client.py     # TMDB API integration
│   └── anilist_client.py  # AniList API integration
├── utils/
│   ├── __init__.py
│   ├── image_utils.py     # Image processing utilities
│   ├── file_utils.py      # File system utilities
│   └── logger.py          # Logging configuration
├── assets/
│   ├── icons/             # Application icons
│   ├── cache/             # Poster cache directory
│   └── ffmpeg/            # FFmpeg binary (user provided)
└── tests/
    ├── __init__.py
    └── test_*.py          # Unit tests
```

## Configuration

The application stores its configuration in `config/config.json`:

```json
{
  "media_directory": "C:/Media",
  "tray_mode": true,
  "scan_frequency": 24,
  "api_keys": {
    "tmdb": "your_tmdb_api_key"
  },
  "features": {
    "tv_shows": true,
    "movies": true,
    "anime": true
  }
}
```

## Usage

1. **Initial Setup**: Configure your media directory and API keys
2. **Manual Scan**: Use the GUI to trigger immediate scans
3. **Tray Mode**: Run in background with system tray integration
4. **Automatic Scanning**: Schedule periodic scans

## License

MIT License
