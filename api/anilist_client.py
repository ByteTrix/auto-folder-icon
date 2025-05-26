"""
AniList API client for fetching anime posters and information.
"""

import logging
import requests
from typing import Optional, Dict, Any, List


logger = logging.getLogger(__name__)


class AniListClient:
    """Client for AniList GraphQL API interactions."""
    
    API_URL = "https://graphql.anilist.co"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AniList client.
        
        Args:
            api_key: Optional AniList API key for authenticated requests
        """
        self.api_key = api_key
        self.session = requests.Session()
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Media-Folder-Icon-Manager/1.0'
        }
        
        # Add authorization header if API key is provided
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
            
        self.session.headers.update(headers)
    
    def test_api_key(self) -> bool:
        """
        Test if the provided API key is valid (if provided).
        
        Returns:
            True if API key is valid or not required, False if invalid
        """
        if not self.api_key:
            # AniList public API doesn't require authentication
            return True
            
        try:
            # Test with a simple query
            query = """
            query {
                Viewer {
                    id
                    name
                }
            }
            """
            
            response = self.session.post(
                self.API_URL,
                json={'query': query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'errors' not in data:
                    logger.info("AniList API key validation successful")
                    return True
                else:
                    logger.error(f"AniList API key validation failed: {data['errors']}")
                    return False
            else:
                logger.error(f"AniList API key test failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"AniList API key test failed: {e}")
            return False
    
    def _make_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Make GraphQL query to AniList.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            
        Returns:
            Query response data or None if failed
        """
        try:
            payload = {
                'query': query,
                'variables': variables or {}
            }
            
            response = self.session.post(self.API_URL, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if 'errors' in data:
                logger.error(f"AniList API errors: {data['errors']}")
                return None
            
            return data.get('data')
            
        except Exception as e:
            logger.error(f"AniList API request failed: {e}")
            return None
    
    def search_anime(self, title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Search for anime by title.
        
        Args:
            title: Anime title
            year: Season year (optional)
            
        Returns:
            Anime data or None if not found
        """
        query = '''
        query ($search: String, $seasonYear: Int) {
            Media (search: $search, type: ANIME, seasonYear: $seasonYear) {
                id
                title {
                    romaji
                    english
                    native
                }
                seasonYear
                format
                episodes
                coverImage {
                    extraLarge
                    large
                    medium
                }
                bannerImage
                description
                genres
                averageScore
            }
        }        '''
        
        variables: Dict[str, Any] = {'search': title}
        if year:
            variables['seasonYear'] = year
        
        data = self._make_query(query, variables)
        if not data or not data.get('Media'):
            return None
        
        result = data['Media']
        title_info = result.get('title', {})
        display_title = (title_info.get('english') or 
                        title_info.get('romaji') or 
                        title_info.get('native', title))
        
        logger.info(f"Found anime: {display_title} ({result.get('seasonYear', 'Unknown')})")
        return result
    
    def get_anime_poster(self, title: str, year: Optional[int] = None) -> Optional[str]:
        """
        Get anime poster/cover URL.
        
        Args:
            title: Anime title
            year: Season year (optional)
            
        Returns:
            Poster URL or None if not found
        """
        anime = self.search_anime(title, year)
        if not anime:
            return None
        
        cover_image = anime.get('coverImage', {})
        # Try to get the best quality image
        poster_url = (cover_image.get('extraLarge') or 
                     cover_image.get('large') or 
                     cover_image.get('medium'))
        
        return poster_url
    
    def search_multiple_anime(self, titles: List[str]) -> List[Dict[str, Any]]:
        """
        Search for multiple anime titles efficiently.
        
        Args:
            titles: List of anime titles to search
            
        Returns:
            List of anime data dictionaries
        """
        results = []
        
        for title in titles:
            anime = self.search_anime(title)
            if anime:
                results.append({
                    'title': title,
                    'anime_data': anime,
                    'poster_url': self.get_anime_poster(title)
                })
        
        return results
    
    def get_trending_anime(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get trending anime for reference/testing.
        
        Args:
            limit: Number of anime to return
            
        Returns:
            List of trending anime
        """
        query = '''
        query ($page: Int, $perPage: Int) {
            Page (page: $page, perPage: $perPage) {
                media (type: ANIME, sort: TRENDING_DESC) {
                    id
                    title {
                        romaji
                        english
                        native
                    }
                    seasonYear
                    coverImage {
                        large
                        medium
                    }
                    averageScore
                }
            }
        }
        '''
        
        variables = {
            'page': 1,
            'perPage': limit
        }
        
        data = self._make_query(query, variables)
        if not data or not data.get('Page', {}).get('media'):
            return []
        
        return data['Page']['media']
    
    def is_likely_anime(self, title: str) -> bool:
        """
        Check if a title is likely to be anime based on search results.
        
        Args:
            title: Title to check
            
        Returns:
            True if likely anime, False otherwise
        """
        anime = self.search_anime(title)
        if not anime:
            return False
        
        # Check if the result looks like a match
        anime_titles = anime.get('title', {})
        search_terms = title.lower().split()
        
        for anime_title in anime_titles.values():
            if anime_title:
                anime_words = anime_title.lower().split()
                # If most words match, it's likely the same anime
                matches = sum(1 for word in search_terms if any(word in anime_word for anime_word in anime_words))
                if matches >= len(search_terms) * 0.7:  # 70% match threshold
                    return True
        
        return False
