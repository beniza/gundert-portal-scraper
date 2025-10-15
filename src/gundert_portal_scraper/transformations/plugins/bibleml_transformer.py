"""BibleML transformer for Bible markup language format."""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import re

from ..framework import BaseTransformer, TransformationResult, LineMapping
from ...storage.schemas import BookStorage, PageContent
from ...core.exceptions import TransformationError

logger = logging.getLogger(__name__)


class BibleMLTransformer(BaseTransformer):
    """Transforms biblical content to BibleML XML format."""
    
    def __init__(self):
        super().__init__()
        self.output_format = "bibleml"
        self.supported_content_types = ["biblical", "religious", "all"]
        self.version = "1.0"
        
        # BibleML namespace
        self.bibleml_ns = "http://www.bibletechnologies.net/2003/OSIS/namespace"
        
        # Structure detection patterns
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
        
        # Book code mapping
        self.book_codes = {
            'genesis': 'Gen',
            'exodus': 'Exod',
            'matthew': 'Matt',
            'mark': 'Mark',
            'luke': 'Luke',
            'john': 'John',
            # Add more as needed
        }
    
    def transform(self, book_storage: BookStorage, output_path: Optional[Path] = None, 
                 options: Dict[str, Any] = None) -> TransformationResult:
        """Transform book content to BibleML format.
        
        Args:
            book_storage: Source book storage
            output_path: Optional output file path
            options: Transformation options
            
        Returns:
            TransformationResult with BibleML content
        """
        options = options or {}
        self.line_mappings = LineMapping()
        
        try:
            # Generate BibleML XML
            bibleml_root = self._generate_bibleml(book_storage, options)
            
            # Convert to string
            xml_content = self._xml_to_string(bibleml_root)
            
            # Write to file if path provided
            file_path = None
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
                file_path = str(output_path)
                logger.info(f"BibleML XML written to {output_path}")
            
            # Prepare metadata
            metadata = {
                'book_id': book_storage.book_metadata.book_id,
                'bibleml_version': '2.0',
                'transformation_date': datetime.now().isoformat(),
                'source_pages': len(book_storage.pages),
                'xml_elements': len(list(bibleml_root.iter())),
                'options': options
            }
            
            return TransformationResult(
                success=True,
                output_format=self.output_format,
                content=xml_content,
                file_path=file_path,
                line_mappings=self.line_mappings,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"BibleML transformation failed: {e}")
            return TransformationResult(
                success=False,
                output_format=self.output_format,
                errors=[str(e)]
            )
    
    def _generate_bibleml(self, book_storage: BookStorage, options: Dict[str, Any]) -> ET.Element:
        """Generate BibleML XML structure.
        
        Args:
            book_storage: Source book storage
            options: Transformation options
            
        Returns:
            BibleML root element
        """
        # Create root OSIS element (BibleML is based on OSIS)
        osis_root = ET.Element("osis")
        osis_root.set("xmlns", self.bibleml_ns)
        osis_root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        osis_root.set("xsi:schemaLocation", 
                     f"{self.bibleml_ns} http://www.bibletechnologies.net/osisCore.2.1.1.xsd")
        
        # Create OSIS text element
        osis_text = ET.SubElement(osis_root, "osisText")
        osis_text.set("osisIDWork", book_storage.book_metadata.book_id)
        osis_text.set("osisRefWork", "bible")
        osis_text.set("xml:lang", "ml")  # Malayalam
        
        # Add header
        header = self._create_header(book_storage, options)
        osis_text.append(header)
        
        # Add book content
        book_div = self._create_book_div(book_storage, options)
        osis_text.append(book_div)
        
        return osis_root
    
    def _create_header(self, book_storage: BookStorage, options: Dict[str, Any]) -> ET.Element:
        """Create BibleML header.
        
        Args:
            book_storage: Source book storage
            options: Header options
            
        Returns:
            header element
        """
        header = ET.Element("header")
        
        # Work element
        work = ET.SubElement(header, "work")
        work.set("osisWork", book_storage.book_metadata.book_id)
        
        # Title
        title = ET.SubElement(work, "title")
        title.text = getattr(book_storage.book_metadata, 'title', f"Book {book_storage.book_metadata.book_id}")
        
        # Creator
        creator = ET.SubElement(work, "creator")
        creator.text = "Gundert Portal Scraper"
        creator.set("role", "encoder")
        
        # Date
        date = ET.SubElement(work, "date")
        date.text = datetime.now().strftime('%Y-%m-%d')
        date.set("event", "transcription")
        
        # Source
        if hasattr(book_storage.book_metadata, 'source_url') and book_storage.book_metadata.source_url:
            source = ET.SubElement(work, "source")
            source.text = book_storage.book_metadata.source_url
        
        # Language
        language = ET.SubElement(work, "language")
        language.text = "Malayalam"
        language.set("type", "x-bible")
        
        # Rights
        rights = ET.SubElement(work, "rights")
        rights.text = "Digital transcription from Gundert Portal"
        
        return header
    
    def _create_book_div(self, book_storage: BookStorage, options: Dict[str, Any]) -> ET.Element:
        """Create book division with content.
        
        Args:
            book_storage: Source book storage
            options: Content options
            
        Returns:
            div element for book
        """
        # Detect book code from metadata
        book_code = self._detect_book_code(book_storage.book_metadata)
        
        # Create book division
        book_div = ET.Element("div")
        book_div.set("type", "book")
        book_div.set("osisID", book_code)
        book_div.set("canonical", "true")
        
        # Add book title
        title = ET.SubElement(book_div, "title")
        title.set("type", "main")
        title.text = getattr(book_storage.book_metadata, 'title', f"Book {book_storage.book_metadata.book_id}")
        
        # Process content to create chapters
        chapters_data = self._extract_chapters_and_verses(book_storage, options)
        
        for chapter_num, chapter_content in chapters_data.items():
            chapter_div = self._create_chapter_div(book_code, chapter_num, chapter_content)
            book_div.append(chapter_div)
        
        return book_div
    
    def _create_chapter_div(self, book_code: str, chapter_num: int, 
                          chapter_content: Dict[str, Any]) -> ET.Element:
        """Create chapter division.
        
        Args:
            book_code: Book code (e.g., 'Gen', 'Matt')
            chapter_num: Chapter number
            chapter_content: Chapter content data
            
        Returns:
            chapter div element
        """
        chapter_div = ET.Element("chapter")
        chapter_div.set("osisID", f"{book_code}.{chapter_num}")
        chapter_div.set("n", str(chapter_num))
        
        # Add chapter title if needed
        title = ET.SubElement(chapter_div, "title")
        title.set("type", "chapter")
        title.text = f"അധ്യായം {chapter_num}"
        
        # Add verses
        for verse_data in chapter_content['verses']:
            verse_elem = self._create_verse_element(book_code, chapter_num, verse_data)
            chapter_div.append(verse_elem)
        
        return chapter_div
    
    def _create_verse_element(self, book_code: str, chapter_num: int, 
                            verse_data: Dict[str, Any]) -> ET.Element:
        """Create verse element.
        
        Args:
            book_code: Book code
            chapter_num: Chapter number
            verse_data: Verse data
            
        Returns:
            verse element
        """
        verse_num = verse_data['verse']
        verse_text = verse_data['text']
        
        verse = ET.Element("verse")
        verse.set("osisID", f"{book_code}.{chapter_num}.{verse_num}")
        verse.set("n", str(verse_num))
        verse.text = verse_text
        
        # Add line mapping
        self.line_mappings.add_mapping(
            original_page=verse_data['source']['page'],
            original_line=verse_data['source']['line'],
            transformed_location=f"{book_code}.{chapter_num}.{verse_num}",
            context={
                'type': 'verse',
                'book': book_code,
                'chapter': chapter_num,
                'verse': verse_num
            }
        )
        
        return verse
    
    def _extract_chapters_and_verses(self, book_storage: BookStorage, 
                                   options: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """Extract chapters and verses from book content.
        
        Args:
            book_storage: Source book storage
            options: Extraction options
            
        Returns:
            Dictionary of chapter data
        """
        chapters = {}
        current_chapter = 1
        current_verse = 1
        
        for page_num, page in enumerate(book_storage.pages, 1):
            if not page.transcript_info.get('available'):
                continue
            
            content_lines = self._get_page_lines(page)
            
            for line_num, line in enumerate(content_lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Detect structure
                chapter_match, verse_match = self._detect_structure(line)
                
                if chapter_match:
                    current_chapter = chapter_match
                    current_verse = 1  # Reset verse count for new chapter
                    
                    # Initialize chapter if not exists
                    if current_chapter not in chapters:
                        chapters[current_chapter] = {
                            'chapter': current_chapter,
                            'verses': []
                        }
                    continue
                
                if verse_match:
                    current_verse = verse_match
                
                # Extract verse content
                verse_text = self._clean_verse_content(line)
                if verse_text:
                    # Initialize chapter if not exists
                    if current_chapter not in chapters:
                        chapters[current_chapter] = {
                            'chapter': current_chapter,
                            'verses': []
                        }
                    
                    verse_data = {
                        'verse': current_verse,
                        'text': verse_text,
                        'source': {
                            'page': page_num,
                            'line': line_num
                        }
                    }
                    
                    chapters[current_chapter]['verses'].append(verse_data)
                    
                    # Auto-increment verse if no explicit verse detected
                    if not verse_match:
                        current_verse += 1
        
        return chapters
    
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
        
        # Clean and filter
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not self._is_metadata_line(line):
                cleaned_lines.append(line)
        
        return cleaned_lines
    
    def _detect_structure(self, line: str) -> Tuple[Optional[int], Optional[int]]:
        """Detect chapter and verse numbers.
        
        Args:
            line: Text line to analyze
            
        Returns:
            Tuple of (chapter_number, verse_number)
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
        """Clean verse content.
        
        Args:
            line: Raw verse line
            
        Returns:
            Cleaned verse text
        """
        # Remove verse/chapter markers
        for pattern in self.verse_patterns + self.chapter_patterns:
            line = re.sub(pattern, '', line).strip()
        
        return line.strip()
    
    def _detect_book_code(self, book_metadata) -> str:
        """Detect book code from metadata.
        
        Args:
            book_metadata: Book metadata
            
        Returns:
            Book code
        """
        title = getattr(book_metadata, 'title', '').lower()
        book_id = book_metadata.book_id.lower()
        
        search_text = f"{title} {book_id}"
        
        for book_name, code in self.book_codes.items():
            if book_name in search_text:
                return code
        
        # Generate generic code from book_id
        return f"Book_{book_metadata.book_id}"
    
    def _is_metadata_line(self, line: str) -> bool:
        """Check if line is metadata."""
        metadata_indicators = [
            'page', 'പേജ്', 'source:', 'url:', 'http', 'www.',
            '©', 'copyright', 'all rights reserved'
        ]
        
        line_lower = line.lower()
        return any(indicator in line_lower for indicator in metadata_indicators)
    
    def _xml_to_string(self, root: ET.Element) -> str:
        """Convert XML to formatted string.
        
        Args:
            root: XML root element
            
        Returns:
            Formatted XML string
        """
        xml_str = ET.tostring(root, encoding='unicode', method='xml')
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
    
    def is_compatible(self, book_storage: BookStorage) -> bool:
        """Check compatibility with biblical content.
        
        Args:
            book_storage: Book storage to check
            
        Returns:
            True if content appears biblical
        """
        if not super().is_compatible(book_storage):
            return False
        
        # Check for biblical indicators
        biblical_indicators = [
            'അധ്യായം', 'വാക്യം', 'chapter', 'verse'
        ]
        
        sample_text = ""
        for page in book_storage.pages[:3]:
            if page.transcript_info.get('available') and page.transcript_info.get('transcript_text'):
                sample_text += page.transcript_info['transcript_text']
        
        sample_lower = sample_text.lower()
        return any(indicator in sample_lower for indicator in biblical_indicators)
    
    def validate_input(self, book_storage: BookStorage) -> List[str]:
        """Validate input for BibleML transformation.
        
        Args:
            book_storage: Book storage to validate
            
        Returns:
            List of validation errors
        """
        errors = super().validate_input(book_storage)
        
        # Check for verse structure
        has_verses = False
        
        for page in book_storage.pages[:5]:
            if not page.transcript_info.get('available'):
                continue
            
            content_text = page.transcript_info.get('transcript_text', "")
            
            for pattern in self.verse_patterns:
                if re.search(pattern, content_text, re.MULTILINE):
                    has_verses = True
                    break
            
            if has_verses:
                break
        
        if not has_verses:
            errors.append("No biblical verse structure detected for BibleML format")
        
        return errors