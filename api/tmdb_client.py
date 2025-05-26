"""
TMDB (The Movie Database) API client for fetching movie and TV show posters.
Enhanced with offline mode support for regions where TMDB is blocked.
"""

import logging
import requests
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin


logger = logging.getLogger(__name__)


class TMDBClient:
    """Client for TMDB API interactions with offline mode support."""
    
    BASE_URL = "https://api.themoviedb.org/3/"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"
    
    def __init__(self, api_key: str):
        """
        Initialize TMDB client.
        
        Args:
            api_key: TMDB API key
        """
        self.api_key = api_key
        self.is_available = False
        self.session = None
        
        if api_key:
            self._test_connection()
        else:
            logger.info("No TMDB API key provided - running in offline mode")
    
    def _test_connection(self):
        """Test if TMDB API is accessible."""
        try:
            # Quick connectivity test with minimal timeout
            test_session = requests.Session()
            test_session.params = {'api_key': self.api_key}
            response = test_session.get(
                f"{self.BASE_URL}configuration", 
                timeout=5  # Very short timeout for connection test
            )
            response.raise_for_status()
            
            # If we get here, connection is working
            self.is_available = True
            self.session = requests.Session()
            self.session.params = {'api_key': self.api_key}
            self.session.headers.update({
                'User-Agent': 'Media-Folder-Icon-Manager/1.0'
            })
            logger.info("TMDB API connection successful")
            
        except Exception as e:
            logger.warning(f"TMDB API not accessible: {e}")
            logger.info("Application will continue without TMDB features")
    
    def test_api_key(self) -> bool:
        """
        Test if the provided API key is valid.
        
        Returns:
            True if API key is valid, False otherwise
        """
        try:
            # Use a simple endpoint to test the API key
            response = requests.get(
                f"{self.BASE_URL}configuration",
                params={'api_key': self.api_key},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("TMDB API key validation successful")
                return True
            elif response.status_code == 401:
                logger.error("TMDB API key is invalid")
                return False
            else:
                logger.error(f"TMDB API key test failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"TMDB API key test failed: {e}")
            return False

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Make API request to TMDB.
        
        Args:
            endpoint: API endpoint
            params: Additional parameters
            
        Returns:
            JSON response data or None if failed
        """
        if not self.is_available or not self.session:
            logger.debug(f"TMDB API not available, skipping request to {endpoint}")
            return None
            
        try:
            url = urljoin(self.BASE_URL, endpoint)
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.debug(f"TMDB API request failed for {endpoint}: {e}")
            return None
    
    def search_movie(self, title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Search for a movie by title and year.
        
        Args:
            title: Movie title
            year: Release year (optional)
            
        Returns:
            Movie data or None if not found        """
        if not self.is_available:
            return None
            
        params: Dict[str, Any] = {'query': title}
        if year:
            params['year'] = year
        
        data = self._make_request('search/movie', params)
        if not data or not data.get('results'):
            return None
        
        # Return the first result
        return data['results'][0]
    
    def search_tv_show(self, title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Search for a TV show by title and year.
        
        Args:
            title: TV show title
            year: First air date year (optional)
            
        Returns:
            TV show data or None if not found
        """
        
        if not self.is_available:
            return None
            
        params: Dict[str, Any] = {'query': title}
        if year:
            params['first_air_date_year'] = year
        
        data = self._make_request('search/tv', params)
        if not data or not data.get('results'):
            return None
        
        # Return the first result
        return data['results'][0]
    
    def get_movie_details(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a movie.
        
        Args:
            movie_id: TMDB movie ID
            
        Returns:
            Movie details or None if not found
        """
        if not self.is_available:
            return None
            
        return self._make_request(f'movie/{movie_id}')
    
    def get_tv_show_details(self, tv_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a TV show.
        
        Args:
            tv_id: TMDB TV show ID
            
        Returns:
            TV show details or None if not found
        """
        if not self.is_available:
            return None
            
        return self._make_request(f'tv/{tv_id}')
    
    def get_poster_url(self, poster_path: str, size: str = "w500") -> Optional[str]:
        """
        Get full URL for a poster image.
        
        Args:
            poster_path: Poster path from TMDB response
            size: Image size (w185, w342, w500, w780, original)
            
        Returns:
            Full poster URL or None if not available
        """
        if not poster_path or not self.is_available:
            return None
        
        return f"{self.IMAGE_BASE_URL}{size}{poster_path}"
    
    def download_poster(self, poster_url: str, output_path: str) -> bool:
        """
        Download a poster image.
        
        Args:
            poster_url: Full URL to poster image
            output_path: Local path to save the image
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available or not poster_url:
            return False
            
        try:
            response = self.session.get(poster_url, timeout=30)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded poster: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download poster {poster_url}: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get TMDB client status information.
        
        Returns:
            Status dictionary
        """
        return {
            'available': self.is_available,
            'has_api_key': bool(self.api_key),
            'base_url': self.BASE_URL,
            'mode': 'online' if self.is_available else 'offline'
        }
