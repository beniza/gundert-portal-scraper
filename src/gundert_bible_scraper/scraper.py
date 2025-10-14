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
    
    def extract_transcript(self, soup: BeautifulSoup) -> List[str]:
        """Extract transcript text from Gundert Bible page.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List of transcript lines (Malayalam text)
        """
        # Check if transcript is empty
        empty_div = soup.find('div', {'id': 'transcript-empty'})
        if empty_div and 'hidden' not in empty_div.get('class', []):
            return []
        
        # Extract from transcript content area
        transcript_content = soup.find('div', {'id': 'transcript-content'})
        if not transcript_content:
            return []
        
        # Get all paragraph elements
        paragraphs = transcript_content.find_all('p')
        lines = []
        
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:  # Only add non-empty lines
                lines.append(text)
        
        return lines
    
    def extract_image_info(self, soup: BeautifulSoup) -> Optional[Dict[str, str]]:
        """Extract image information from viewer window.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Dictionary with image info or None if no image found
        """
        viewer_window = soup.find('div', {'id': 'viewer-window'})
        if not viewer_window:
            return None
        
        img = viewer_window.find('img')
        if not img:
            return None
        
        return {
            'url': img.get('src', ''),
            'alt_text': img.get('alt', ''),
            'page_number': img.get('data-page', '')
        }
    
    def build_page_url(self, page_number: int, tab: str = "transcript") -> str:
        """Build URL for a specific page and tab.
        
        Args:
            page_number: Page number to navigate to
            tab: Tab to open (default: transcript)
            
        Returns:
            Complete URL with page and tab parameters
        """
        return f"{self.base_url}#p={page_number}&tab={tab}"
    
    def scrape_page(self, page_number: int) -> Optional[Dict]:
        """Scrape a complete page with transcript and image data.
        
        Args:
            page_number: Page number to scrape
            
        Returns:
            Dictionary with page data or None if failed
        """
        url = self.build_page_url(page_number)
        soup = self.get_page(url)
        
        if not soup:
            return None
        
        return {
            'page_number': page_number,
            'transcript': self.extract_transcript(soup),
            'image': self.extract_image_info(soup)
        }