"""
Connection manager for OpenDigi portal with Selenium support.

Handles both static and SPA (Single Page Application) content extraction.
"""

import time
from typing import Optional
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from .book_identifier import BookIdentifier


class GundertPortalConnector:
    """
    Manages connection to OpenDigi portal with Selenium WebDriver support.
    
    This connector is designed for SPA (Single Page Application) websites
    where content is dynamically loaded via JavaScript.
    """
    
    def __init__(
        self,
        book_identifier: BookIdentifier,
        headless: bool = True,
        page_load_timeout: int = 30,
        implicit_wait: int = 10
    ):
        """
        Initialize portal connector.
        
        Args:
            book_identifier: BookIdentifier with URL information
            headless: Run browser in headless mode
            page_load_timeout: Maximum time to wait for page load
            implicit_wait: Implicit wait time for elements
        """
        self.book_id = book_identifier
        self.headless = headless
        self.page_load_timeout = page_load_timeout
        self.implicit_wait = implicit_wait
        self.driver: Optional[webdriver.Chrome] = None
    
    def connect(self) -> webdriver.Chrome:
        """
        Establish connection and initialize WebDriver.
        
        Returns:
            Selenium WebDriver instance
        """
        if self.driver is not None:
            return self.driver
        
        # Configure Chrome options
        chrome_options = ChromeOptions()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Disable images for faster loading (optional)
        # chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        
        # Initialize WebDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set timeouts
        self.driver.set_page_load_timeout(self.page_load_timeout)
        self.driver.implicitly_wait(self.implicit_wait)
        
        return self.driver
    
    def navigate_to_book(self, page_number: Optional[int] = None) -> None:
        """
        Navigate to book page.
        
        Args:
            page_number: Optional specific page to navigate to
        """
        if self.driver is None:
            self.connect()
        
        url = self.book_id.get_page_url(page_number)
        self.driver.get(url)
        
        # Wait for page to be fully loaded
        time.sleep(2)  # Give SPA time to initialize
    
    def wait_for_element(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: int = 10
    ):
        """
        Wait for element to be present.
        
        Args:
            selector: CSS selector or other locator
            by: Selenium By locator strategy
            timeout: Maximum wait time
            
        Returns:
            WebElement if found
        """
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located((by, selector)))
    
    def execute_script(self, script: str, *args):
        """
        Execute JavaScript in browser context.
        
        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to script
            
        Returns:
            Script return value
        """
        if self.driver is None:
            raise RuntimeError("Driver not connected")
        
        return self.driver.execute_script(script, *args)
    
    def get_page_source(self) -> str:
        """Get current page HTML source."""
        if self.driver is None:
            raise RuntimeError("Driver not connected")
        
        return self.driver.page_source
    
    def close(self) -> None:
        """Close browser and cleanup resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()
