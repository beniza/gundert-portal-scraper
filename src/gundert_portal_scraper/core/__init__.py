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
from .cache import RawContentCache, CacheMetadata
from .download_phase import DownloadPhase, DownloadProgress
from .processing_phase import ProcessingPhase, ProcessingProgress
from .two_phase_scraper import TwoPhaseContentScraper, create_two_phase_scraper

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
    'TransformationError',
    'RawContentCache',
    'CacheMetadata',
    'DownloadPhase',
    'DownloadProgress',
    'ProcessingPhase',
    'ProcessingProgress',
    'TwoPhaseContentScraper',
    'create_two_phase_scraper'
]