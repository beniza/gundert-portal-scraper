"""Main scraper module for Gundert Bible."""

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class GundertBibleScraper:
    """Main scraper class for extracting content from Gundert Bible."""
    
    def __init__(self, base_url: str = "", timeout: int = 30):
        """Initialize the scraper.
        
        Args:
            base_url: Base URL for the Gundert Bible site
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GundertBibleScraper/0.1.0'
        })
    
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a page.
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object if successful, None otherwise
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_text(self, soup: BeautifulSoup, selector: str) -> List[str]:
        """Extract text from elements matching the selector.
        
        Args:
            soup: BeautifulSoup object
            selector: CSS selector
            
        Returns:
            List of extracted text strings
        """
        elements = soup.select(selector)
        return [elem.get_text(strip=True) for elem in elements if elem.get_text(strip=True)]