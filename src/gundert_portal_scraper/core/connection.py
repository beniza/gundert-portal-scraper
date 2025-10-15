"""Universal connector for Gundert Portal books."""

import time
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# Selenium imports (optional)
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from .book_identifier import BookIdentifier
from .exceptions import (
    BookNotFoundError, ConnectionError, PageNotFoundError, 
    TranscriptNotAvailableError, InvalidBookURLError
)

logger = logging.getLogger(__name__)


class GundertPortalConnector:
    """Universal connector for any Gundert Portal book."""
    
    def __init__(self, book_url_or_id: str, use_selenium: bool = True, timeout: int = 30):
        """Initialize the connector.
        
        Args:
            book_url_or_id: Either a full Gundert Portal URL or book ID
            use_selenium: Whether to use Selenium for dynamic content
            timeout: Request/wait timeout in seconds
        """
        self.book_identifier = BookIdentifier(book_url_or_id)
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.timeout = timeout
        self.driver = None
        self._book_info = None
        self._page_count = None
        
        if not self.use_selenium:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'GundertPortalScraper/2.0.0 (Research Tool)'
            })
        
        logger.info(f"Initialized connector for book: {self.book_identifier}")
    
    def __enter__(self):
        """Context manager entry."""
        if self.use_selenium:
            self.setup_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def setup_driver(self) -> None:
        """Set up Selenium WebDriver."""
        if not SELENIUM_AVAILABLE:
            raise ConnectionError("", "Selenium is not available but use_selenium=True")
        
        if self.driver:
            return
        
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=GundertPortalScraper/2.0.0 (Research Tool)')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            
            logger.info("Selenium WebDriver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise ConnectionError("", f"WebDriver setup failed: {str(e)}")
    
    def close(self) -> None:
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
    
    def validate_book_access(self) -> bool:
        """Validate that the book is accessible.
        
        Returns:
            True if book is accessible
            
        Raises:
            BookNotFoundError: If book cannot be accessed
            ConnectionError: If connection fails
        """
        try:
            book_url = self.book_identifier.generate_book_url()
            
            if self.use_selenium:
                self._validate_with_selenium(book_url)
            else:
                self._validate_with_requests(book_url)
            
            logger.info(f"Book validation successful: {self.book_identifier.book_id}")
            return True
            
        except Exception as e:
            if isinstance(e, (BookNotFoundError, ConnectionError)):
                raise
            else:
                raise BookNotFoundError(self.book_identifier.book_id, f"Validation failed: {str(e)}")
    
    def _validate_with_selenium(self, book_url: str) -> None:
        """Validate book access using Selenium."""
        if not self.driver:
            self.setup_driver()
        
        try:
            self.driver.get(book_url)
            
            # Wait for page to load and check for error indicators
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Check for common error indicators
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            if self._has_error_indicators(soup):
                raise BookNotFoundError(self.book_identifier.book_id, "Book page contains error indicators")
            
        except TimeoutException:
            raise ConnectionError(book_url, "Page load timeout")
        except Exception as e:
            raise ConnectionError(book_url, f"Selenium validation failed: {str(e)}")
    
    def _validate_with_requests(self, book_url: str) -> None:
        """Validate book access using requests."""
        try:
            response = self.session.get(book_url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            if self._has_error_indicators(soup):
                raise BookNotFoundError(self.book_identifier.book_id, "Book page contains error indicators")
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(book_url, f"HTTP request failed: {str(e)}")
    
    def _has_error_indicators(self, soup: BeautifulSoup) -> bool:
        """Check if page contains error indicators."""
        error_indicators = [
            'not found', '404', 'error', 'nicht gefunden', 
            'access denied', 'forbidden', 'unavailable'
        ]
        
        page_text = soup.get_text().lower()
        return any(indicator in page_text for indicator in error_indicators)
    
    def get_page_count(self) -> int:
        """Get the total number of pages in the book.
        
        Returns:
            Total page count
            
        Raises:
            ConnectionError: If page count cannot be determined
        """
        if self._page_count is not None:
            return self._page_count
        
        try:
            if self.use_selenium:
                self._page_count = self._get_page_count_selenium()
            else:
                self._page_count = self._get_page_count_requests()
            
            logger.info(f"Detected page count: {self._page_count}")
            return self._page_count
            
        except Exception as e:
            raise ConnectionError("", f"Failed to get page count: {str(e)}")
    
    def _get_page_count_selenium(self) -> int:
        """Get page count using Selenium."""
        if not self.driver:
            self.setup_driver()
        
        book_url = self.book_identifier.generate_book_url()
        self.driver.get(book_url)
        
        # Wait for page to load
        WebDriverWait(self.driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Look for page count indicators in various formats
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        return self._extract_page_count_from_soup(soup)
    
    def _get_page_count_requests(self) -> int:
        """Get page count using requests."""
        book_url = self.book_identifier.generate_book_url()
        response = self.session.get(book_url, timeout=self.timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        return self._extract_page_count_from_soup(soup)
    
    def _extract_page_count_from_soup(self, soup: BeautifulSoup) -> int:
        """Extract page count from page HTML."""
        # Common selectors for page count
        page_count_selectors = [
            '.page-count', '.total-pages', '#pageCount',
            '.pagination-info', '.page-info'
        ]
        
        for selector in page_count_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text()
                page_count = self._extract_number_from_text(text)
                if page_count:
                    return page_count
        
        # Look for pagination elements
        pagination_elements = soup.select('a[href*="p="], a[href*="page="]')
        if pagination_elements:
            max_page = 0
            for elem in pagination_elements:
                href = elem.get('href', '')
                page_num = self._extract_page_from_url(href)
                if page_num > max_page:
                    max_page = page_num
            if max_page > 0:
                return max_page
        
        # Default fallback - try to access high page numbers
        return self._probe_max_page()
    
    def _extract_number_from_text(self, text: str) -> Optional[int]:
        """Extract a number from text."""
        import re
        numbers = re.findall(r'\d+', text)
        return int(numbers[-1]) if numbers else None
    
    def _extract_page_from_url(self, url: str) -> int:
        """Extract page number from URL."""
        import re
        matches = re.findall(r'[p=](\d+)', url)
        return int(matches[-1]) if matches else 0
    
    def _probe_max_page(self) -> int:
        """Probe to find maximum page number."""
        # Binary search approach to find max page
        low, high = 1, 1000  # Reasonable upper bound
        
        while low <= high:
            mid = (low + high) // 2
            if self._page_exists(mid):
                low = mid + 1
            else:
                high = mid - 1
        
        return high if high > 0 else 100  # Fallback
    
    def _page_exists(self, page_number: int) -> bool:
        """Check if a page exists."""
        try:
            page_url = self.book_identifier.generate_page_url(page_number)
            
            if self.use_selenium:
                self.driver.get(page_url)
                time.sleep(1)  # Brief wait
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            else:
                response = self.session.get(page_url, timeout=5)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
            
            return not self._has_error_indicators(soup)
            
        except Exception:
            return False
    
    def navigate_to_page(self, page_number: int, tab: str = "view") -> str:
        """Navigate to a specific page and tab.
        
        Args:
            page_number: Page number (1-based)
            tab: Tab name (view, transcript, info)
            
        Returns:
            URL of the navigated page
            
        Raises:
            PageNotFoundError: If page doesn't exist
            ConnectionError: If navigation fails
        """
        if page_number < 1:
            raise PageNotFoundError(page_number, self.book_identifier.book_id, "Invalid page number")
        
        try:
            page_url = self.book_identifier.generate_page_url(page_number, tab)
            
            if self.use_selenium:
                if not self.driver:
                    self.setup_driver()
                self.driver.get(page_url)
                
                # Wait for page to load
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            
            logger.info(f"Navigated to page {page_number}, tab {tab}")
            return page_url
            
        except Exception as e:
            raise ConnectionError(page_url, f"Navigation failed: {str(e)}")
    
    def get_available_tabs(self) -> List[str]:
        """Get list of available tabs for the book.
        
        Returns:
            List of available tab names
        """
        # Standard tabs - implementation would detect available tabs dynamically
        standard_tabs = ['info', 'view', 'transcript']
        
        # TODO: Implement dynamic tab detection
        return standard_tabs
    
    def check_transcript_availability(self) -> bool:
        """Check if transcript is available for this book.
        
        Returns:
            True if transcript is available
        """
        try:
            # Navigate to first page transcript tab
            self.navigate_to_page(1, "transcript")
            
            if self.use_selenium:
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            else:
                transcript_url = self.book_identifier.generate_page_url(1, "transcript")
                response = self.session.get(transcript_url, timeout=self.timeout)
                soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for transcript content indicators
            transcript_indicators = [
                '.transcript', '.transcription', '#transcript-content',
                '.text-content', '.page-text'
            ]
            
            for selector in transcript_indicators:
                if soup.select_one(selector):
                    return True
            
            # Check for empty/unavailable indicators
            unavailable_text = soup.get_text().lower()
            if any(phrase in unavailable_text for phrase in ['no transcript', 'nicht verfügbar', 'not available']):
                return False
            
            return False
            
        except Exception as e:
            logger.warning(f"Could not check transcript availability: {e}")
            return False
    
    def get_current_page_source(self) -> str:
        """Get the current page source.
        
        Returns:
            HTML source of current page
            
        Raises:
            ConnectionError: If no page is loaded
        """
        if self.use_selenium:
            if not self.driver:
                raise ConnectionError("", "No page loaded - driver not initialized")
            return self.driver.page_source
        else:
            raise ConnectionError("", "Cannot get current page source without Selenium")
    
    def wait_for_content_load(self, timeout: int = 15) -> bool:
        """Wait for page content to load completely.
        
        Args:
            timeout: Wait timeout in seconds
            
        Returns:
            True if content loaded successfully
        """
        if not self.use_selenium or not self.driver:
            return True  # Assume loaded for requests-based access
        
        try:
            # Wait for general page load
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Wait for any loading indicators to disappear
            try:
                WebDriverWait(self.driver, 5).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".loading, .spinner, .load-indicator"))
                )
            except TimeoutException:
                pass  # No loading indicators found, continue
            
            # For OpenDigi, wait for substantial content to load (dynamic content)
            if self.book_identifier.portal_type == 'opendigi':
                try:
                    # Wait for page to have substantial content (indicates dynamic loading is complete)
                    WebDriverWait(self.driver, timeout).until(
                        lambda d: len(d.page_source) > 100000  # Wait for substantial HTML
                    )
                    
                    # Additional wait for Malayalam content to appear
                    import time
                    time.sleep(3)  # Give extra time for dynamic content
                    
                except TimeoutException:
                    logger.warning("OpenDigi content may not be fully loaded")
            
            return True
            
        except TimeoutException:
            logger.warning(f"Content load timeout after {timeout} seconds")
            return False
    
    def get_book_info(self) -> Dict[str, str]:
        """Get comprehensive book information.
        
        Returns:
            Dictionary with book details and connection info
        """
        info = self.book_identifier.get_info()
        info.update({
            'connector_type': 'selenium' if self.use_selenium else 'requests',
            'page_count': str(self.get_page_count()) if self._page_count else 'unknown',
            'transcript_available': str(self.check_transcript_availability()),
            'connection_status': 'active' if (self.driver or self.session) else 'inactive'
        })
        return info
    
    def __str__(self) -> str:
        """String representation."""
        return f"GundertPortalConnector({self.book_identifier.book_id})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"GundertPortalConnector(book_id='{self.book_identifier.book_id}', selenium={self.use_selenium})"