"""Two-phase content scraper integrating download and processing phases."""

import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path

from ..core.cache import RawContentCache
from ..core.download_phase import DownloadPhase, DownloadProgress
from ..core.processing_phase import ProcessingPhase, ProcessingProgress
from ..core.book_identifier import BookIdentifier
from ..core.exceptions import ExtractionError

logger = logging.getLogger(__name__)


class TwoPhaseContentScraper:
    """Content scraper with two-phase architecture: download then process."""
    
    def __init__(self, 
                 cache_dir: Optional[Path] = None,
                 max_download_workers: int = 1,  # WebDriver limitations
                 max_processing_workers: int = 4,
                 preserve_formatting: bool = True):
        """Initialize two-phase scraper.
        
        Args:
            cache_dir: Cache directory for raw content
            max_download_workers: Max concurrent download workers
            max_processing_workers: Max concurrent processing workers
            preserve_formatting: Whether to preserve HTML formatting
        """
        self.cache = RawContentCache(cache_dir)
        self.download_phase = DownloadPhase(self.cache, max_download_workers)
        self.processing_phase = ProcessingPhase(self.cache, max_processing_workers)
        self.preserve_formatting = preserve_formatting
        
        # Progress callbacks
        self.download_progress_callback: Optional[Callable] = None
        self.processing_progress_callback: Optional[Callable] = None
    
    def set_progress_callbacks(self, 
                             download_callback: Optional[Callable] = None,
                             processing_callback: Optional[Callable] = None):
        """Set progress callbacks for both phases."""
        self.download_progress_callback = download_callback
        self.processing_progress_callback = processing_callback
        
        if download_callback:
            self.download_phase.set_progress_callback(download_callback)
        if processing_callback:
            self.processing_phase.set_progress_callback(processing_callback)
    
    def extract_book(self, 
                    book_identifier: BookIdentifier,
                    start_page: int = 1,
                    end_page: Optional[int] = None,
                    force_redownload: bool = False,
                    skip_download: bool = False) -> Dict[str, Any]:
        """Extract complete book with two-phase approach.
        
        Args:
            book_identifier: Book to extract
            start_page: Starting page number
            end_page: Ending page number (None = auto-detect)
            force_redownload: Force redownload even if cached
            skip_download: Skip download phase (process existing cache only)
            
        Returns:
            Complete book data with metadata, pages, and statistics
        """
        book_id = book_identifier.book_id
        logger.info(f"Starting two-phase extraction for book: {book_id}")
        
        extraction_start = datetime.now()
        
        # Phase 1: Download (if not skipped)
        download_result = None
        if not skip_download:
            logger.info("Phase 1: Downloading raw content...")
            
            try:
                download_result = self.download_phase.download_book(
                    book_identifier=book_identifier,
                    start_page=start_page,
                    end_page=end_page,
                    force_redownload=force_redownload
                )
                
                if not download_result['success'] and not download_result.get('from_cache'):
                    raise ExtractionError("download phase", 
                                        f"Download failed: {download_result.get('statistics', {}).get('failed_pages', 'Unknown error')}")
                
                if download_result.get('from_cache'):
                    logger.info("Using existing cache - download phase skipped")
                else:
                    stats = download_result.get('statistics', {})
                    logger.info(f"Download completed: {stats.get('successful_pages', 0)}/{stats.get('total_pages', 0)} pages")
                    
            except Exception as e:
                logger.error(f"Download phase failed: {e}")
                raise ExtractionError("download phase", str(e))
        else:
            logger.info("Download phase skipped - processing existing cache")
        
        # Phase 2: Processing
        logger.info("Phase 2: Processing cached content...")
        
        try:
            book_data = self.processing_phase.process_cached_book(
                book_id=book_id,
                preserve_formatting=self.preserve_formatting
            )
            
            # Add download statistics to final result if available
            if download_result and not download_result.get('from_cache'):
                book_data['download_statistics'] = download_result.get('statistics')
            
            extraction_end = datetime.now()
            total_duration = (extraction_end - extraction_start).total_seconds()
            
            # Update final statistics
            book_data['statistics']['total_extraction_duration_seconds'] = total_duration
            book_data['statistics']['extraction_method'] = 'two_phase'
            
            if download_result:
                book_data['statistics']['used_cache'] = download_result.get('from_cache', False)
            
            logger.info(f"Two-phase extraction completed in {total_duration:.1f}s")
            return book_data
            
        except Exception as e:
            logger.error(f"Processing phase failed: {e}")
            raise ExtractionError("processing phase", str(e))
    
    def check_cache_status(self, book_id: str) -> Dict[str, Any]:
        """Check cache status for a book."""
        return self.download_phase.check_cache_status(book_id)
    
    def clear_cache(self, book_id: str) -> bool:
        """Clear cache for a specific book."""
        return self.cache.clear_cache(book_id)
    
    def list_cached_books(self) -> List[Dict[str, Any]]:
        """List all cached books."""
        return self.cache.list_cached_books()
    
    def get_cache_info(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed cache information for a book."""
        return self.cache.get_cache_info(book_id)
    
    def validate_cache(self, book_id: str) -> tuple[bool, List[str]]:
        """Validate cache integrity for a book."""
        return self.cache.validate_cache(book_id)
    
    # Legacy compatibility methods (delegating to two-phase approach)
    def scrape_full_book(self, start_page: int = 1, end_page: Optional[int] = None, 
                        batch_size: int = 10) -> Dict[str, Any]:
        """Legacy method for backward compatibility."""
        logger.warning("scrape_full_book is deprecated, use extract_book instead")
        
        # This would need a book identifier, but since it's legacy, 
        # we'll need to create one from existing connection if available
        # For now, raise an error directing users to new method
        raise ExtractionError("legacy method", 
                            "scrape_full_book is deprecated. Use TwoPhaseContentScraper.extract_book() instead.")


# Factory function for easy creation
def create_two_phase_scraper(cache_dir: Optional[Path] = None,
                           max_download_workers: int = 1,
                           max_processing_workers: int = 4,
                           preserve_formatting: bool = True) -> TwoPhaseContentScraper:
    """Create a configured two-phase content scraper.
    
    Args:
        cache_dir: Cache directory for raw content
        max_download_workers: Max concurrent download workers
        max_processing_workers: Max concurrent processing workers
        preserve_formatting: Whether to preserve HTML formatting
        
    Returns:
        Configured TwoPhaseContentScraper instance
    """
    return TwoPhaseContentScraper(
        cache_dir=cache_dir,
        max_download_workers=max_download_workers,
        max_processing_workers=max_processing_workers,
        preserve_formatting=preserve_formatting
    )