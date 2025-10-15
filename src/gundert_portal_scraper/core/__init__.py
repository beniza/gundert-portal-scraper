"""Core functionality for Gundert Portal Scraper."""

from .book_identifier import BookIdentifier, parse_book_identifier
from .connection import GundertPortalConnector
from .exceptions import (
    GundertPortalError,
    InvalidBookURLError,
    BookNotFoundError,
    PageNotFoundError,
    TranscriptNotAvailableError,
    ConnectionError,
    ExtractionError,
    ValidationError,
    StorageError,
    TransformationError
)

__all__ = [
    'BookIdentifier',
    'parse_book_identifier',
    'GundertPortalConnector',
    'GundertPortalError',
    'InvalidBookURLError',
    'BookNotFoundError',
    'PageNotFoundError',
    'TranscriptNotAvailableError',
    'ConnectionError',
    'ExtractionError',
    'ValidationError',
    'StorageError',
    'TransformationError'
]