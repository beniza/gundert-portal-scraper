"""Format converters for different output types."""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from .schemas import BookStorage, BookMetadata, PageContent, TEISchema


class BaseConverter:
    """Base class for format converters."""
    
    def __init__(self):
        self.format_name = "base"
    
    def convert(self, book_storage: BookStorage) -> str:
        """Convert BookStorage to target format."""
        raise NotImplementedError("Subclasses must implement convert method")


class TEIConverter(BaseConverter):
    """Convert to TEI XML format for scholarly digital editions."""
    
    def __init__(self):
        super().__init__()
        self.format_name = "tei_xml"
    
    def convert_to_tei(self, book_storage: BookStorage) -> str:
        """Convert BookStorage to TEI XML."""
        
        # Generate TEI header
        header = TEISchema.generate_tei_header(
            book_storage.book_metadata,
            book_storage.extraction_timestamp
        )
        
        # Generate text body
        body_parts = []
        body_parts.append('  <text>')
        body_parts.append('    <body>')
        
        # Group pages into logical divisions if possible
        if self._is_biblical_content(book_storage.book_metadata):
            body_parts.extend(self._generate_biblical_structure(book_storage.pages))
        else:
            body_parts.extend(self._generate_generic_structure(book_storage.pages))
        
        body_parts.append('    </body>')
        body_parts.append('  </text>')
        body_parts.append('</TEI>')
        
        # Combine all parts
        tei_xml = header + '\n\n' + '\n'.join(body_parts)
        
        return tei_xml
    
    def _is_biblical_content(self, metadata: BookMetadata) -> bool:
        """Check if content appears to be biblical."""
        content_type = (metadata.content_type or '').lower()
        title = (metadata.title or '').lower()
        
        biblical_indicators = ['bible', 'testament', 'gospel', 'matthew', 'mark', 'luke', 'john', 'psalms']
        
        return any(indicator in content_type or indicator in title for indicator in biblical_indicators)
    
    def _generate_biblical_structure(self, pages: List[PageContent]) -> List[str]:
        """Generate biblical structure with chapters and verses."""
        body_parts = []
        body_parts.append('      <div type="biblical_text">')
        
        current_chapter = None
        
        for page in pages:
            if not page.transcript_info.get('available'):
                continue
            
            # Add page marker
            body_parts.append(f'        <pb n="{page.page_number}"/>')
            
            # Add image reference if available
            if page.image_info.get('image_url'):
                body_parts.append(f'        <graphic url="{page.image_info["image_url"]}"/>')
            
            lines = page.transcript_info.get('lines', [])
            
            for line in lines:
                line_text = line.get('text', '').strip()
                if not line_text:
                    continue
                
                # Check for chapter markers
                chapter_match = re.search(r'(\d+)\s*അധ്യായം|Chapter\s*(\d+)', line_text, re.IGNORECASE)
                if chapter_match:
                    chapter_num = chapter_match.group(1) or chapter_match.group(2)
                    
                    # Close previous chapter
                    if current_chapter:
                        body_parts.append('        </div>')
                    
                    # Start new chapter
                    body_parts.append(f'        <div type="chapter" n="{chapter_num}">')
                    body_parts.append(f'          <head>{self._escape_xml(line_text)}</head>')
                    current_chapter = chapter_num
                    continue
                
                # Check for verse numbers
                verse_match = re.search(r'^(\d+)\.?\s*(.+)', line_text)
                if verse_match:
                    verse_num = verse_match.group(1)
                    verse_text = verse_match.group(2)
                    body_parts.append(f'          <ab n="{verse_num}">{self._escape_xml(verse_text)}</ab>')
                else:
                    # Regular text line
                    body_parts.append(f'          <l n="{line.get("line_number", "")}">{self._escape_xml(line_text)}</l>')
        
        # Close final chapter
        if current_chapter:
            body_parts.append('        </div>')
        
        body_parts.append('      </div>')
        
        return body_parts
    
    def _generate_generic_structure(self, pages: List[PageContent]) -> List[str]:
        """Generate generic structure for non-biblical content."""
        body_parts = []
        body_parts.append('      <div type="manuscript">')
        
        for page in pages:
            if not page.transcript_info.get('available'):
                continue
            
            body_parts.append(f'        <div type="page" n="{page.page_number}">')
            body_parts.append(f'          <pb n="{page.page_number}"/>')
            
            # Add image reference if available
            if page.image_info.get('image_url'):
                body_parts.append(f'          <graphic url="{page.image_info["image_url"]}"/>')
            
            lines = page.transcript_info.get('lines', [])
            
            for line in lines:
                line_text = line.get('text', '').strip()
                if line_text:
                    body_parts.append(f'          <l n="{line.get("line_number", "")}">{self._escape_xml(line_text)}</l>')
                elif line.get('is_line_break'):
                    body_parts.append('          <lb/>')
            
            body_parts.append('        </div>')
        
        body_parts.append('      </div>')
        
        return body_parts
    
    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')


class PlainTextConverter(BaseConverter):
    """Convert to plain text format."""
    
    def __init__(self):
        super().__init__()
        self.format_name = "plain_text"
    
    def convert_to_text(self, book_storage: BookStorage) -> str:
        """Convert BookStorage to plain text."""
        
        text_parts = []
        
        # Add header with metadata
        metadata = book_storage.book_metadata
        text_parts.append(self._generate_text_header(metadata))
        text_parts.append('')
        
        # Add content
        for page in book_storage.pages:
            if not page.transcript_info.get('available'):
                continue
            
            # Add page separator
            text_parts.append(f'--- Page {page.page_number} ---')
            text_parts.append('')
            
            lines = page.transcript_info.get('lines', [])
            
            for line in lines:
                line_text = line.get('text', '').strip()
                if line_text:
                    text_parts.append(line_text)
                elif line.get('is_line_break'):
                    text_parts.append('')
            
            text_parts.append('')
        
        # Add footer with extraction info
        text_parts.append(self._generate_text_footer(book_storage))
        
        return '\n'.join(text_parts)
    
    def _generate_text_header(self, metadata: BookMetadata) -> str:
        """Generate plain text header with metadata."""
        header_parts = []
        header_parts.append('=' * 60)
        header_parts.append(f'TITLE: {metadata.title or "Unknown Title"}')
        
        if metadata.author:
            header_parts.append(f'AUTHOR: {metadata.author}')
        if metadata.editor:
            header_parts.append(f'EDITOR: {metadata.editor}')
        if metadata.publication_year:
            header_parts.append(f'YEAR: {metadata.publication_year}')
        if metadata.publication_place:
            header_parts.append(f'PLACE: {metadata.publication_place}')
        
        header_parts.append(f'BOOK ID: {metadata.book_id}')
        header_parts.append(f'CONTENT TYPE: {metadata.content_type or "Unknown"}')
        header_parts.append(f'PRIMARY LANGUAGE: {metadata.primary_language or "Unknown"}')
        
        if metadata.page_count:
            header_parts.append(f'PAGES: {metadata.page_count}')
        
        header_parts.append('=' * 60)
        
        return '\n'.join(header_parts)
    
    def _generate_text_footer(self, book_storage: BookStorage) -> str:
        """Generate plain text footer with extraction info."""
        footer_parts = []
        footer_parts.append('-' * 60)
        footer_parts.append('EXTRACTION INFORMATION')
        footer_parts.append('-' * 60)
        footer_parts.append(f'Extracted: {book_storage.extraction_timestamp}')
        footer_parts.append(f'Format Version: {book_storage.format_version}')
        footer_parts.append(f'Pages Processed: {book_storage.statistics.pages_processed}')
        footer_parts.append(f'Success Rate: {book_storage.statistics.success_rate}%')
        footer_parts.append(f'Total Lines: {book_storage.statistics.total_lines_extracted}')
        footer_parts.append('')
        footer_parts.append('Generated by Gundert Portal Scraper')
        footer_parts.append('-' * 60)
        
        return '\n'.join(footer_parts)


class MarkdownConverter(BaseConverter):
    """Convert to Markdown format."""
    
    def __init__(self):
        super().__init__()
        self.format_name = "markdown"
    
    def convert_to_markdown(self, book_storage: BookStorage) -> str:
        """Convert BookStorage to Markdown."""
        
        md_parts = []
        
        # Add YAML frontmatter
        md_parts.append(self._generate_yaml_frontmatter(book_storage.book_metadata))
        md_parts.append('')
        
        # Add title and metadata
        metadata = book_storage.book_metadata
        md_parts.append(f'# {metadata.title or "Unknown Title"}')
        md_parts.append('')
        
        if metadata.author:
            md_parts.append(f'**Author:** {metadata.author}')
        if metadata.editor:
            md_parts.append(f'**Editor:** {metadata.editor}')
        if metadata.publication_year:
            md_parts.append(f'**Year:** {metadata.publication_year}')
        if metadata.content_type:
            md_parts.append(f'**Content Type:** {metadata.content_type}')
        if metadata.primary_language:
            md_parts.append(f'**Language:** {metadata.primary_language}')
        
        md_parts.append('')
        md_parts.append('---')
        md_parts.append('')
        
        # Add content
        current_chapter = None
        
        for page in book_storage.pages:
            if not page.transcript_info.get('available'):
                continue
            
            lines = page.transcript_info.get('lines', [])
            
            for line in lines:
                line_text = line.get('text', '').strip()
                if not line_text:
                    continue
                
                # Check for chapter markers
                chapter_match = re.search(r'(\d+)\s*അധ്യായം|Chapter\s*(\d+)', line_text, re.IGNORECASE)
                if chapter_match:
                    chapter_num = chapter_match.group(1) or chapter_match.group(2)
                    md_parts.append(f'## Chapter {chapter_num}')
                    md_parts.append('')
                    current_chapter = chapter_num
                    continue
                
                # Check for verse numbers
                verse_match = re.search(r'^(\d+)\.?\s*(.+)', line_text)
                if verse_match:
                    verse_num = verse_match.group(1)
                    verse_text = verse_match.group(2)
                    md_parts.append(f'**{verse_num}.** {verse_text}')
                else:
                    # Regular text line
                    md_parts.append(line_text)
                
                md_parts.append('')
            
            # Add page break comment
            md_parts.append(f'<!-- Page {page.page_number} -->')
            md_parts.append('')
        
        # Add extraction info
        md_parts.append('---')
        md_parts.append('')
        md_parts.append('## Extraction Information')
        md_parts.append('')
        md_parts.append(f'- **Extracted:** {book_storage.extraction_timestamp}')
        md_parts.append(f'- **Pages Processed:** {book_storage.statistics.pages_processed}')
        md_parts.append(f'- **Success Rate:** {book_storage.statistics.success_rate}%')
        md_parts.append(f'- **Total Lines:** {book_storage.statistics.total_lines_extracted}')
        md_parts.append('')
        md_parts.append('*Generated by Gundert Portal Scraper*')
        
        return '\n'.join(md_parts)
    
    def _generate_yaml_frontmatter(self, metadata: BookMetadata) -> str:
        """Generate YAML frontmatter for Markdown."""
        yaml_parts = []
        yaml_parts.append('---')
        yaml_parts.append(f'title: "{metadata.title or "Unknown Title"}"')
        
        if metadata.author:
            yaml_parts.append(f'author: "{metadata.author}"')
        if metadata.editor:
            yaml_parts.append(f'editor: "{metadata.editor}"')
        if metadata.publication_year:
            yaml_parts.append(f'year: "{metadata.publication_year}"')
        if metadata.publication_place:
            yaml_parts.append(f'place: "{metadata.publication_place}"')
        
        yaml_parts.append(f'book_id: "{metadata.book_id}"')
        yaml_parts.append(f'portal_type: "{metadata.portal_type}"')
        
        if metadata.content_type:
            yaml_parts.append(f'content_type: "{metadata.content_type}"')
        if metadata.primary_language:
            yaml_parts.append(f'language: "{metadata.primary_language}"')
        if metadata.secondary_languages:
            yaml_parts.append(f'secondary_languages: {metadata.secondary_languages}')
        if metadata.subject_keywords:
            yaml_parts.append(f'keywords: {metadata.subject_keywords}')
        
        if metadata.page_count:
            yaml_parts.append(f'pages: {metadata.page_count}')
        
        yaml_parts.append(f'extraction_date: "{datetime.now().strftime("%Y-%m-%d")}"')
        yaml_parts.append('---')
        
        return '\n'.join(yaml_parts)


class USFMConverter(BaseConverter):
    """Convert to USFM (Unified Standard Format Markers) for biblical texts."""
    
    def __init__(self):
        super().__init__()
        self.format_name = "usfm"
    
    def convert_to_usfm(self, book_storage: BookStorage) -> str:
        """Convert BookStorage to USFM format."""
        
        usfm_parts = []
        metadata = book_storage.book_metadata
        
        # USFM header
        usfm_parts.append(f'\\id {self._get_book_code(metadata.title)} {metadata.title or "Unknown"}')
        usfm_parts.append(f'\\h {metadata.title or "Unknown"}')
        usfm_parts.append(f'\\toc1 {metadata.title or "Unknown"}')
        usfm_parts.append(f'\\toc2 {metadata.title or "Unknown"}')
        usfm_parts.append(f'\\toc3 {self._get_book_code(metadata.title)}')
        usfm_parts.append('')
        
        current_chapter = None
        
        for page in book_storage.pages:
            if not page.transcript_info.get('available'):
                continue
            
            lines = page.transcript_info.get('lines', [])
            
            for line in lines:
                line_text = line.get('text', '').strip()
                if not line_text:
                    continue
                
                # Check for chapter markers
                chapter_match = re.search(r'(\d+)\s*അധ്യായം|Chapter\s*(\d+)', line_text, re.IGNORECASE)
                if chapter_match:
                    chapter_num = chapter_match.group(1) or chapter_match.group(2)
                    usfm_parts.append(f'\\c {chapter_num}')
                    usfm_parts.append('')
                    current_chapter = chapter_num
                    continue
                
                # Check for verse numbers
                verse_match = re.search(r'^(\d+)\.?\s*(.+)', line_text)
                if verse_match:
                    verse_num = verse_match.group(1)
                    verse_text = verse_match.group(2)
                    usfm_parts.append(f'\\v {verse_num} {verse_text}')
                else:
                    # Regular text line (treat as continuation)
                    usfm_parts.append(line_text)
        
        return '\n'.join(usfm_parts)
    
    def _get_book_code(self, title: str) -> str:
        """Get USFM book code from title."""
        if not title:
            return 'XXX'
        
        title_lower = title.lower()
        
        # Common biblical book mappings
        book_codes = {
            'matthew': 'MAT',
            'mark': 'MRK', 
            'luke': 'LUK',
            'john': 'JHN',
            'acts': 'ACT',
            'romans': 'ROM',
            'genesis': 'GEN',
            'exodus': 'EXO',
            'psalms': 'PSA'
        }
        
        for book_name, code in book_codes.items():
            if book_name in title_lower:
                return code
        
        # Default: use first 3 letters
        return title[:3].upper()