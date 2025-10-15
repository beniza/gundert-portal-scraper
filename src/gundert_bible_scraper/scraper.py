"""Main scraper module for Gundert Bible."""

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging
import time

# Selenium imports (optional)
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

logger = logging.getLogger(__name__)


class GundertBibleScraper:
    """Main scraper class for extracting content from Gundert Bible."""
    
    def __init__(self, base_url: str = "", timeout: int = 30, use_selenium: bool = False):
        """Initialize the scraper.
        
        Args:
            base_url: Base URL for the Gundert Bible site
            timeout: Request timeout in seconds
            use_selenium: Whether to use Selenium for dynamic content
        """
        self.base_url = base_url
        self.timeout = timeout
        self.use_selenium = use_selenium
        self.driver = None
        
        if not use_selenium:
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
    
    def setup_driver(self):
        """Set up Selenium WebDriver for dynamic content.
        
        Returns:
            WebDriver instance
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not available. Install with: uv add --dev selenium webdriver-manager")
        
        options = Options()
        options.add_argument('--headless')  # Run in background
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Initialize driver with automatic Chrome management
        self.driver = webdriver.Chrome(
            service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
            options=options
        )
        
        self.driver.implicitly_wait(10)
        return self.driver
    
    def get_page_selenium(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a page using Selenium for JavaScript content.
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object if successful, None otherwise
        """
        if not self.driver:
            self.setup_driver()
        
        try:
            self.driver.get(url)
            
            # Wait for content to load
            self.wait_for_transcript_content()
            
            # Get page source after JavaScript execution
            html = self.driver.page_source
            return BeautifulSoup(html, 'html.parser')
            
        except Exception as e:
            logger.error(f"Error fetching {url} with Selenium: {e}")
            return None
    
    def wait_for_transcript_content(self, timeout: int = 15) -> bool:
        """Wait for transcript content to load dynamically.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if content loaded, False if timeout
        """
        try:
            # Wait for either transcript content or empty message
            wait = WebDriverWait(self.driver, timeout)
            
            # Try to find transcript content or empty indicator
            wait.until(
                lambda driver: (
                    driver.find_elements(By.ID, "transcript-content") or
                    driver.find_elements(By.ID, "transcript-empty")
                )
            )
            
            # Additional wait for content to populate
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.warning(f"Timeout waiting for transcript content: {e}")
            return False
    
    def scrape_page_selenium(self, page_number: int) -> Optional[Dict]:
        """Scrape a complete page using Selenium for dynamic content.
        
        Args:
            page_number: Page number to scrape
            
        Returns:
            Dictionary with page data or None if failed
        """
        url = self.build_page_url(page_number)
        soup = self.get_page_selenium(url)
        
        if not soup:
            return None
        
        return {
            'page_number': page_number,
            'transcript': self.extract_transcript(soup),
            'image': self.extract_image_info(soup)
        }
    
    def batch_scrape_pages(self, page_numbers: List[int]) -> List[Dict]:
        """Scrape multiple pages efficiently using Selenium.
        
        Args:
            page_numbers: List of page numbers to scrape
            
        Returns:
            List of page data dictionaries
        """
        if not self.use_selenium:
            raise ValueError("Batch scraping requires Selenium. Set use_selenium=True")
        
        results = []
        
        try:
            if not self.driver:
                self.setup_driver()
            
            for page_num in page_numbers:
                logger.info(f"Scraping page {page_num}...")
                page_data = self.scrape_page_selenium(page_num)
                
                if page_data:
                    results.append(page_data)
                
                # Be respectful - add delay between pages
                time.sleep(1)
        
        finally:
            # Always cleanup
            self.cleanup_driver()
        
        return results
    
    def cleanup_driver(self):
        """Clean up Selenium WebDriver resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None