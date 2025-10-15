"""Book storage manager with organized folder structure."""

import os
import json
import hashlib
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import requests
from urllib.parse import urlparse

from .schemas import BookStorage, BookMetadata, ContentFormat, StorageVersion
from ..core.exceptions import StorageError

logger = logging.getLogger(__name__)


class BookStorageManager:
    """Manages storage and organization of extracted book content."""
    
    def __init__(self, base_storage_path: str = "extracted_books"):
        """Initialize the storage manager.
        
        Args:
            base_storage_path: Base directory for all extracted books
        """
        self.base_path = Path(base_storage_path)
        self.base_path.mkdir(exist_ok=True)
        
        logger.info(f"BookStorageManager initialized with base path: {self.base_path.absolute()}")
    
    def get_book_storage_path(self, book_id: str) -> Path:
        """Get the storage path for a specific book.
        
        Args:
            book_id: Book identifier
            
        Returns:
            Path object for the book's storage directory
        """
        # Sanitize book ID for filesystem
        safe_book_id = self._sanitize_filename(book_id)
        return self.base_path / safe_book_id
    
    def create_book_structure(self, book_id: str) -> Path:
        """Create the folder structure for a book.
        
        Args:
            book_id: Book identifier
            
        Returns:
            Path to the created book directory
        """
        book_path = self.get_book_storage_path(book_id)
        
        # Create directory structure (parents=True to create parent directories)
        directories = [
            book_path,
            book_path / "images",
            book_path / "logs",
            book_path / "exports"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created storage structure for book: {book_id}")
        return book_path
    
    def save_book(self, book_storage: BookStorage, formats: List[ContentFormat] = None) -> Dict[str, str]:
        """Save book content in specified formats.
        
        Args:
            book_storage: BookStorage object to save
            formats: List of formats to save (default: JSON only)
            
        Returns:
            Dictionary mapping format names to file paths
        """
        if formats is None:
            formats = [ContentFormat.JSON]
        
        book_id = book_storage.book_metadata.book_id
        book_path = self.create_book_structure(book_id)
        
        # Update storage metadata
        book_storage.storage_path = str(book_path)
        book_storage.last_updated = datetime.now().isoformat()
        
        saved_files = {}
        
        try:
            # Save in each requested format
            for format_type in formats:
                if format_type == ContentFormat.JSON:
                    file_path = self._save_json(book_storage, book_path)
                    saved_files['json'] = str(file_path)
                    
                elif format_type == ContentFormat.TEI_XML:
                    file_path = self._save_tei_xml(book_storage, book_path)
                    saved_files['tei_xml'] = str(file_path)
                    
                elif format_type == ContentFormat.PLAIN_TEXT:
                    file_path = self._save_plain_text(book_storage, book_path)
                    saved_files['plain_text'] = str(file_path)
                    
                elif format_type == ContentFormat.MARKDOWN:
                    file_path = self._save_markdown(book_storage, book_path)
                    saved_files['markdown'] = str(file_path)
            
            # Save metadata separately for quick access
            metadata_path = self._save_metadata(book_storage.book_metadata, book_path)
            saved_files['metadata'] = str(metadata_path)
            
            # Save extraction log
            log_path = self._save_extraction_log(book_storage, book_path)
            saved_files['log'] = str(log_path)
            
            logger.info(f"Successfully saved book {book_id} in {len(formats)} format(s)")
            return saved_files
            
        except Exception as e:
            logger.error(f"Failed to save book {book_id}: {e}")
            raise StorageError("book saving", f"Failed to save book {book_id}: {str(e)}")
    
    def load_book(self, book_id: str, format_type: ContentFormat = ContentFormat.JSON) -> BookStorage:
        """Load book content from storage.
        
        Args:
            book_id: Book identifier
            format_type: Format to load from
            
        Returns:
            BookStorage object
        """
        book_path = self.get_book_storage_path(book_id)
        
        if not book_path.exists():
            raise StorageError("book loading", f"Book {book_id} not found in storage")
        
        try:
            if format_type == ContentFormat.JSON:
                return self._load_json(book_path)
            else:
                raise StorageError("book loading", f"Loading from {format_type.value} not yet implemented")
                
        except Exception as e:
            logger.error(f"Failed to load book {book_id}: {e}")
            raise StorageError("book loading", f"Failed to load book {book_id}: {str(e)}")
    
    def list_stored_books(self) -> List[Dict[str, Any]]:
        """List all books in storage with basic metadata.
        
        Returns:
            List of dictionaries with book information
        """
        books = []
        
        for book_dir in self.base_path.iterdir():
            if book_dir.is_dir():
                try:
                    metadata_file = book_dir / "metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        # Get file information
                        content_file = book_dir / "content.json"
                        file_size = content_file.stat().st_size if content_file.exists() else 0
                        last_modified = datetime.fromtimestamp(content_file.stat().st_mtime).isoformat() if content_file.exists() else None
                        
                        books.append({
                            'book_id': metadata.get('book_id', book_dir.name),
                            'title': metadata.get('title', 'Unknown'),
                            'author': metadata.get('author'),
                            'content_type': metadata.get('content_type'),
                            'primary_language': metadata.get('primary_language'),
                            'page_count': metadata.get('page_count'),
                            'storage_path': str(book_dir),
                            'file_size_bytes': file_size,
                            'last_modified': last_modified
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to read metadata for {book_dir.name}: {e}")
        
        return sorted(books, key=lambda x: x.get('last_modified', ''), reverse=True)
    
    def delete_book(self, book_id: str, confirm: bool = False) -> bool:
        """Delete a book from storage.
        
        Args:
            book_id: Book identifier
            confirm: Confirmation flag for safety
            
        Returns:
            True if deleted successfully
        """
        if not confirm:
            raise StorageError("book deletion", "Deletion requires explicit confirmation")
        
        book_path = self.get_book_storage_path(book_id)
        
        if not book_path.exists():
            logger.warning(f"Book {book_id} not found for deletion")
            return False
        
        try:
            shutil.rmtree(book_path)
            logger.info(f"Successfully deleted book {book_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete book {book_id}: {e}")
            raise StorageError("book deletion", f"Failed to delete book {book_id}: {str(e)}")
    
    def download_images(self, book_storage: BookStorage, max_concurrent: int = 5) -> Dict[str, str]:
        """Download and save all images for a book.
        
        Args:
            book_storage: BookStorage object with image URLs
            max_concurrent: Maximum concurrent downloads
            
        Returns:
            Dictionary mapping page numbers to local image paths
        """
        book_path = self.get_book_storage_path(book_storage.book_metadata.book_id)
        images_path = book_path / "images"
        images_path.mkdir(exist_ok=True)
        
        downloaded_images = {}
        
        for page in book_storage.pages:
            image_info = page.image_info
            if image_info.get('image_url'):
                try:
                    local_path = self._download_single_image(
                        image_info['image_url'],
                        images_path,
                        page.page_number,
                        image_info.get('format', 'jpg')
                    )
                    downloaded_images[str(page.page_number)] = str(local_path)
                    
                except Exception as e:
                    logger.warning(f"Failed to download image for page {page.page_number}: {e}")
        
        logger.info(f"Downloaded {len(downloaded_images)} images for book {book_storage.book_metadata.book_id}")
        return downloaded_images
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage usage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        stats = {
            'total_books': 0,
            'total_size_bytes': 0,
            'books_by_content_type': {},
            'books_by_language': {},
            'storage_path': str(self.base_path.absolute()),
            'last_updated': datetime.now().isoformat()
        }
        
        books = self.list_stored_books()
        stats['total_books'] = len(books)
        
        for book in books:
            # Size statistics
            stats['total_size_bytes'] += book.get('file_size_bytes', 0)
            
            # Content type statistics
            content_type = book.get('content_type', 'unknown')
            stats['books_by_content_type'][content_type] = stats['books_by_content_type'].get(content_type, 0) + 1
            
            # Language statistics
            language = book.get('primary_language', 'unknown')
            stats['books_by_language'][language] = stats['books_by_language'].get(language, 0) + 1
        
        # Convert bytes to human readable
        stats['total_size_mb'] = round(stats['total_size_bytes'] / (1024 * 1024), 2)
        
        return stats
    
    def _save_json(self, book_storage: BookStorage, book_path: Path) -> Path:
        """Save book as JSON."""
        file_path = book_path / "content.json"
        
        # Calculate checksum
        json_content = book_storage.to_json()
        book_storage.checksum = hashlib.sha256(json_content.encode('utf-8')).hexdigest()
        
        # Save with updated checksum
        json_content = book_storage.to_json()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_content)
        
        return file_path
    
    def _save_tei_xml(self, book_storage: BookStorage, book_path: Path) -> Path:
        """Save book as TEI XML."""
        from .formats import TEIConverter
        
        file_path = book_path / "content.xml"
        converter = TEIConverter()
        tei_xml = converter.convert_to_tei(book_storage)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(tei_xml)
        
        return file_path
    
    def _save_plain_text(self, book_storage: BookStorage, book_path: Path) -> Path:
        """Save book as plain text."""
        from .formats import PlainTextConverter
        
        file_path = book_path / "content.txt"
        converter = PlainTextConverter()
        plain_text = converter.convert_to_text(book_storage)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(plain_text)
        
        return file_path
    
    def _save_markdown(self, book_storage: BookStorage, book_path: Path) -> Path:
        """Save book as Markdown."""
        from .formats import MarkdownConverter
        
        file_path = book_path / "content.md" 
        converter = MarkdownConverter()
        markdown_content = converter.convert_to_markdown(book_storage)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return file_path
    
    def _save_metadata(self, metadata: BookMetadata, book_path: Path) -> Path:
        """Save metadata separately for quick access."""
        file_path = book_path / "metadata.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)
        
        return file_path
    
    def _save_extraction_log(self, book_storage: BookStorage, book_path: Path) -> Path:
        """Save extraction log with statistics and errors."""
        log_path = book_path / "logs" / "extraction.log"
        
        log_content = f"""Extraction Log for {book_storage.book_metadata.book_id}
{'=' * 60}

Extraction Timestamp: {book_storage.extraction_timestamp}
Format Version: {book_storage.format_version}

Book Metadata:
- Title: {book_storage.book_metadata.title}
- Author: {book_storage.book_metadata.author}
- Content Type: {book_storage.book_metadata.content_type}
- Primary Language: {book_storage.book_metadata.primary_language}
- Page Count: {book_storage.book_metadata.page_count}

Extraction Parameters:
- Page Range: {book_storage.extraction_parameters.start_page}-{book_storage.extraction_parameters.end_page}
- Batch Size: {book_storage.extraction_parameters.batch_size}
- Preserve Formatting: {book_storage.extraction_parameters.preserve_formatting}
- Portal Type: {book_storage.extraction_parameters.portal_type}

Statistics:
- Pages Processed: {book_storage.statistics.pages_processed}
- Pages with Images: {book_storage.statistics.pages_with_images}
- Pages with Transcripts: {book_storage.statistics.pages_with_transcripts}
- Total Lines Extracted: {book_storage.statistics.total_lines_extracted}
- Success Rate: {book_storage.statistics.success_rate}%
- Duration: {book_storage.statistics.extraction_duration_seconds:.2f} seconds
- Pages per Minute: {book_storage.statistics.pages_per_minute}

"""
        
        if book_storage.statistics.errors:
            log_content += "Errors:\n"
            for error in book_storage.statistics.errors:
                log_content += f"- Page {error.get('page_number', 'unknown')}: {error.get('error', 'Unknown error')}\n"
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        return log_path
    
    def _load_json(self, book_path: Path) -> BookStorage:
        """Load book from JSON."""
        file_path = book_path / "content.json"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            json_content = f.read()
        
        return BookStorage.from_json(json_content)
    
    def _download_single_image(self, url: str, images_path: Path, page_number: int, format_hint: str) -> Path:
        """Download a single image."""
        # Determine file extension
        parsed_url = urlparse(url)
        url_ext = Path(parsed_url.path).suffix.lower()
        
        if url_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.jp2']:
            ext = url_ext
        else:
            # Use format hint or default
            format_mapping = {
                'JPEG': '.jpg',
                'PNG': '.png', 
                'TIFF': '.tiff',
                'JPEG2000': '.jp2'
            }
            ext = format_mapping.get(format_hint.upper(), '.jpg')
        
        # Create filename
        filename = f"page_{page_number:03d}{ext}"
        local_path = images_path / filename
        
        # Download image
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return local_path
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        # Replace problematic characters
        sanitized = filename.replace('/', '_').replace('\\', '_').replace(':', '_')
        sanitized = sanitized.replace('?', '_').replace('*', '_').replace('"', '_')
        sanitized = sanitized.replace('<', '_').replace('>', '_').replace('|', '_')
        
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        return sanitized