"""Raw content cache management for two-phase extraction."""

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)


class CacheMetadata:
    """Metadata for cached content."""
    
    def __init__(self, book_id: str, portal_type: str, url: str):
        self.book_id = book_id
        self.portal_type = portal_type
        self.url = url
        self.download_date = datetime.now().isoformat()
        self.page_count = 0
        self.pages_cached = []
        self.checksums = {}
        self.download_duration_seconds = 0.0
        self.cache_version = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            'book_id': self.book_id,
            'portal_type': self.portal_type,
            'url': self.url,
            'download_date': self.download_date,
            'page_count': self.page_count,
            'pages_cached': self.pages_cached,
            'checksums': self.checksums,
            'download_duration_seconds': self.download_duration_seconds,
            'cache_version': self.cache_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheMetadata':
        """Create from dictionary."""
        metadata = cls(
            book_id=data['book_id'],
            portal_type=data['portal_type'],
            url=data['url']
        )
        metadata.download_date = data.get('download_date', metadata.download_date)
        metadata.page_count = data.get('page_count', 0)
        metadata.pages_cached = data.get('pages_cached', [])
        metadata.checksums = data.get('checksums', {})
        metadata.download_duration_seconds = data.get('download_duration_seconds', 0.0)
        metadata.cache_version = data.get('cache_version', '1.0')
        return metadata


class RawContentCache:
    """Manages raw HTML content cache organized by book-id."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache manager.
        
        Args:
            cache_dir: Base cache directory. Defaults to ./cache
        """
        self.cache_dir = Path(cache_dir or "./cache")
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"RawContentCache initialized: {self.cache_dir.absolute()}")
    
    def get_book_cache_dir(self, book_id: str) -> Path:
        """Get cache directory for a specific book."""
        # Sanitize book_id for filesystem
        safe_book_id = "".join(c for c in book_id if c.isalnum() or c in "_-.")
        return self.cache_dir / safe_book_id
    
    def is_cached(self, book_id: str) -> bool:
        """Check if book is already cached."""
        book_dir = self.get_book_cache_dir(book_id)
        metadata_file = book_dir / "metadata.json"
        return metadata_file.exists()
    
    def get_cache_info(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Get cache information for a book."""
        if not self.is_cached(book_id):
            return None
        
        try:
            metadata_file = self.get_book_cache_dir(book_id) / "metadata.json"
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata_dict = json.load(f)
            
            # Add size information
            book_dir = self.get_book_cache_dir(book_id)
            total_size = sum(f.stat().st_size for f in book_dir.rglob('*') if f.is_file())
            
            return {
                **metadata_dict,
                'cache_size_bytes': total_size,
                'cache_size_mb': round(total_size / (1024 * 1024), 2),
                'cached_pages': len(metadata_dict.get('pages_cached', []))
            }
        except Exception as e:
            logger.error(f"Failed to get cache info for {book_id}: {e}")
            return None
    
    def save_page_content(self, book_id: str, page_number: int, 
                         html_content: str, tab_type: str = "transcript") -> bool:
        """Save raw HTML content for a page.
        
        Args:
            book_id: Book identifier
            page_number: Page number
            html_content: Raw HTML content
            tab_type: Type of tab (transcript, view, info)
            
        Returns:
            True if saved successfully
        """
        try:
            book_dir = self.get_book_cache_dir(book_id)
            book_dir.mkdir(exist_ok=True, parents=True)
            
            # Save HTML content
            filename = f"page_{page_number:04d}_{tab_type}.html"
            file_path = book_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Calculate checksum
            checksum = hashlib.md5(html_content.encode('utf-8')).hexdigest()
            
            # Update metadata
            self._update_metadata(book_id, page_number, tab_type, checksum)
            
            logger.debug(f"Cached page {page_number} ({tab_type}) for {book_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache page {page_number} for {book_id}: {e}")
            return False
    
    def load_page_content(self, book_id: str, page_number: int, 
                         tab_type: str = "transcript") -> Optional[str]:
        """Load cached HTML content for a page."""
        try:
            book_dir = self.get_book_cache_dir(book_id)
            filename = f"page_{page_number:04d}_{tab_type}.html"
            file_path = book_dir / filename
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Failed to load cached page {page_number} for {book_id}: {e}")
            return None
    
    def get_cached_pages(self, book_id: str) -> List[int]:
        """Get list of cached page numbers for a book."""
        if not self.is_cached(book_id):
            return []
        
        try:
            metadata = self.get_cache_info(book_id)
            return metadata.get('pages_cached', []) if metadata else []
        except Exception as e:
            logger.error(f"Failed to get cached pages for {book_id}: {e}")
            return []
    
    def validate_cache(self, book_id: str) -> Tuple[bool, List[str]]:
        """Validate cache integrity for a book.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        if not self.is_cached(book_id):
            return False, ["Cache not found"]
        
        try:
            book_dir = self.get_book_cache_dir(book_id)
            metadata_file = book_dir / "metadata.json"
            
            # Check metadata file
            if not metadata_file.exists():
                issues.append("Metadata file missing")
                return False, issues
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata_dict = json.load(f)
            
            # Validate cached pages exist
            pages_cached = metadata_dict.get('pages_cached', [])
            checksums = metadata_dict.get('checksums', {})
            
            for page_num in pages_cached:
                filename = f"page_{page_num:04d}_transcript.html"
                file_path = book_dir / filename
                
                if not file_path.exists():
                    issues.append(f"Page {page_num} file missing")
                    continue
                
                # Validate checksum if available
                if str(page_num) in checksums:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    actual_checksum = hashlib.md5(content.encode('utf-8')).hexdigest()
                    expected_checksum = checksums[str(page_num)]
                    
                    if actual_checksum != expected_checksum:
                        issues.append(f"Page {page_num} checksum mismatch")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            logger.error(f"Cache validation failed for {book_id}: {e}")
            return False, [f"Validation error: {str(e)}"]
    
    def clear_cache(self, book_id: str) -> bool:
        """Clear cache for a specific book."""
        try:
            book_dir = self.get_book_cache_dir(book_id)
            if book_dir.exists():
                shutil.rmtree(book_dir)
                logger.info(f"Cleared cache for book {book_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache for {book_id}: {e}")
            return False
    
    def list_cached_books(self) -> List[Dict[str, Any]]:
        """List all cached books with metadata."""
        cached_books = []
        
        for book_dir in self.cache_dir.iterdir():
            if book_dir.is_dir():
                metadata_file = book_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        # Add directory size
                        total_size = sum(f.stat().st_size for f in book_dir.rglob('*') if f.is_file())
                        metadata['cache_size_mb'] = round(total_size / (1024 * 1024), 2)
                        
                        cached_books.append(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to read metadata for {book_dir.name}: {e}")
        
        return cached_books
    
    def _update_metadata(self, book_id: str, page_number: int, 
                        tab_type: str, checksum: str) -> None:
        """Update cache metadata after saving content."""
        try:
            book_dir = self.get_book_cache_dir(book_id)
            metadata_file = book_dir / "metadata.json"
            
            # Load existing metadata or create new
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_dict = json.load(f)
                metadata = CacheMetadata.from_dict(metadata_dict)
            else:
                metadata = CacheMetadata(book_id, "unknown", "unknown")
            
            # Update metadata
            if page_number not in metadata.pages_cached:
                metadata.pages_cached.append(page_number)
                metadata.pages_cached.sort()
            
            metadata.checksums[f"{page_number}_{tab_type}"] = checksum
            metadata.page_count = max(metadata.page_count, page_number)
            
            # Save updated metadata
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to update metadata for {book_id}: {e}")
    
    def initialize_metadata(self, book_id: str, portal_type: str, url: str) -> CacheMetadata:
        """Initialize metadata for a new cache entry."""
        metadata = CacheMetadata(book_id, portal_type, url)
        
        try:
            book_dir = self.get_book_cache_dir(book_id)
            book_dir.mkdir(exist_ok=True, parents=True)
            
            metadata_file = book_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Initialized cache metadata for {book_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to initialize metadata for {book_id}: {e}")
            raise