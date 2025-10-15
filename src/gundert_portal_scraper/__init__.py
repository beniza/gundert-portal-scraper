"""Gundert Portal Scraper - Universal extraction system for Gundert Portal books."""

__version__ = "2.0.0"
__author__ = "Gundert Portal Scraper Team"
__description__ = "Universal extraction system for historical texts from Gundert Portal"

from .core import (
    BookIdentifier,
    parse_book_identifier,
    GundertPortalConnector,
    GundertPortalError
)

from .extraction import (
    MetadataExtractor,
    ContentScraper
)

from .preview import SinglePageViewer

from .storage import (
    BookStorageManager,
    BookStorage,
    ContentFormat
)

__all__ = [
    'BookIdentifier',
    'parse_book_identifier', 
    'GundertPortalConnector',
    'GundertPortalError',
    'MetadataExtractor',
    'ContentScraper',
    'SinglePageViewer',
    'BookStorageManager',
    'BookStorage',
    'ContentFormat',
    '__version__'
]