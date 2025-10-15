"""USFM (Unified Standard Format Markers) transformer for biblical texts."""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

from ..framework import BaseTransformer, TransformationResult, LineMapping
from ...storage.schemas import BookStorage, PageContent
from ...core.exceptions import TransformationError

logger = logging.getLogger(__name__)


class USFMTransformer(BaseTransformer):
    """Transforms Malayalam biblical content to USFM format."""
    
    def __init__(self):
        super().__init__()
        self.output_format = "usfm"
        self.supported_content_types = ["biblical", "religious", "all"]
        self.version = "1.0"
        
        # USFM patterns for biblical text detection
        self.verse_patterns = [
            r'^\d+\.',  # "1.", "2.", etc.
            r'^\d+\s+',  # "1 ", "2 ", etc.
            r'അധ്യായം\s*\d+',  # Chapter in Malayalam
            r'വാക്യം\s*\d+',   # Verse in Malayalam
            r'\d+:\d+',  # Reference format "1:1"
        ]
        
        # Chapter and verse detection patterns
        self.chapter_patterns = [
            r'അധ്യായം\s*(\d+)',  # Malayalam chapter
            r'Chapter\s*(\d+)',   # English chapter
            r'^(\d+)\s*$',        # Standalone number
        ]
        
        self.verse_start_patterns = [
            r'^(\d+)\.',          # Verse with dot
            r'^(\d+)\s+',         # Verse with space
            r'വാക്യം\s*(\d+)',    # Malayalam verse
        ]
    
    def transform(self, book_storage: BookStorage, output_path: Optional[Path] = None, 
                 options: Dict[str, Any] = None) -> TransformationResult:
        """Transform book content to USFM format.
        
        Args:
            book_storage: Source book storage
            output_path: Optional output file path
            options: Transformation options
            
        Returns:
            TransformationResult with USFM content
        """
        options = options or {}
        self.line_mappings = LineMapping()
        
        try:
            # Generate USFM content
            usfm_content = self._generate_usfm(book_storage, options)
            
            # Write to file if path provided
            file_path = None
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(usfm_content)
                file_path = str(output_path)
                logger.info(f"USFM content written to {output_path}")
            
            # Prepare metadata
            metadata = {
                'book_id': book_storage.book_metadata.book_id,
                'usfm_version': '3.0',
                'transformation_date': datetime.now().isoformat(),
                'source_pages': len(book_storage.pages), 
                'content_lines': len(usfm_content.split('\n')),
                'options': options
            }
            
            return TransformationResult(
                success=True,
                output_format=self.output_format,
                content=usfm_content,
                file_path=file_path,
                line_mappings=self.line_mappings,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"USFM transformation failed: {e}")
            return TransformationResult(
                success=False,
                output_format=self.output_format,
                errors=[str(e)]
            )
    
    def _generate_usfm(self, book_storage: BookStorage, options: Dict[str, Any]) -> str:
        """Generate USFM content from book storage.
        
        Args:
            book_storage: Source book storage
            options: Transformation options
            
        Returns:
            USFM formatted string
        """
        usfm_lines = []
        
        # Add USFM header
        book_metadata = book_storage.book_metadata
        usfm_lines.extend(self._generate_header(book_metadata, options))
        
        # Process pages
        current_chapter = None
        current_verse = None
        line_number = len(usfm_lines)
        
        for page_num, page in enumerate(book_storage.pages, 1):
            if not page.transcript_info.get('available'):
                continue
            
            # Process page content
            page_lines = self._process_page_content(page, page_num, options)
            
            for original_line_num, content_line in enumerate(page_lines, 1):
                line_number += 1
                
                # Detect chapter/verse markers
                chapter_match, verse_match = self._detect_structure(content_line)
                
                if chapter_match:
                    chapter_num = chapter_match
                    if current_chapter != chapter_num:
                        current_chapter = chapter_num
                        current_verse = None
                        
                        # Add chapter marker
                        chapter_marker = f"\\c {chapter_num}"
                        usfm_lines.append(chapter_marker)
                        
                        # Add line mapping
                        self.line_mappings.add_mapping(
                            original_page=page_num,
                            original_line=original_line_num,
                            transformed_location=f"chapter_{chapter_num}",
                            context={'type': 'chapter', 'number': chapter_num}
                        )
                        
                        line_number += 1
                        continue
                
                if verse_match:
                    verse_num = verse_match
                    if current_verse != verse_num:
                        current_verse = verse_num
                        
                        # Add verse marker
                        verse_marker = f"\\v {verse_num}"
                        usfm_lines.append(verse_marker)
                        
                        # Add line mapping
                        self.line_mappings.add_mapping(
                            original_page=page_num,
                            original_line=original_line_num,
                            transformed_location=f"chapter_{current_chapter}_verse_{verse_num}",
                            context={'type': 'verse', 'chapter': current_chapter, 'verse': verse_num}
                        )
                        
                        line_number += 1
                
                # Add content line (remove verse numbers if detected)
                clean_content = self._clean_content_line(content_line)
                if clean_content.strip():
                    usfm_lines.append(clean_content)
                    
                    # Add line mapping
                    location = f"chapter_{current_chapter}_verse_{current_verse}" if current_chapter and current_verse else f"page_{page_num}_line_{original_line_num}"
                    self.line_mappings.add_mapping(
                        original_page=page_num,
                        original_line=original_line_num,
                        transformed_location=location,
                        context={'type': 'content', 'chapter': current_chapter, 'verse': current_verse}
                    )
        
        return '\n'.join(usfm_lines)
    
    def _generate_header(self, book_metadata, options: Dict[str, Any]) -> List[str]:
        """Generate USFM header markers.
        
        Args:
            book_metadata: Book metadata
            options: Transformation options
            
        Returns:
            List of header lines
        """
        header_lines = []
        
        # USFM identification
        header_lines.append("\\id UNK")  # Unknown book code - could be enhanced
        
        # Unicode byte order mark
        header_lines.append("\\usfm 3.0")
        
        # Header information
        if hasattr(book_metadata, 'title') and book_metadata.title:
            header_lines.append(f"\\h {book_metadata.title}")
            header_lines.append(f"\\toc1 {book_metadata.title}")
            header_lines.append(f"\\toc2 {book_metadata.title}")
            header_lines.append(f"\\toc3 {book_metadata.title}")
        
        # Main title
        if hasattr(book_metadata, 'title') and book_metadata.title:
            header_lines.append(f"\\mt1 {book_metadata.title}")
        
        # Source information
        if hasattr(book_metadata, 'source_url') and book_metadata.source_url:
            header_lines.append(f"\\rem Source: {book_metadata.source_url}")
        
        # Generation timestamp
        header_lines.append(f"\\rem Generated: {datetime.now().isoformat()}")
        
        # Language information
        header_lines.append("\\rem Language: Malayalam")
        
        return header_lines
    
    def _process_page_content(self, page: PageContent, page_num: int, 
                            options: Dict[str, Any]) -> List[str]:
        """Process content from a single page.
        
        Args:
            page: Page content object
            page_num: Page number
            options: Processing options
            
        Returns:
            List of content lines
        """
        content_lines = []
        
        # Get text content from transcript_info
        text_content = ""
        
        if page.transcript_info.get('available') and page.transcript_info.get('transcript_text'):
            text_content = page.transcript_info['transcript_text']
        
        if not text_content:
            return content_lines
        
        # Split into lines and clean
        raw_lines = text_content.split('\n')
        
        for line in raw_lines:
            line = line.strip()
            if line and not self._is_metadata_line(line):
                content_lines.append(line)
        
        return content_lines
    
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
        for pattern in self.verse_start_patterns:
            match = re.search(pattern, line)
            if match:
                try:
                    verse_num = int(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
        
        return chapter_num, verse_num
    
    def _clean_content_line(self, line: str) -> str:
        """Clean content line by removing verse numbers and markers.
        
        Args:
            line: Raw content line
            
        Returns:
            Cleaned content line
        """
        # Remove verse number prefixes
        for pattern in self.verse_start_patterns:
            line = re.sub(pattern, '', line).strip()
        
        # Remove other common markers
        line = re.sub(r'^വാക്യം\s*\d+\s*', '', line)  # Malayalam verse marker
        line = re.sub(r'^\d+:\d+\s*', '', line)        # Reference format
        
        return line.strip()
    
    def _is_metadata_line(self, line: str) -> bool:
        """Check if line contains metadata rather than content.
        
        Args:
            line: Line to check
            
        Returns:
            True if line appears to be metadata
        """
        metadata_indicators = [
            'page',
            'പേജ്',  # Malayalam "page"
            'source:',
            'url:',
            'http',
            'www.',
            '©',
            'copyright',
            'all rights reserved'
        ]
        
        line_lower = line.lower()
        return any(indicator in line_lower for indicator in metadata_indicators)
    
    def is_compatible(self, book_storage: BookStorage) -> bool:
        """Check compatibility with book content.
        
        Args:
            book_storage: Book storage to check
            
        Returns:
            True if content appears biblical/religious
        """
        if not super().is_compatible(book_storage):
            return False
        
        # Check for biblical indicators in content
        biblical_indicators = [
            'അധ്യായം',  # Chapter in Malayalam
            'വാക്യം',   # Verse in Malayalam  
            'chapter',
            'verse',
        ]
        
        # Sample some content to check
        sample_text = ""
        for page in book_storage.pages[:3]:  # Check first 3 pages
            if page.transcript_info.get('available') and page.transcript_info.get('transcript_text'):
                sample_text += page.transcript_info['transcript_text']
        
        sample_lower = sample_text.lower()
        return any(indicator in sample_lower for indicator in biblical_indicators)
    
    def validate_input(self, book_storage: BookStorage) -> List[str]:
        """Validate input for USFM transformation.
        
        Args:
            book_storage: Book storage to validate
            
        Returns:
            List of validation errors
        """
        errors = super().validate_input(book_storage)
        
        # Check for biblical content structure
        has_structured_content = False
        
        for page in book_storage.pages[:5]:  # Check first 5 pages
            if not page.transcript_info.get('available'):
                continue
            
            content_text = page.transcript_info.get('transcript_text', "")
            
            # Look for verse-like patterns
            for pattern in self.verse_patterns:
                if re.search(pattern, content_text, re.MULTILINE):
                    has_structured_content = True
                    break
            
            if has_structured_content:
                break
        
        if not has_structured_content:
            errors.append("No biblical verse structure detected in content")
        
        return errors