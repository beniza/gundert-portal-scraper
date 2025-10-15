"""Download phase implementation for two-phase extraction."""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path

from ..core.connection import GundertPortalConnector
from ..core.cache import RawContentCache, CacheMetadata
from ..core.book_identifier import BookIdentifier
from ..core.exceptions import ExtractionError

logger = logging.getLogger(__name__)


class DownloadProgress:
    """Progress tracking for download phase."""
    
    def __init__(self, total_pages: int):
        self.total_pages = total_pages
        self.completed_pages = 0
        self.failed_pages = []
        self.start_time = datetime.now()
        self.current_page = 0
        
    def update(self, page_number: int, success: bool = True):
        """Update progress for a completed page."""
        self.completed_pages += 1
        self.current_page = page_number
        if not success:
            self.failed_pages.append(page_number)
    
    def get_progress_info(self) -> Dict[str, Any]:
        """Get current progress information."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        pages_per_second = self.completed_pages / elapsed if elapsed > 0 else 0
        
        return {
            'completed_pages': self.completed_pages,
            'total_pages': self.total_pages,
            'failed_pages': len(self.failed_pages),
            'percentage': (self.completed_pages / self.total_pages * 100) if self.total_pages > 0 else 0,
            'pages_per_second': round(pages_per_second, 2),
            'estimated_remaining_seconds': int((self.total_pages - self.completed_pages) / pages_per_second) if pages_per_second > 0 else 0,
            'current_page': self.current_page
        }


class DownloadWorker:
    """Worker class for downloading individual pages."""
    
    def __init__(self, worker_id: int, connector: GundertPortalConnector, cache: RawContentCache):
        self.worker_id = worker_id
        self.connector = connector
        self.cache = cache
        
    def download_page(self, book_id: str, page_number: int) -> Dict[str, Any]:
        """Download a single page with all available tabs."""
        result = {
            'page_number': page_number,
            'success': True,
            'tabs_downloaded': [],
            'errors': [],
            'download_time': 0.0
        }
        
        start_time = time.time()
        
        try:
            logger.debug(f"Worker {self.worker_id}: Downloading page {page_number}")
            
            # Download transcript tab (primary content)
            try:
                self.connector.navigate_to_page(page_number, "transcript")
                self.connector.wait_for_content_load()
                transcript_html = self.connector.get_current_page_source()
                
                if self.cache.save_page_content(book_id, page_number, transcript_html, "transcript"):
                    result['tabs_downloaded'].append('transcript')
                else:
                    result['errors'].append('Failed to save transcript content')
                    
            except Exception as e:
                result['errors'].append(f"Transcript download failed: {str(e)}")
                logger.warning(f"Failed to download transcript for page {page_number}: {e}")
            
            # Download view tab (images)
            try:
                self.connector.navigate_to_page(page_number, "view")
                self.connector.wait_for_content_load()
                view_html = self.connector.get_current_page_source()
                
                if self.cache.save_page_content(book_id, page_number, view_html, "view"):
                    result['tabs_downloaded'].append('view')
                else:
                    result['errors'].append('Failed to save view content')
                    
            except Exception as e:
                result['errors'].append(f"View download failed: {str(e)}")
                logger.warning(f"Failed to download view for page {page_number}: {e}")
            
            # If no content was downloaded successfully, mark as failed
            if not result['tabs_downloaded']:
                result['success'] = False
                
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"Page download failed: {str(e)}")
            logger.error(f"Worker {self.worker_id}: Failed to download page {page_number}: {e}")
        
        finally:
            result['download_time'] = time.time() - start_time
        
        return result
    
    def download_complete_book(self, book_id: str, requested_pages: List[int]) -> Dict[str, Any]:
        """Download complete book content once for SPA websites like opendigi.
        
        Args:
            book_id: The book identifier
            requested_pages: List of page numbers requested by user
            
        Returns:
            Dict containing page_results and failed_pages
        """
        logger.info(f"Downloading complete book content for SPA website: {book_id}")
        start_time = time.time()
        
        page_results = []
        failed_pages = []
        
        try:
            # Navigate to the base book URL (loads complete content)
            self.connector.navigate_to_page(1, "view")  # Load any page to get full content
            self.connector.wait_for_content_load()
            
            # Get complete HTML content
            complete_html = self.connector.get_current_page_source()
            
            # Parse page structure from HTML to understand available pages
            page_structure = self._parse_spa_page_structure(complete_html)
            max_available_page = max(page_structure.keys()) if page_structure else max(requested_pages)
            
            # Save content for each requested page
            for page_num in requested_pages:
                result = {
                    'page_number': page_num,
                    'success': True,
                    'tabs_downloaded': [],
                    'errors': [],
                    'download_time': 0.0
                }
                
                if page_num > max_available_page:
                    result['success'] = False
                    result['errors'].append(f'Page {page_num} exceeds available pages ({max_available_page})')
                    failed_pages.append(page_num)
                    page_results.append(result)
                    continue
                
                # Save complete content for both tabs (they're identical in SPA)
                try:
                    # Save as transcript tab
                    if self.cache.save_page_content(book_id, page_num, complete_html, "transcript"):
                        result['tabs_downloaded'].append('transcript')
                    
                    # Save as view tab (same content but different tab)
                    if self.cache.save_page_content(book_id, page_num, complete_html, "view"):
                        result['tabs_downloaded'].append('view')
                    
                    if not result['tabs_downloaded']:
                        result['success'] = False
                        result['errors'].append('Failed to save content for both tabs')
                        failed_pages.append(page_num)
                
                except Exception as e:
                    result['success'] = False
                    result['errors'].append(f'Cache save failed: {str(e)}')
                    failed_pages.append(page_num)
                    
                result['download_time'] = time.time() - start_time
                page_results.append(result)
            
            total_time = time.time() - start_time
            logger.info(f"Complete book download finished in {total_time:.1f}s: "
                       f"{len(requested_pages) - len(failed_pages)}/{len(requested_pages)} pages successful")
            
            return {
                'page_results': page_results,
                'failed_pages': failed_pages,
                'total_download_time': total_time,
                'page_structure': page_structure
            }
            
        except Exception as e:
            logger.error(f"Complete book download failed: {e}")
            # Mark all pages as failed
            for page_num in requested_pages:
                failed_pages.append(page_num)
                page_results.append({
                    'page_number': page_num,
                    'success': False,
                    'tabs_downloaded': [],
                    'errors': [f'Complete book download failed: {str(e)}'],
                    'download_time': time.time() - start_time
                })
            
            return {
                'page_results': page_results,
                'failed_pages': failed_pages,
                'total_download_time': time.time() - start_time,
                'page_structure': {}
            }
    
    def _parse_spa_page_structure(self, html_content: str) -> Dict[int, Dict[str, Any]]:
        """Parse the page structure from SPA HTML content.
        
        Args:
            html_content: Complete HTML content from SPA
            
        Returns:
            Dictionary mapping page numbers to page information
        """
        try:
            from bs4 import BeautifulSoup
            import re
            
            soup = BeautifulSoup(html_content, 'html.parser')
            page_structure = {}
            
            # Find all elements with data-pages attributes
            elements_with_pages = soup.find_all(attrs={'data-pages': True})
            
            for element in elements_with_pages:
                data_pages_str = element.get('data-pages', '')
                
                # Extract page numbers from data-pages="[1,2,3]" format
                import json
                try:
                    page_numbers = json.loads(data_pages_str)
                    if isinstance(page_numbers, list):
                        # Get section title if available
                        section_title = element.get_text(strip=True) or "Unknown Section"
                        
                        # Add each page to the structure
                        for page_num in page_numbers:
                            page_structure[page_num] = {
                                'section_title': section_title,
                                'is_part_of_section': True,
                                'section_pages': page_numbers
                            }
                            
                except (json.JSONDecodeError, ValueError):
                    # If JSON parsing fails, try regex extraction
                    match = re.search(r'\[([0-9,\s]+)\]', data_pages_str)
                    if match:
                        page_nums_str = match.group(1)
                        try:
                            page_numbers = [int(x.strip()) for x in page_nums_str.split(',') if x.strip()]
                            section_title = element.get_text(strip=True) or "Unknown Section"
                            
                            for page_num in page_numbers:
                                page_structure[page_num] = {
                                    'section_title': section_title,
                                    'is_part_of_section': True,
                                    'section_pages': page_numbers
                                }
                        except ValueError:
                            continue
            
            logger.debug(f"Parsed SPA page structure: {len(page_structure)} pages found")
            return page_structure
            
        except Exception as e:
            logger.warning(f"Failed to parse SPA page structure: {e}")
            return {}


class DownloadPhase:
    """Manages the download phase of two-phase extraction."""
    
    def __init__(self, cache: Optional[RawContentCache] = None, max_workers: int = 3):
        """Initialize download phase.
        
        Args:
            cache: Cache instance to use
            max_workers: Maximum number of concurrent download workers
        """
        self.cache = cache or RawContentCache()
        self.max_workers = max_workers
        self.progress_callback: Optional[Callable] = None
        
    def set_progress_callback(self, callback: Callable[[DownloadProgress], None]):
        """Set callback for progress updates."""
        self.progress_callback = callback
    
    def check_cache_status(self, book_id: str) -> Dict[str, Any]:
        """Check what's already cached for a book."""
        cache_info = self.cache.get_cache_info(book_id)
        
        if not cache_info:
            return {
                'is_cached': False,
                'pages_cached': [],
                'cache_valid': False,
                'cache_info': None
            }
        
        # Validate cache
        cache_valid, issues = self.cache.validate_cache(book_id)
        
        return {
            'is_cached': True,
            'pages_cached': cache_info.get('pages_cached', []),
            'cache_valid': cache_valid,
            'cache_issues': issues if not cache_valid else [],
            'cache_info': cache_info
        }
    
    def download_book(self, book_identifier: BookIdentifier, 
                     start_page: int = 1, 
                     end_page: Optional[int] = None,
                     force_redownload: bool = False) -> Dict[str, Any]:
        """Download complete book content with parallel processing.
        
        Args:
            book_identifier: Book to download
            start_page: Starting page number
            end_page: Ending page number (None = auto-detect)
            force_redownload: Force redownload even if cached
            
        Returns:
            Download results with statistics
        """
        book_id = book_identifier.book_id
        
        # Check cache status
        cache_status = self.check_cache_status(book_id)
        
        if cache_status['is_cached'] and cache_status['cache_valid'] and not force_redownload:
            logger.info(f"Book {book_id} is already cached and valid")
            return {
                'success': True,
                'from_cache': True,
                'cache_info': cache_status['cache_info'],
                'download_statistics': None
            }
        
        if cache_status['is_cached'] and not force_redownload:
            if not cache_status['cache_valid']:
                logger.warning(f"Cache for {book_id} is invalid: {cache_status['cache_issues']}")
            else:
                logger.info(f"Using existing cache for {book_id}")
        
        # Initialize cache metadata
        try:
            metadata = self.cache.initialize_metadata(
                book_id, 
                book_identifier.portal_type, 
                book_identifier.base_url or "unknown"
            )
        except Exception as e:
            raise ExtractionError("cache initialization", f"Failed to initialize cache: {str(e)}")
        
        # Create connector and get page range
        # Generate the proper book URL for the connector
        book_url = book_identifier.generate_book_url()
        with GundertPortalConnector(book_url, use_selenium=True) as main_connector:
            try:
                # Detect page count if not specified
                if end_page is None:
                    total_pages = main_connector.get_page_count()
                    end_page = total_pages
                else:
                    total_pages = end_page
                
                end_page = min(end_page, total_pages)
                pages_to_download = list(range(start_page, end_page + 1))
                
                logger.info(f"Starting download of {len(pages_to_download)} pages for {book_id}")
                
                # Initialize progress tracking
                progress = DownloadProgress(len(pages_to_download))
                download_start = datetime.now()
                
                # Create worker pool and download pages
                download_results = []
                failed_pages = []
                
                # For SPA websites (like opendigi), download complete content once
                if book_identifier.portal_type == 'opendigi':
                    # Download complete book content once instead of page by page
                    worker = DownloadWorker(0, main_connector, self.cache)
                    spa_result = worker.download_complete_book(book_id, pages_to_download)
                    download_results = spa_result['page_results']
                    failed_pages = spa_result['failed_pages']
                    
                    # Update progress for all pages at once
                    for page_num in pages_to_download:
                        progress.update(page_num, page_num not in failed_pages)
                else:
                    # Sequential download for page-based sites
                    for page_num in pages_to_download:
                        worker = DownloadWorker(0, main_connector, self.cache)
                        result = worker.download_page(book_id, page_num)
                        download_results.append(result)
                        
                        # Update progress
                        progress.update(page_num, result['success'])
                    
                    if not result['success']:
                        failed_pages.append(page_num)
                        logger.warning(f"Failed to download page {page_num}: {result['errors']}")
                    
                    # Call progress callback if set
                    if self.progress_callback:
                        self.progress_callback(progress)
                    
                    # Brief pause between pages
                    time.sleep(0.5)
                
                download_end = datetime.now()
                download_duration = (download_end - download_start).total_seconds()
                
                # Update metadata with final statistics
                metadata.page_count = total_pages
                metadata.pages_cached = [r['page_number'] for r in download_results if r['success']]
                metadata.download_duration_seconds = download_duration
                
                # Save final metadata
                try:
                    book_dir = self.cache.get_book_cache_dir(book_id)
                    metadata_file = book_dir / "metadata.json"
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        import json
                        json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)
                except Exception as e:
                    logger.warning(f"Failed to save final metadata: {e}")
                
                # Compile results
                successful_pages = progress.completed_pages - len(failed_pages)
                statistics = {
                    'total_pages': len(pages_to_download),
                    'successful_pages': successful_pages,
                    'failed_pages': len(failed_pages),
                    'success_rate': (successful_pages / len(pages_to_download) * 100) if pages_to_download else 0,
                    'download_duration_seconds': download_duration,
                    'pages_per_minute': (successful_pages / (download_duration / 60)) if download_duration > 0 else 0,
                    'failed_page_numbers': failed_pages
                }
                
                logger.info(f"Download completed: {statistics['successful_pages']}/{statistics['total_pages']} pages in {download_duration:.1f}s")
                
                return {
                    'success': statistics['failed_pages'] == 0,
                    'from_cache': False,
                    'statistics': statistics,
                    'download_results': download_results,
                    'cache_info': self.cache.get_cache_info(book_id)
                }
                
            except Exception as e:
                logger.error(f"Download phase failed: {e}")
                raise ExtractionError("download phase", f"Download failed: {str(e)}")
    
    def resume_download(self, book_id: str, missing_pages: List[int]) -> Dict[str, Any]:
        """Resume download for missing pages."""
        logger.info(f"Resuming download for {book_id}, missing pages: {missing_pages}")
        
        # This would implement resuming partial downloads
        # For now, return placeholder
        return {
            'success': False,
            'message': "Resume download not yet implemented"
        }