"""ParaBible JSON transformer for parallel Bible analysis format."""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import re

from ..framework import BaseTransformer, TransformationResult, LineMapping
from ...storage.schemas import BookStorage, PageContent
from ...core.exceptions import TransformationError

logger = logging.getLogger(__name__)


class ParaBibleTransformer(BaseTransformer):
    """Transforms biblical content to ParaBible JSON format."""
    
    def __init__(self):
        super().__init__()
        self.output_format = "parabible_json"
        self.supported_content_types = ["biblical", "religious", "all"]
        self.version = "1.0"
        
        # Biblical structure patterns
        self.chapter_patterns = [
            r'അധ്യായം\s*(\d+)',  # Malayalam chapter
            r'Chapter\s*(\d+)',   # English chapter
            r'^(\d+)\s*$',        # Standalone number
        ]
        
        self.verse_patterns = [
            r'^\d+\.',          # Verse with dot
            r'^\d+\s+',         # Verse with space
            r'വാക്യം\s*(\d+)',  # Malayalam verse
        ]
        
        # Book mapping (can be extended)
        self.book_mapping = {
            'genesis': 'GEN',
            'exodus': 'EXO',
            'matthew': 'MAT',
            'mark': 'MRK',
            'luke': 'LUK',
            'john': 'JHN',
            # Add more as needed
        }
    
    def transform(self, book_storage: BookStorage, output_path: Optional[Path] = None, 
                 options: Dict[str, Any] = None) -> TransformationResult:
        """Transform book content to ParaBible JSON format.
        
        Args:
            book_storage: Source book storage
            output_path: Optional output file path
            options: Transformation options
            
        Returns:
            TransformationResult with ParaBible JSON content
        """
        options = options or {}
        self.line_mappings = LineMapping()
        
        try:
            # Generate ParaBible structure
            parabible_data = self._generate_parabible_json(book_storage, options)
            
            # Convert to JSON string
            json_content = json.dumps(parabible_data, ensure_ascii=False, indent=2)
            
            # Write to file if path provided
            file_path = None
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(json_content)
                file_path = str(output_path)
                logger.info(f"ParaBible JSON written to {output_path}")
            
            # Prepare metadata
            metadata = {
                'book_id': book_storage.book_metadata.book_id,
                'parabible_version': '1.0',
                'transformation_date': datetime.now().isoformat(),
                'source_pages': len(book_storage.pages),
                'total_verses': len(parabible_data.get('verses', [])),
                'options': options
            }
            
            return TransformationResult(
                success=True,
                output_format=self.output_format,
                content=json_content,
                file_path=file_path,
                line_mappings=self.line_mappings,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"ParaBible transformation failed: {e}")
            return TransformationResult(
                success=False,
                output_format=self.output_format,
                errors=[str(e)]
            )
    
    def _generate_parabible_json(self, book_storage: BookStorage, options: Dict[str, Any]) -> Dict[str, Any]:
        """Generate ParaBible JSON structure.
        
        Args:
            book_storage: Source book storage
            options: Transformation options
            
        Returns:
            ParaBible JSON dictionary
        """
        # Initialize ParaBible structure
        parabible_data = {
            "metadata": self._create_metadata(book_storage, options),
            "verses": [],
            "chapters": {},
            "statistics": {}
        }
        
        # Process content to extract verses
        verses = self._extract_verses(book_storage, options)
        parabible_data["verses"] = verses
        
        # Organize verses by chapters
        chapters = self._organize_by_chapters(verses)
        parabible_data["chapters"] = chapters
        
        # Generate statistics
        stats = self._generate_statistics(verses, chapters)
        parabible_data["statistics"] = stats
        
        return parabible_data
    
    def _create_metadata(self, book_storage: BookStorage, options: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata section.
        
        Args:
            book_storage: Source book storage
            options: Metadata options
            
        Returns:
            Metadata dictionary
        """
        book_metadata = book_storage.book_metadata
        
        # Try to detect book code from title or ID
        book_code = self._detect_book_code(book_metadata)
        
        metadata = {
            "book_id": book_metadata.book_id,
            "book_code": book_code,
            "title": getattr(book_metadata, 'title', f"Book {book_metadata.book_id}"),
            "language": "ml",  # Malayalam
            "script": "malayalam",
            "source": {
                "type": "manuscript_scan",
                "url": getattr(book_metadata, 'source_url', ''),
                "pages": len(book_storage.pages)
            },
            "transformation": {
                "date": datetime.now().isoformat(),
                "version": self.version,
                "tool": "Gundert Portal Scraper"
            },
            "encoding": "UTF-8"
        }
        
        return metadata
    
    def _extract_verses(self, book_storage: BookStorage, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract verses from book content.
        
        Args:
            book_storage: Source book storage
            options: Extraction options
            
        Returns:
            List of verse dictionaries
        """
        verses = []
        current_chapter = 1  # Default chapter
        current_verse = 1    # Default verse
        verse_id = 1
        
        for page_num, page in enumerate(book_storage.pages, 1):
            if not page.transcript_info.get('available'):
                continue
            
            # Get page content lines
            content_lines = self._get_page_lines(page)
            
            for line_num, line in enumerate(content_lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Detect chapter and verse structure
                chapter_match, verse_match = self._detect_structure(line)
                
                if chapter_match:
                    current_chapter = chapter_match
                    continue
                
                if verse_match:
                    current_verse = verse_match
                
                # Create verse entry
                verse_text = self._clean_verse_content(line)
                if verse_text:
                    verse_data = {
                        "id": verse_id,
                        "chapter": current_chapter,
                        "verse": current_verse,
                        "text": verse_text,
                        "source": {
                            "page": page_num,
                            "line": line_num
                        },
                        "metadata": {
                            "character_count": len(verse_text),
                            "word_count": len(verse_text.split()),
                            "language": "ml"
                        }
                    }
                    
                    verses.append(verse_data)
                    
                    # Add line mapping
                    location = f"verse_id_{verse_id}"
                    self.line_mappings.add_mapping(
                        original_page=page_num,
                        original_line=line_num,
                        transformed_location=location,
                        context={
                            'type': 'verse',
                            'chapter': current_chapter,
                            'verse': current_verse,
                            'verse_id': verse_id
                        }
                    )
                    
                    verse_id += 1
                    
                    # Auto-increment verse if no explicit verse detected
                    if not verse_match:
                        current_verse += 1
        
        return verses
    
    def _organize_by_chapters(self, verses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Organize verses by chapters.
        
        Args:
            verses: List of verse dictionaries
            
        Returns:
            Chapter organization dictionary
        """
        chapters = {}
        
        for verse in verses:
            chapter_num = verse["chapter"]
            
            if chapter_num not in chapters:
                chapters[chapter_num] = {
                    "chapter": chapter_num,
                    "verses": [],
                    "verse_count": 0,
                    "character_count": 0,
                    "word_count": 0
                }
            
            chapters[chapter_num]["verses"].append({
                "verse": verse["verse"],
                "text": verse["text"],
                "id": verse["id"]
            })
            
            # Update chapter statistics
            chapters[chapter_num]["verse_count"] += 1
            chapters[chapter_num]["character_count"] += verse["metadata"]["character_count"]
            chapters[chapter_num]["word_count"] += verse["metadata"]["word_count"]
        
        # Convert to list format with chapter numbers as keys
        chapter_dict = {}
        for chapter_num in sorted(chapters.keys()):
            chapter_dict[str(chapter_num)] = chapters[chapter_num]
        
        return chapter_dict
    
    def _generate_statistics(self, verses: List[Dict[str, Any]], chapters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate content statistics.
        
        Args:
            verses: List of verses
            chapters: Chapter organization
            
        Returns:
            Statistics dictionary
        """
        total_characters = sum(verse["metadata"]["character_count"] for verse in verses)
        total_words = sum(verse["metadata"]["word_count"] for verse in verses)
        
        stats = {
            "total_verses": len(verses),
            "total_chapters": len(chapters),
            "total_characters": total_characters,
            "total_words": total_words,
            "average_verse_length": total_characters / len(verses) if verses else 0,
            "average_words_per_verse": total_words / len(verses) if verses else 0,
            "chapter_statistics": {}
        }
        
        # Per-chapter statistics
        for chapter_num, chapter_data in chapters.items():
            stats["chapter_statistics"][chapter_num] = {
                "verses": chapter_data["verse_count"],
                "characters": chapter_data["character_count"],
                "words": chapter_data["word_count"],
                "avg_verse_length": chapter_data["character_count"] / chapter_data["verse_count"] if chapter_data["verse_count"] > 0 else 0
            }
        
        return stats
    
    def _get_page_lines(self, page: PageContent) -> List[str]:
        """Extract text lines from page content.
        
        Args:
            page: Page content object
            
        Returns:
            List of text lines
        """
        lines = []
        
        # Get text content from transcript_info
        if page.transcript_info.get('available') and page.transcript_info.get('transcript_text'):
            lines = page.transcript_info['transcript_text'].split('\n')
        
        if not lines:
            return []
        
        # Clean and filter lines
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not self._is_metadata_line(line):
                cleaned_lines.append(line)
        
        return cleaned_lines
    
    def _detect_structure(self, line: str) -> Tuple[Optional[int], Optional[int]]:
        """Detect chapter and verse numbers in a line.
        
        Args:
            line: Text line to analyze
            
        Returns:
            Tuple of (chapter_number, verse_number) or (None, None)
        """
        chapter_num = None
        verse_num = None
        
        # Check for chapter patterns
        for pattern in self.chapter_patterns:
            match = re.search(pattern, line)
            if match:
                try:
                    chapter_num = int(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
        
        # Check for verse patterns
        for pattern in self.verse_patterns:
            match = re.search(pattern, line)
            if match:
                try:
                    verse_num = int(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
        
        return chapter_num, verse_num
    
    def _clean_verse_content(self, line: str) -> str:
        """Clean verse content by removing verse number markers.
        
        Args:
            line: Raw verse line
            
        Returns:
            Cleaned verse text
        """
        # Remove verse number prefixes
        for pattern in self.verse_patterns:
            line = re.sub(pattern, '', line).strip()
        
        # Remove chapter references
        for pattern in self.chapter_patterns:
            line = re.sub(pattern, '', line).strip()
        
        return line.strip()
    
    def _detect_book_code(self, book_metadata) -> str:
        """Detect biblical book code from metadata.
        
        Args:
            book_metadata: Book metadata
            
        Returns:
            Book code (e.g., 'GEN', 'MAT')
        """
        # Try to match title or ID to known books
        title = getattr(book_metadata, 'title', '').lower()
        book_id = book_metadata.book_id.lower()
        
        search_text = f"{title} {book_id}"
        
        for book_name, code in self.book_mapping.items():
            if book_name in search_text:
                return code
        
        # Default to unknown
        return "UNK"
    
    def _is_metadata_line(self, line: str) -> bool:
        """Check if line contains metadata rather than content.
        
        Args:
            line: Line to check
            
        Returns:
            True if line appears to be metadata
        """
        metadata_indicators = [
            'page', 'പേജ്',  # Page indicators
            'source:', 'url:', 'http', 'www.',  # URL indicators
            '©', 'copyright', 'all rights reserved'  # Copyright indicators
        ]
        
        line_lower = line.lower()
        return any(indicator in line_lower for indicator in metadata_indicators)
    
    def is_compatible(self, book_storage: BookStorage) -> bool:
        """Check compatibility with book content.
        
        Args:
            book_storage: Book storage to check
            
        Returns:
            True if content appears biblical
        """
        if not super().is_compatible(book_storage):
            return False
        
        # Check for biblical indicators
        biblical_indicators = [
            'അധ്യായം',  # Chapter in Malayalam
            'വാക്യം',   # Verse in Malayalam
            'chapter',
            'verse',
        ]
        
        # Sample content to check
        sample_text = ""
        for page in book_storage.pages[:3]:
            if page.transcript_info.get('available') and page.transcript_info.get('transcript_text'):
                sample_text += page.transcript_info['transcript_text']
        
        sample_lower = sample_text.lower()
        return any(indicator in sample_lower for indicator in biblical_indicators)
    
    def validate_input(self, book_storage: BookStorage) -> List[str]:
        """Validate input for ParaBible transformation.
        
        Args:
            book_storage: Book storage to validate
            
        Returns:
            List of validation errors
        """
        errors = super().validate_input(book_storage)
        
        # Check for biblical content structure
        has_verses = False
        
        for page in book_storage.pages[:5]:
            if not page.transcript_info.get('available'):
                continue
            
            content_text = page.transcript_info.get('transcript_text', "")
            
            # Look for verse patterns
            for pattern in self.verse_patterns:
                if re.search(pattern, content_text, re.MULTILINE):
                    has_verses = True
                    break
            
            if has_verses:
                break
        
        if not has_verses:
            errors.append("No biblical verse structure detected for ParaBible format")
        
        return errors