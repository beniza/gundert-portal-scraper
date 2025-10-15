"""Custom exceptions for Gundert Portal Scraper."""

from typing import Optional


class GundertPortalError(Exception):
    """Base exception for Gundert Portal scraper errors."""
    pass


class InvalidBookURLError(GundertPortalError):
    """Raised when the provided book URL is invalid."""
    
    def __init__(self, url: str, message: Optional[str] = None):
        self.url = url
        self.message = message or f"Invalid Gundert Portal book URL: {url}"
        super().__init__(self.message)


class BookNotFoundError(GundertPortalError):
    """Raised when a book cannot be found or accessed."""
    
    def __init__(self, book_id: str, message: Optional[str] = None):
        self.book_id = book_id
        self.message = message or f"Book not found: {book_id}"
        super().__init__(self.message)


class PageNotFoundError(GundertPortalError):
    """Raised when a specific page cannot be accessed."""
    
    def __init__(self, page_number: int, book_id: str, message: Optional[str] = None):
        self.page_number = page_number
        self.book_id = book_id
        self.message = message or f"Page {page_number} not found in book {book_id}"
        super().__init__(self.message)


class TranscriptNotAvailableError(GundertPortalError):
    """Raised when transcript is not available for a book or page."""
    
    def __init__(self, book_id: str, page_number: Optional[int] = None, message: Optional[str] = None):
        self.book_id = book_id
        self.page_number = page_number
        if page_number:
            self.message = message or f"Transcript not available for page {page_number} in book {book_id}"
        else:
            self.message = message or f"Transcript not available for book {book_id}"
        super().__init__(self.message)


class ConnectionError(GundertPortalError):
    """Raised when connection to Gundert Portal fails."""
    
    def __init__(self, url: str, message: Optional[str] = None):
        self.url = url
        self.message = message or f"Failed to connect to: {url}"
        super().__init__(self.message)


class ExtractionError(GundertPortalError):
    """Raised when content extraction fails."""
    
    def __init__(self, operation: str, details: Optional[str] = None):
        self.operation = operation
        self.details = details
        self.message = f"Extraction failed during {operation}"
        if details:
            self.message += f": {details}"
        super().__init__(self.message)


class ValidationError(GundertPortalError):
    """Raised when data validation fails."""
    
    def __init__(self, field: str, value: str, message: Optional[str] = None):
        self.field = field
        self.value = value
        self.message = message or f"Validation failed for {field}: {value}"
        super().__init__(self.message)


class StorageError(GundertPortalError):
    """Raised when storage operations fail."""
    
    def __init__(self, operation: str, path: str, message: Optional[str] = None):
        self.operation = operation
        self.path = path
        self.message = message or f"Storage {operation} failed for: {path}"
        super().__init__(self.message)


class TransformationError(GundertPortalError):
    """Raised when format transformation fails."""
    
    def __init__(self, source_format: str, target_format: str, message: Optional[str] = None):
        self.source_format = source_format
        self.target_format = target_format
        self.message = message or f"Failed to transform from {source_format} to {target_format}"
        super().__init__(self.message)