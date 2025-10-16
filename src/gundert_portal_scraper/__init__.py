"""
Gundert Portal Scraper - Extract and transform content from OpenDigi manuscripts.

A comprehensive tool for extracting content from Single Page Application (SPA)
manuscript portals and transforming them into various academic and publishing formats.
"""

__version__ = "0.1.0"
__author__ = "Ben"

from .core.book_identifier import BookIdentifier
from .core.connector import GundertPortalConnector
from .extraction.content_scraper import ContentScraper
from .storage.schemas import BookStorage, PageContent, BookMetadata

__all__ = [
    "BookIdentifier",
    "GundertPortalConnector",
    "ContentScraper",
    "BookStorage",
    "PageContent",
    "BookMetadata",
]
