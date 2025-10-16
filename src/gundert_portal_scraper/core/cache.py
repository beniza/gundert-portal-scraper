"""
Caching system for downloaded content.

Implements the download phase cache to avoid repeated browser connections.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class RawContentCache:
    """
    Cache for raw downloaded content from SPA pages.
    
    Stores the complete HTML/XML content after initial download,
    eliminating need for repeated browser connections.
    """
    
    def __init__(self, cache_dir: str = "./cache"):
        """
        Initialize cache.
        
        Args:
            cache_dir: Directory to store cached content
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_path(self, book_id: str) -> Path:
        """Get cache file path for book."""
        return self.cache_dir / f"{book_id}_content.json"
    
    def is_cached(self, book_id: str) -> bool:
        """Check if book content is cached."""
        return self.get_cache_path(book_id).exists()
    
    def save(
        self,
        book_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save content to cache.
        
        Args:
            book_id: Book identifier
            content: Raw HTML/XML content
            metadata: Optional metadata to store
        """
        cache_data = {
            "book_id": book_id,
            "content": content,
            "metadata": metadata or {},
            "cached_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        cache_path = self.get_cache_path(book_id)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    def load(self, book_id: str) -> Optional[Dict[str, Any]]:
        """
        Load cached content.
        
        Args:
            book_id: Book identifier
            
        Returns:
            Dict with 'content' and 'metadata', or None if not cached
        """
        cache_path = self.get_cache_path(book_id)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Error loading cache: {e}")
            return None
    
    def clear(self, book_id: str) -> bool:
        """
        Clear cached content for book.
        
        Args:
            book_id: Book identifier
            
        Returns:
            True if cleared, False if not found
        """
        cache_path = self.get_cache_path(book_id)
        
        if cache_path.exists():
            cache_path.unlink()
            return True
        
        return False
    
    def clear_all(self) -> int:
        """
        Clear all cached content.
        
        Returns:
            Number of files cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob("*_content.json"):
            cache_file.unlink()
            count += 1
        
        return count
