"""Advanced TEI XML transformer for scholarly digital editions."""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import re

from ..framework import BaseTransformer, TransformationResult, LineMapping
from ...storage.schemas import BookStorage, PageContent
from ...core.exceptions import TransformationError

logger = logging.getLogger(__name__)


class AdvancedTEITransformer(BaseTransformer):
    """Transforms content to TEI XML format with scholarly markup."""
    
    def __init__(self):
        super().__init__()
        self.output_format = "tei_xml"
        self.supported_content_types = ["all"]
        self.version = "1.0"
        
        # TEI namespace
        self.tei_ns = "http://www.tei-c.org/ns/1.0"
        
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
    
    def transform(self, book_storage: BookStorage, output_path: Optional[Path] = None, 
                 options: Dict[str, Any] = None) -> TransformationResult:
        """Transform book content to TEI XML format.
        
        Args:
            book_storage: Source book storage
            output_path: Optional output file path
            options: Transformation options
            
        Returns:
            TransformationResult with TEI XML content
        """
        options = options or {}
        self.line_mappings = LineMapping()
        
        try:
            # Generate TEI XML
            tei_root = self._generate_tei(book_storage, options)
            
            # Convert to string
            tei_content = self._xml_to_string(tei_root)
            
            # Write to file if path provided
            file_path = None
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(tei_content)
                file_path = str(output_path)
                logger.info(f"TEI XML written to {output_path}")
            
            # Prepare metadata
            metadata = {
                'book_id': book_storage.book_metadata.book_id,
                'tei_version': 'P5',
                'transformation_date': datetime.now().isoformat(),
                'source_pages': len(book_storage.pages),
                'xml_elements': len(list(tei_root.iter())),
                'options': options
            }
            
            return TransformationResult(
                success=True,
                output_format=self.output_format,
                content=tei_content,
                file_path=file_path,
                line_mappings=self.line_mappings,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"TEI transformation failed: {e}")
            return TransformationResult(
                success=False,
                output_format=self.output_format,
                errors=[str(e)]
            )
    
    def _generate_tei(self, book_storage: BookStorage, options: Dict[str, Any]) -> ET.Element:
        """Generate TEI XML structure.
        
        Args:
            book_storage: Source book storage
            options: Transformation options
            
        Returns:
            TEI root element
        """
        # Create root TEI element
        tei_root = ET.Element("TEI")
        tei_root.set("xmlns", self.tei_ns)
        
        # Add TEI header
        tei_header = self._create_tei_header(book_storage, options)
        tei_root.append(tei_header)
        
        # Add text element
        text_elem = ET.SubElement(tei_root, "text")
        text_elem.set("xml:lang", options.get('language', 'ml'))  # Malayalam
        
        # Add front matter if needed
        if options.get('include_front_matter', True):
            front_elem = self._create_front_matter(book_storage)
            text_elem.append(front_elem)
        
        # Add body
        body_elem = self._create_body(book_storage, options)
        text_elem.append(body_elem)
        
        # Add back matter if needed
        if options.get('include_back_matter', True):
            back_elem = self._create_back_matter(book_storage)
            text_elem.append(back_elem)
        
        return tei_root
    
    def _create_tei_header(self, book_storage: BookStorage, options: Dict[str, Any]) -> ET.Element:
        """Create TEI header with metadata.
        
        Args:
            book_storage: Source book storage
            options: Header options
            
        Returns:
            teiHeader element
        """
        header = ET.Element("teiHeader")
        
        # File description
        file_desc = ET.SubElement(header, "fileDesc")
        
        # Title statement
        title_stmt = ET.SubElement(file_desc, "titleStmt")
        
        title_elem = ET.SubElement(title_stmt, "title")
        title_elem.text = getattr(book_storage.book_metadata, 'title', f"Book {book_storage.book_metadata.book_id}")
        
        respStmt = ET.SubElement(title_stmt, "respStmt")
        resp_elem = ET.SubElement(respStmt, "resp")
        resp_elem.text = "Digital transcription"
        name_elem = ET.SubElement(respStmt, "name")
        name_elem.text = "Gundert Portal Scraper"
        
        # Publication statement
        pub_stmt = ET.SubElement(file_desc, "publicationStmt")
        pub_elem = ET.SubElement(pub_stmt, "p")
        pub_elem.text = f"Digital edition created {datetime.now().strftime('%Y-%m-%d')}"
        
        # Source description
        source_desc = ET.SubElement(file_desc, "sourceDesc")
        
        # Manuscript description
        ms_desc = ET.SubElement(source_desc, "msDesc")
        ms_identifier = ET.SubElement(ms_desc, "msIdentifier")
        
        ms_name = ET.SubElement(ms_identifier, "msName")
        ms_name.text = book_storage.book_metadata.book_id
        
        if hasattr(book_storage.book_metadata, 'source_url') and book_storage.book_metadata.source_url:
            repository = ET.SubElement(ms_identifier, "repository")
            repository.text = book_storage.book_metadata.source_url
        
        # Physical description
        phys_desc = ET.SubElement(ms_desc, "physDesc")
        extent = ET.SubElement(phys_desc, "extent")
        extent.text = f"{len(book_storage.pages)} pages"
        
        # Encoding description
        encoding_desc = ET.SubElement(header, "encodingDesc")
        proj_desc = ET.SubElement(encoding_desc, "projectDesc")
        proj_p = ET.SubElement(proj_desc, "p")
        proj_p.text = "Digital transcription of Malayalam manuscript from Gundert Portal"
        
        # Profile description
        profile_desc = ET.SubElement(header, "profileDesc")
        lang_usage = ET.SubElement(profile_desc, "langUsage")
        language = ET.SubElement(lang_usage, "language")
        language.set("ident", "ml")
        language.text = "Malayalam"
        
        # Revision description
        revision_desc = ET.SubElement(header, "revisionDesc")
        change = ET.SubElement(revision_desc, "change")
        change.set("when", datetime.now().strftime('%Y-%m-%d'))
        change.set("who", "Gundert Portal Scraper")
        change.text = "Initial digital transcription"
        
        return header
    
    def _create_front_matter(self, book_storage: BookStorage) -> ET.Element:
        """Create front matter section.
        
        Args:
            book_storage: Source book storage
            
        Returns:
            front element
        """
        front = ET.Element("front")
        
        # Title page
        title_page = ET.SubElement(front, "titlePage")
        
        doc_title = ET.SubElement(title_page, "docTitle")
        title_part = ET.SubElement(doc_title, "titlePart")
        title_part.text = getattr(book_storage.book_metadata, 'title', f"Book {book_storage.book_metadata.book_id}")
        
        # Additional front matter can be added here
        
        return front
    
    def _create_body(self, book_storage: BookStorage, options: Dict[str, Any]) -> ET.Element:
        """Create body with main content.
        
        Args:
            book_storage: Source book storage
            options: Body options
            
        Returns:
            body element
        """
        body = ET.Element("body")
        
        # Structure detection options
        detect_structure = options.get('detect_structure', True)
        preserve_pages = options.get('preserve_pages', True)
        
        current_div = None
        current_chapter = None
        
        for page_num, page in enumerate(book_storage.pages, 1):
            if not page.transcript_info.get('available'):
                continue
            
            # Create page break element if preserving page structure
            if preserve_pages:
                pb_elem = ET.SubElement(body if current_div is None else current_div, "pb")
                pb_elem.set("n", str(page_num))
                pb_elem.set("facs", f"page_{page_num}")
            
            # Process page content
            content_lines = self._get_page_lines(page)
            
            for line_num, line in enumerate(content_lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Detect structural elements if enabled
                chapter_match, verse_match = None, None
                if detect_structure:
                    chapter_match, verse_match = self._detect_structure(line)
                
                # Handle chapter
                if chapter_match:
                    current_chapter = chapter_match
                    
                    # Create new division for chapter
                    current_div = ET.SubElement(body, "div")
                    current_div.set("type", "chapter")
                    current_div.set("n", str(current_chapter))
                    
                    # Add chapter head
                    head_elem = ET.SubElement(current_div, "head")
                    head_elem.text = f"അധ്യായം {current_chapter}"
                    
                    # Add line mapping
                    self.line_mappings.add_mapping(
                        original_page=page_num,
                        original_line=line_num,
                        transformed_location=f"chapter_{current_chapter}_head",
                        context={'type': 'chapter', 'number': current_chapter}
                    )
                    continue
                
                # Handle verse or regular content
                if verse_match:
                    # Create verse element
                    container = current_div if current_div is not None else body
                    verse_elem = ET.SubElement(container, "ab")
                    verse_elem.set("type", "verse")
                    verse_elem.set("n", str(verse_match))
                    
                    # Clean content (remove verse number)
                    clean_content = self._clean_verse_content(line)
                    verse_elem.text = clean_content
                    
                    # Add line mapping
                    location = f"chapter_{current_chapter}_verse_{verse_match}" if current_chapter else f"verse_{verse_match}"
                    self.line_mappings.add_mapping(
                        original_page=page_num,
                        original_line=line_num,
                        transformed_location=location,
                        context={'type': 'verse', 'chapter': current_chapter, 'verse': verse_match}
                    )
                    
                else:
                    # Regular paragraph
                    container = current_div if current_div is not None else body
                    p_elem = ET.SubElement(container, "p")
                    p_elem.text = line
                    
                    # Add line mapping
                    p_index = len(list(container.iter('p'))) - 1
                    location = f"chapter_{current_chapter}_p_{p_index}" if current_chapter else f"p_{p_index}"
                    self.line_mappings.add_mapping(
                        original_page=page_num,
                        original_line=line_num,
                        transformed_location=location,
                        context={'type': 'paragraph', 'chapter': current_chapter}
                    )
        
        return body
    
    def _create_back_matter(self, book_storage: BookStorage) -> ET.Element:
        """Create back matter section.
        
        Args:
            book_storage: Source book storage
            
        Returns:
            back element
        """
        back = ET.Element("back")
        
        # Add appendix with transformation metadata
        div = ET.SubElement(back, "div")
        div.set("type", "appendix")
        
        head = ET.SubElement(div, "head")
        head.text = "Transformation Metadata"
        
        list_elem = ET.SubElement(div, "list")
        
        metadata_items = [
            ("Book ID", book_storage.book_metadata.book_id),
            ("Total Pages", str(len(book_storage.pages))),
            ("Transformation Date", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            ("Line Mappings", str(len(self.line_mappings.mappings)))
        ]
        
        for label, value in metadata_items:
            item = ET.SubElement(list_elem, "item")
            item.text = f"{label}: {value}"
        
        return back
    
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
    
    def _detect_structure(self, line: str) -> tuple:
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
        
        return line.strip()
    
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
    
    def _xml_to_string(self, root: ET.Element) -> str:
        """Convert XML element to formatted string.
        
        Args:
            root: XML root element
            
        Returns:
            Formatted XML string
        """
        # Add XML declaration and format
        xml_str = ET.tostring(root, encoding='unicode', method='xml')
        
        # Add XML declaration
        formatted_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
        
        # Basic formatting (could be enhanced with proper indentation)
        return formatted_xml
    
    def validate_input(self, book_storage: BookStorage) -> List[str]:
        """Validate input for TEI transformation.
        
        Args:
            book_storage: Book storage to validate
            
        Returns:
            List of validation errors
        """
        errors = super().validate_input(book_storage)
        
        # TEI works with any content, so minimal validation needed
        
        return errors