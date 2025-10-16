"""
Book identification and URL parsing for OpenDigi portal.

Extracts book identifiers from URLs and provides metadata about the source.
"""

import re
from urllib.parse import urlparse
from typing import Optional


class BookIdentifier:
    """
    Identifies and parses book information from OpenDigi URLs.
    
    Examples:
        >>> book = BookIdentifier("https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a")
        >>> book.book_id
        'GaXXXIV5a'
        >>> book.base_url
        'https://opendigi.ub.uni-tuebingen.de/opendigi'
    """
    
    def __init__(self, url: str):
        """
        Initialize book identifier from URL.
        
        Args:
            url: Full URL to the OpenDigi manuscript page
            
        Raises:
            ValueError: If URL format is invalid
        """
        self.url = url
        self._parse_url()
    
    def _parse_url(self) -> None:
        """Parse URL and extract book information."""
        parsed = urlparse(self.url)
        
        if 'opendigi' not in parsed.netloc and 'opendigi' not in parsed.path:
            raise ValueError(f"Invalid OpenDigi URL: {self.url}")
        
        # Extract book ID from path (e.g., /opendigi/GaXXXIV5a)
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) < 2:
            raise ValueError(f"Cannot extract book ID from URL: {self.url}")
        
        self.book_id = path_parts[-1]
        self.base_url = f"{parsed.scheme}://{parsed.netloc}/{path_parts[0]}"
        
        # Extract collection identifier if present (e.g., Ga for Gundert Archive)
        collection_match = re.match(r'^([A-Za-z]+)', self.book_id)
        self.collection = collection_match.group(1) if collection_match else None
    
    def get_page_url(self, page_number: Optional[int] = None) -> str:
        """
        Get URL for specific page or base book URL.
        
        Args:
            page_number: Optional page number to navigate to
            
        Returns:
            Full URL to the book or specific page
        """
        base = f"{self.base_url}/{self.book_id}"
        if page_number is not None:
            return f"{base}?page={page_number}"
        return base
    
    def __str__(self) -> str:
        return f"BookIdentifier({self.book_id})"
    
    def __repr__(self) -> str:
        return f"BookIdentifier(url='{self.url}', book_id='{self.book_id}')"
