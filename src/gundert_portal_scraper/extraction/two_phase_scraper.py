"""
Two-phase content scraper with download and processing phases.

This implements the proper SPA extraction architecture:
1. Download Phase: Connect once, download entire content, cache it
2. Processing Phase: Extract pages from cached content without browser
"""

import time
from typing import Optional, List
from bs4 import BeautifulSoup

from ..core.connector import GundertPortalConnector
from ..core.cache import RawContentCache
from ..storage.schemas import BookStorage, BookMetadata, PageContent


class TwoPhaseContentScraper:
    """
    Two-phase content scraper for SPA extraction.
    
    Phase 1 (Download): Load SPA once, extract and cache entire content
    Phase 2 (Processing): Parse cached content to extract individual pages
    """
    
    def __init__(
        self,
        connector: GundertPortalConnector,
        cache_dir: str = "./cache",
        force_redownload: bool = False
    ):
        """
        Initialize two-phase scraper.
        
        Args:
            connector: GundertPortalConnector instance
            cache_dir: Directory for caching content
            force_redownload: Force fresh download even if cached
        """
        self.connector = connector
        self.cache = RawContentCache(cache_dir)
        self.force_redownload = force_redownload
        self.book_id = connector.book_id.book_id
    
    def scrape_full_book(
        self,
        start_page: int = 1,
        end_page: Optional[int] = None,
        max_pages: int = 999
    ) -> BookStorage:
        """
        Scrape entire book using two-phase approach.
        
        Args:
            start_page: Starting page number
            end_page: Ending page number (None = all)
            max_pages: Maximum pages to prevent runaway
            
        Returns:
            BookStorage with extracted content
        """
        print(f"🔍 Starting two-phase extraction for {self.book_id}")
        
        # Phase 1: Download (or load from cache)
        cached_content = self._download_phase()
        
        # Phase 2: Process cached content
        book_storage = self._processing_phase(
            cached_content,
            start_page=start_page,
            end_page=end_page,
            max_pages=max_pages
        )
        
        return book_storage
    
    def _download_phase(self) -> dict:
        """
        Phase 1: Download entire SPA content.
        
        Returns:
            Dict with 'content' (HTML) and 'metadata'
        """
        # Check cache first
        if not self.force_redownload and self.cache.is_cached(self.book_id):
            print(f"📦 Loading from cache: {self.book_id}")
            cached = self.cache.load(self.book_id)
            if cached:
                print(f"✅ Cache loaded (cached at: {cached.get('cached_at', 'unknown')})")
                return cached
        
        # Download fresh content
        print(f"🌐 Downloading content from portal...")
        
        # Navigate to book
        self.connector.navigate_to_book(1)
        
        # Wait for content to load
        time.sleep(3)
        
        # Extract entire page source (includes embedded TEI XML)
        page_source = self.connector.get_page_source()
        
        # Extract basic metadata
        metadata = self._extract_basic_metadata()
        
        # Cache the content
        print(f"💾 Caching content for future use...")
        self.cache.save(self.book_id, page_source, metadata)
        
        print(f"✅ Download phase complete")
        
        return {
            'content': page_source,
            'metadata': metadata
        }
    
    def _processing_phase(
        self,
        cached_content: dict,
        start_page: int,
        end_page: Optional[int],
        max_pages: int
    ) -> BookStorage:
        """
        Phase 2: Process cached content to extract pages.
        
        Args:
            cached_content: Dict with 'content' and 'metadata'
            start_page: Starting page number
            end_page: Ending page number
            max_pages: Maximum pages
            
        Returns:
            BookStorage with extracted pages
        """
        print(f"\n📖 Processing cached content...")
        
        html_content = cached_content['content']
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the TEI transcript container
        transcript_div = soup.find('div', id='transcript-content')
        
        if not transcript_div:
            print("⚠️  Warning: No transcript content found in cached HTML")
            return self._create_empty_book()
        
        # Find all surface elements (pages)
        surfaces = transcript_div.find_all('surface')
        total_pages = len(surfaces)
        
        print(f"📄 Found {total_pages} pages in manuscript")
        
        # Determine page range
        if end_page is None:
            end_page = min(total_pages, max_pages)
        
        end_page = min(end_page, total_pages)
        
        # Extract pages
        pages = []
        extraction_errors = 0
        
        print(f"🔄 Extracting pages {start_page} to {end_page}...")
        
        for page_num in range(start_page, end_page + 1):
            try:
                # Find the surface element for this page
                surface = self._find_surface_by_number(surfaces, page_num)
                
                if surface:
                    page_content = self._extract_page_from_surface(surface, page_num)
                    pages.append(page_content)
                    print(f"  ✓ Page {page_num}: {len(page_content.lines)} lines", end="\r")
                else:
                    # Page not found
                    pages.append(PageContent(
                        page_number=page_num,
                        lines=[],
                        full_text="",
                        confidence=0.0,
                        notes=[f"Surface element not found for page {page_num}"]
                    ))
                    extraction_errors += 1
                    
            except Exception as e:
                print(f"\n⚠️  Error processing page {page_num}: {e}")
                extraction_errors += 1
                pages.append(PageContent(
                    page_number=page_num,
                    lines=[],
                    full_text="",
                    confidence=0.0,
                    notes=[f"Extraction error: {str(e)}"]
                ))
        
        print(f"\n✅ Processing complete: {len(pages)} pages extracted")
        
        # Create metadata
        metadata = self._create_metadata(cached_content.get('metadata', {}), total_pages)
        
        # Create BookStorage
        book = BookStorage(metadata=metadata, pages=pages)
        book.statistics["extraction_errors"] = extraction_errors
        book.update_statistics()
        
        return book
    
    def _find_surface_by_number(self, surfaces: list, page_num: int):
        """Find surface element by page number."""
        for surface in surfaces:
            n_attr = surface.get('n')
            if n_attr and int(n_attr) == page_num:
                return surface
        return None
    
    def _extract_page_from_surface(self, surface, page_number: int) -> PageContent:
        """
        Extract content from a surface element.
        
        Args:
            surface: BeautifulSoup element (surface)
            page_number: Page number
            
        Returns:
            PageContent with extracted text and image URL
        """
        lines = []
        
        # Extract all text nodes, preserving structure
        for element in surface.descendants:
            if element.name is None:  # Text node
                text = element.strip()
                if text:
                    lines.append(text)
        
        # Clean up lines
        lines = [line.strip() for line in lines if line.strip()]
        
        # Combine into full text
        full_text = '\n'.join(lines)
        
        # Generate image URL based on OpenDigi pattern
        image_url = self._generate_image_url(page_number)
        
        # Analyze content
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
    
    def _generate_image_url(self, page_number: int) -> str:
        """
        Generate OpenDigi image URL for a page.
        
        OpenDigi uses IIIF Image API with pattern:
        https://opendigi.ub.uni-tuebingen.de/opendigi/image/{book_id}/{book_id}_{page:03d}.jp2/full/full/0/default.jpg
        
        Args:
            page_number: Page number (1-indexed)
            
        Returns:
            Full URL to page image
        """
        return (
            f"https://opendigi.ub.uni-tuebingen.de/opendigi/image/"
            f"{self.book_id}/{self.book_id}_{page_number:03d}.jp2/full/full/0/default.jpg"
        )
    
    def _extract_basic_metadata(self) -> dict:
        """Extract basic metadata from page."""
        try:
            # Try to get title
            title_script = """
            const titleEl = document.querySelector('h1, .title, .book-title');
            return titleEl ? titleEl.textContent.trim() : null;
            """
            title = self.connector.execute_script(title_script)
            
            return {
                'title': title,
                'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception:
            return {}
    
    def _create_metadata(self, cached_metadata: dict, total_pages: int) -> BookMetadata:
        """Create BookMetadata from cached data."""
        return BookMetadata(
            book_id=self.book_id,
            url=self.connector.book_id.url,
            title=cached_metadata.get('title') or self.book_id,
            total_pages=total_pages,
            content_type="unknown",  # Will be detected during transformation
            language="malayalam",
            script="malayalam"
        )
    
    def _create_empty_book(self) -> BookStorage:
        """Create empty BookStorage for error cases."""
        metadata = BookMetadata(
            book_id=self.book_id,
            url=self.connector.book_id.url,
            title=self.book_id,
            total_pages=0
        )
        
        return BookStorage(metadata=metadata, pages=[])
    
    def _detect_verse_numbers(self, text: str) -> bool:
        """Detect if text contains verse numbering."""
        import re
        verse_patterns = [
            r'\b\d+\.\s',  # 1. 2. 3.
            r'\(\d+\)',    # (1) (2) (3)
            r'^\d+\s',     # Line starting with number
        ]
        
        for pattern in verse_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _detect_heading(self, lines: List[str]) -> bool:
        """Detect if page has heading."""
        if not lines:
            return False
        
        first_line = lines[0]
        
        return (
            len(first_line) < 50 and
            first_line[0].isupper() if first_line else False
        )
