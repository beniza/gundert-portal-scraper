"""
Content scraper for extracting text from OpenDigi SPA pages.

This module handles the extraction of manuscript transcriptions from
the Single Page Application, preserving pagination and line-level structure.
"""

import re
import time
from typing import Optional
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ..core.connector import GundertPortalConnector
from ..storage.schemas import BookStorage, BookMetadata, PageContent


class ContentScraper:
    """
    Extract content from OpenDigi manuscript pages.
    
    This scraper is designed to work with SPA (Single Page Application)
    architecture where content is dynamically loaded.
    """
    
    def __init__(
        self,
        connector: GundertPortalConnector,
        preserve_formatting: bool = True,
        extract_metadata: bool = True
    ):
        """
        Initialize content scraper.
        
        Args:
            connector: Connected GundertPortalConnector instance
            preserve_formatting: Maintain line breaks and formatting
            extract_metadata: Extract book metadata from page
        """
        self.connector = connector
        self.preserve_formatting = preserve_formatting
        self.extract_metadata = extract_metadata
    
    def scrape_full_book(
        self,
        start_page: int = 1,
        end_page: Optional[int] = None,
        max_pages: int = 999
    ) -> BookStorage:
        """
        Scrape entire book or page range.
        
        Args:
            start_page: Starting page number
            end_page: Ending page number (None = scrape all)
            max_pages: Maximum pages to prevent infinite loops
            
        Returns:
            BookStorage with all extracted content
        """
        print(f"🔍 Starting extraction for {self.connector.book_id.book_id}")
        
        # Navigate to first page
        self.connector.navigate_to_book(start_page)
        
        # Extract metadata
        metadata = self._extract_metadata() if self.extract_metadata else self._default_metadata()
        
        # Detect total pages
        total_pages = self._detect_total_pages()
        print(f"📖 Detected {total_pages} pages in manuscript")
        
        if end_page is None:
            end_page = min(total_pages, max_pages)
        
        metadata.total_pages = total_pages
        
        # Extract pages
        pages = []
        extraction_errors = 0
        
        for page_num in range(start_page, end_page + 1):
            try:
                print(f"📄 Extracting page {page_num}/{end_page}...", end="\r")
                page_content = self._extract_page_content(page_num)
                pages.append(page_content)
                
                # Small delay to avoid overwhelming the server
                time.sleep(0.5)
                
            except Exception as e:
                print(f"\n⚠️  Error extracting page {page_num}: {e}")
                extraction_errors += 1
                
                # Add empty page to maintain structure
                pages.append(PageContent(
                    page_number=page_num,
                    lines=[],
                    full_text="",
                    confidence=0.0,
                    notes=[f"Extraction failed: {str(e)}"]
                ))
        
        print(f"\n✅ Extraction complete: {len(pages)} pages")
        
        # Create BookStorage
        book = BookStorage(metadata=metadata, pages=pages)
        book.statistics["extraction_errors"] = extraction_errors
        book.update_statistics()
        
        return book
    
    def _extract_page_content(self, page_number: int) -> PageContent:
        """
        Extract content from a specific page.
        
        Args:
            page_number: Page number to extract
            
        Returns:
            PageContent with extracted text
        """
        # For OpenDigi/Diva viewer, all content is embedded in TEI XML
        # Extract from the embedded TEI structure
        script = f"""
        const transcriptDiv = document.getElementById('transcript-content');
        if (!transcriptDiv) return null;
        
        // Find the surface element for this page
        const surface = transcriptDiv.querySelector('surface[n="{page_number}"]');
        if (!surface) return null;
        
        // Get all text content, preserving structure
        const lines = [];
        const walker = document.createTreeWalker(
            surface,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        let node;
        while (node = walker.nextNode()) {{
            const text = node.textContent.trim();
            if (text) {{
                lines.push(text);
            }}
        }}
        
        return {{
            found: true,
            lines: lines,
            html: surface.innerHTML
        }};
        """
        
        try:
            result = self.connector.execute_script(script)
            
            if result and result.get('found'):
                lines = result.get('lines', [])
                
                # Clean up lines - remove extra whitespace
                lines = [line.strip() for line in lines if line.strip()]
                
                # Extract image URL
                image_url = self._extract_image_url()
                
                # Analyze content
                full_text = '\n'.join(lines)
                has_verse_numbers = self._detect_verse_numbers(full_text)
                has_heading = self._detect_heading(lines)
                
                return PageContent(
                    page_number=page_number,
                    image_url=image_url,
                    lines=lines,
                    full_text=full_text,
                    has_verse_numbers=has_verse_numbers,
                    has_heading=has_heading,
                    confidence=1.0 if lines else 0.0
                )
            else:
                # Fallback: page not found
                return PageContent(
                    page_number=page_number,
                    lines=[],
                    full_text="",
                    confidence=0.0,
                    notes=[f"Surface element not found for page {page_number}"]
                )
                
        except Exception as e:
            return PageContent(
                page_number=page_number,
                lines=[],
                full_text="",
                confidence=0.0,
                notes=[f"Extraction error: {str(e)}"]
            )
    
    def _navigate_to_page(self, page_number: int) -> None:
        """Navigate to specific page in SPA."""
        # Try clicking navigation controls or executing JavaScript
        script = f"""
        // Try to navigate to page {page_number}
        if (window.navigateToPage) {{
            window.navigateToPage({page_number});
        }}
        """
        try:
            self.connector.execute_script(script)
            time.sleep(1)
        except Exception:
            # Fallback: reload with page parameter
            self.connector.navigate_to_book(page_number)
    
    def _detect_total_pages(self) -> int:
        """Detect total number of pages in manuscript."""
        try:
            # For OpenDigi/Diva, count surface elements in TEI XML
            script = """
            const transcriptDiv = document.getElementById('transcript-content');
            if (!transcriptDiv) return 0;
            
            const surfaces = transcriptDiv.querySelectorAll('surface');
            return surfaces.length;
            """
            page_count = self.connector.execute_script(script)
            if page_count and page_count > 0:
                return page_count
            
            # Fallback: Look for page indicator (e.g., "Page 1 of 150")
            page_info_selectors = [
                ".page-info",
                ".pagination-info",
                "[class*='page-count']",
                ".page-indicator"
            ]
            
            for selector in page_info_selectors:
                try:
                    element = self.connector.driver.find_element(By.CSS_SELECTOR, selector)
                    text = element.text
                    
                    # Parse "Page X of Y" or "X / Y"
                    match = re.search(r'of\s+(\d+)|/\s*(\d+)', text, re.IGNORECASE)
                    if match:
                        return int(match.group(1) or match.group(2))
                except NoSuchElementException:
                    continue
            
        except Exception as e:
            print(f"⚠️  Could not detect total pages: {e}")
        
        # Default fallback
        return 100
    
    def _extract_image_url(self) -> Optional[str]:
        """Extract URL of current page image."""
        try:
            # Common image container selectors
            img_selectors = [
                "img.page-image",
                ".image-viewer img",
                "[class*='viewer'] img",
                ".content-image"
            ]
            
            for selector in img_selectors:
                try:
                    img = self.connector.driver.find_element(By.CSS_SELECTOR, selector)
                    if img and img.get_attribute('src'):
                        return img.get_attribute('src')
                except NoSuchElementException:
                    continue
        except Exception:
            pass
        
        return None
    
    def _extract_metadata(self) -> BookMetadata:
        """Extract metadata from page."""
        book_id = self.connector.book_id.book_id
        url = self.connector.book_id.url
        
        # Try to extract title
        title = None
        try:
            title_element = self.connector.driver.find_element(By.CSS_SELECTOR, "h1, .title, .book-title")
            title = title_element.text.strip() if title_element else None
        except NoSuchElementException:
            pass
        
        return BookMetadata(
            book_id=book_id,
            url=url,
            title=title or book_id,
            content_type="unknown",  # Will be detected during transformation
            language="malayalam",
            script="malayalam"
        )
    
    def _default_metadata(self) -> BookMetadata:
        """Create default metadata."""
        return BookMetadata(
            book_id=self.connector.book_id.book_id,
            url=self.connector.book_id.url,
            title=self.connector.book_id.book_id
        )
    
    def _detect_verse_numbers(self, text: str) -> bool:
        """Detect if text contains verse numbering."""
        # Look for patterns like: 1. 2. or (1) (2) or superscript numbers
        verse_patterns = [
            r'\b\d+\.\s',  # 1. 2. 3.
            r'\(\d+\)',    # (1) (2) (3)
            r'^\d+\s',     # Line starting with number
        ]
        
        for pattern in verse_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _detect_heading(self, lines: list[str]) -> bool:
        """Detect if page has heading (first line is likely a heading)."""
        if not lines:
            return False
        
        first_line = lines[0]
        
        # Heuristics for headings
        return (
            len(first_line) < 50 and  # Short
            not any(char.isdigit() for char in first_line) and  # No numbers
            first_line.isupper() or first_line[0].isupper()  # Capitalized
        )
