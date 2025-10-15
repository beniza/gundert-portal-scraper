"""Book identifier parsing and validation for Gundert Portal."""

import re
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs

from .exceptions import InvalidBookURLError, ValidationError


class BookIdentifier:
    """Handle book ID parsing and validation for Gundert Portal books."""
    
    # Known Gundert Portal URL patterns
    PORTAL_DOMAINS = [
        'gundert-portal.de',
        'opendigi.ub.uni-tuebingen.de'
    ]
    
    # Book ID patterns (shelf marks)
    BOOK_ID_PATTERNS = [
        r'Ga[A-Z]+\d+[a-z]?_?\d*',  # GaXXXIV5a, GaXXXIV5_1
        r'Ga\d+[a-z]?',             # Ga123a
        r'[A-Z]{2,}\d+[a-z]?'       # Other shelf mark patterns
    ]
    
    def __init__(self, url_or_id: str):
        """Initialize with either a URL or book ID.
        
        Args:
            url_or_id: Either a full Gundert Portal URL or a book ID
        """
        self.original_input = url_or_id
        self._book_id = None
        self._base_url = None
        self._portal_type = None
        
        if self._looks_like_url(url_or_id):
            self._parse_url(url_or_id)
        else:
            self._parse_book_id(url_or_id)
    
    def _looks_like_url(self, text: str) -> bool:
        """Check if text looks like a URL."""
        return text.startswith(('http://', 'https://')) or any(domain in text for domain in self.PORTAL_DOMAINS)
    
    def _parse_url(self, url: str) -> None:
        """Parse book ID and metadata from URL."""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Validate domain
            if not any(portal_domain in domain for portal_domain in self.PORTAL_DOMAINS):
                raise InvalidBookURLError(url, f"URL is not from a recognized Gundert Portal domain: {domain}")
            
            # Determine portal type
            if 'gundert-portal.de' in domain:
                self._portal_type = 'gundert_portal'
                self._parse_gundert_portal_url(parsed_url, url)
            elif 'opendigi.ub.uni-tuebingen.de' in domain:
                self._portal_type = 'opendigi'
                self._parse_opendigi_url(parsed_url, url)
            
            self._base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
        except Exception as e:
            raise InvalidBookURLError(url, f"Failed to parse URL: {str(e)}")
    
    def _parse_gundert_portal_url(self, parsed_url, original_url: str) -> None:
        """Parse Gundert Portal specific URL format."""
        # Example: https://gundert-portal.de/book/GaXXXIV5a
        path_parts = parsed_url.path.strip('/').split('/')
        
        if len(path_parts) >= 2 and path_parts[0] == 'book':
            potential_id = path_parts[1]
        else:
            # Try to extract from query parameters
            query_params = parse_qs(parsed_url.query)
            potential_id = query_params.get('id', [None])[0]
        
        if not potential_id:
            raise InvalidBookURLError(original_url, "Could not extract book ID from Gundert Portal URL")
        
        self._validate_and_set_book_id(potential_id, original_url)
    
    def _parse_opendigi_url(self, parsed_url, original_url: str) -> None:
        """Parse OpenDigi specific URL format."""
        # Example: https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a#tab=view&p=1
        path_parts = parsed_url.path.strip('/').split('/')
        
        if 'opendigi' in path_parts:
            opendigi_index = path_parts.index('opendigi')
            if opendigi_index + 1 < len(path_parts):
                potential_id = path_parts[opendigi_index + 1]
            else:
                raise InvalidBookURLError(original_url, "Could not extract book ID from OpenDigi URL")
        else:
            raise InvalidBookURLError(original_url, "Invalid OpenDigi URL format")
        
        self._validate_and_set_book_id(potential_id, original_url)
    
    def _parse_book_id(self, book_id: str) -> None:
        """Parse and validate a standalone book ID."""
        self._validate_and_set_book_id(book_id, book_id)
        self._portal_type = 'unknown'
        self._base_url = None
    
    def _validate_and_set_book_id(self, book_id: str, original_input: str) -> None:
        """Validate book ID against known patterns."""
        # Clean the book ID
        cleaned_id = book_id.strip()
        
        # Check against known patterns
        for pattern in self.BOOK_ID_PATTERNS:
            if re.match(pattern, cleaned_id, re.IGNORECASE):
                self._book_id = cleaned_id
                return
        
        raise InvalidBookURLError(original_input, f"Book ID '{book_id}' does not match known patterns")
    
    @property
    def book_id(self) -> str:
        """Get the validated book ID."""
        return self._book_id
    
    @property
    def base_url(self) -> Optional[str]:
        """Get the base URL of the portal."""
        return self._base_url
    
    @property
    def portal_type(self) -> str:
        """Get the portal type (gundert_portal, opendigi, or unknown)."""
        return self._portal_type
    
    def generate_book_url(self, portal_type: Optional[str] = None) -> str:
        """Generate a book URL for the given portal type.
        
        Args:
            portal_type: Override the detected portal type
            
        Returns:
            Full URL to the book
        """
        target_portal = portal_type or self._portal_type
        
        if target_portal == 'gundert_portal':
            return f"https://gundert-portal.de/book/{self._book_id}"
        elif target_portal == 'opendigi':
            return f"https://opendigi.ub.uni-tuebingen.de/opendigi/{self._book_id}"
        else:
            raise ValidationError('portal_type', target_portal, "Unknown portal type")
    
    def generate_page_url(self, page_number: int, tab: str = 'view', portal_type: Optional[str] = None) -> str:
        """Generate a URL for a specific page and tab.
        
        Args:
            page_number: Page number (1-based)
            tab: Tab name (view, transcript, info)
            portal_type: Override the detected portal type
            
        Returns:
            Full URL to the specific page and tab
        """
        if page_number < 1:
            raise ValidationError('page_number', str(page_number), "Page number must be >= 1")
        
        target_portal = portal_type or self._portal_type
        
        if target_portal == 'gundert_portal':
            return f"https://gundert-portal.de/book/{self._book_id}?page={page_number}&tab={tab}"
        elif target_portal == 'opendigi':
            return f"https://opendigi.ub.uni-tuebingen.de/opendigi/{self._book_id}#tab={tab}&p={page_number}"
        else:
            raise ValidationError('portal_type', target_portal, "Unknown portal type")
    
    def get_info(self) -> Dict[str, str]:
        """Get comprehensive information about the book identifier.
        
        Returns:
            Dictionary with book ID, portal info, and URLs
        """
        return {
            'book_id': self._book_id,
            'original_input': self.original_input,
            'portal_type': self._portal_type,
            'base_url': self._base_url or 'N/A',
            'book_url': self.generate_book_url() if self._portal_type != 'unknown' else 'N/A'
        }
    
    def __str__(self) -> str:
        """String representation of the book identifier."""
        return f"BookIdentifier(id='{self._book_id}', portal='{self._portal_type}')"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"BookIdentifier(book_id='{self._book_id}', portal_type='{self._portal_type}', base_url='{self._base_url}')"


def parse_book_identifier(url_or_id: str) -> BookIdentifier:
    """Convenience function to parse a book identifier.
    
    Args:
        url_or_id: Either a full URL or book ID
        
    Returns:
        BookIdentifier instance
        
    Raises:
        InvalidBookURLError: If the input cannot be parsed
    """
    return BookIdentifier(url_or_id)