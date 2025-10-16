"""TEI XML Transformer for Gundert Portal Scraper.

This module provides transformation from cached HTML to valid TEI P5 XML format.
The source content already contains TEI markup embedded in the HTML response.
This transformer extracts, validates, and properly formats the TEI content.

TEI (Text Encoding Initiative) is a standard for representing texts in digital form,
widely used in digital humanities and historical text preservation.
"""

from typing import Optional
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from datetime import datetime
import re


class TEITransformer:
    """Transform extracted content to valid TEI P5 XML format.
    
    This transformer:
    1. Extracts embedded TEI content from cached HTML
    2. Adds proper TEI P5 namespace and schema declarations
    3. Enhances TEI header with complete metadata
    4. Validates basic TEI structure
    5. Produces valid TEI P5 XML output
    
    The source already contains TEI markup within <tei> tags embedded in the HTML.
    We extract, enhance, and validate this existing TEI structure.
    """
    
    TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"
    TEI_SCHEMA = "http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng"
    
    def __init__(self):
        """Initialize the TEI transformer."""
        self.errors = []
        self.warnings = []
    
    def transform(self, cached_content: dict, output_path: Path, 
                  page_range: Optional[tuple[int, int]] = None) -> dict:
        """Transform cached HTML content to valid TEI XML.
        
        Args:
            cached_content: Dictionary with 'content' (HTML), 'book_id', 'metadata'
            output_path: Path to save the TEI XML file
            page_range: Optional (start_page, end_page) to limit output
            
        Returns:
            Dictionary with transformation statistics and validation results
            
        Raises:
            ValueError: If content is invalid or TEI structure not found
        """
        self.errors = []
        self.warnings = []
        
        # Extract HTML content
        html_content = cached_content.get('content', '')
        if not html_content:
            raise ValueError("No content found in cached data")
        
        # Parse HTML and find TEI content
        soup = BeautifulSoup(html_content, 'html.parser')
        transcript_div = soup.find('div', id='transcript-content')
        
        if not transcript_div:
            raise ValueError("No transcript-content div found in HTML")
        
        tei_root = transcript_div.find('tei')
        if not tei_root:
            raise ValueError("No TEI element found in transcript content")
        
        # Extract components
        tei_header = tei_root.find('teiheader')
        source_doc = tei_root.find('sourcedoc')
        
        if not tei_header or not source_doc:
            raise ValueError("TEI structure incomplete: missing teiHeader or sourceDoc")
        
        # Filter pages if range specified
        if page_range:
            start_page, end_page = page_range
            surfaces = source_doc.find_all('surface')
            filtered_surfaces = [
                s for s in surfaces 
                if start_page <= int(s.get('n', 0)) <= end_page
            ]
            # Create new sourceDoc with filtered surfaces
            new_source_doc = soup.new_tag('sourceDoc')
            new_source_doc['rend'] = source_doc.get('rend', '')
            for surface in filtered_surfaces:
                new_source_doc.append(surface)
            source_doc = new_source_doc
        
        # Enhance TEI header with metadata
        enhanced_header = self._enhance_tei_header(
            tei_header, 
            cached_content.get('metadata', {}),
            cached_content.get('book_id', 'unknown')
        )
        
        # Build complete TEI document
        tei_doc = self._build_tei_document(enhanced_header, source_doc)
        
        # Validate
        validation_results = self._validate_tei(tei_doc)
        
        # Format and save
        formatted_xml = self._format_tei_xml(tei_doc)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(formatted_xml, encoding='utf-8')
        
        # Calculate statistics
        stats = self._calculate_statistics(source_doc)
        
        return {
            'success': True,
            'output_path': str(output_path),
            'statistics': stats,
            'validation': validation_results,
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    def _enhance_tei_header(self, original_header: Tag, metadata: dict, book_id: str) -> Tag:
        """Enhance the TEI header with complete metadata.
        
        Args:
            original_header: Original teiHeader from source
            metadata: Additional metadata from extraction
            book_id: Book identifier
            
        Returns:
            Enhanced teiHeader element
        """
        soup = BeautifulSoup('', 'html.parser')
        header = soup.new_tag('teiHeader')
        
        # File Description
        file_desc = soup.new_tag('fileDesc')
        
        # Title Statement
        title_stmt = soup.new_tag('titleStmt')
        title = soup.new_tag('title')
        
        # Get title from metadata or original header
        title_text = metadata.get('title')
        if not title_text and original_header.find('title'):
            title_text = original_header.find('title').text
        if not title_text:
            title_text = 'Untitled'
        
        title.string = title_text
        title_stmt.append(title)
        
        # Add responsibility statement
        resp_stmt = soup.new_tag('respStmt')
        resp = soup.new_tag('resp')
        resp.string = "Digitization"
        resp_stmt.append(resp)
        name = soup.new_tag('name')
        name.string = "Universitätsbibliothek Tübingen"
        resp_stmt.append(name)
        title_stmt.append(resp_stmt)
        
        file_desc.append(title_stmt)
        
        # Publication Statement
        pub_stmt = soup.new_tag('publicationStmt')
        publisher = soup.new_tag('publisher')
        publisher.string = "OpenDigi - University of Tübingen"
        pub_stmt.append(publisher)
        
        pub_place = soup.new_tag('pubPlace')
        pub_place.string = "Tübingen, Germany"
        pub_stmt.append(pub_place)
        
        date_elem = soup.new_tag('date')
        date_elem['when'] = datetime.now().strftime('%Y-%m-%d')
        date_elem.string = datetime.now().strftime('%Y')
        pub_stmt.append(date_elem)
        
        # Availability
        avail = soup.new_tag('availability')
        avail_p = soup.new_tag('p')
        avail_p.string = "This work is protected by copyright or related property rights but available in Open Access."
        avail.append(avail_p)
        pub_stmt.append(avail)
        
        # ID number
        id_no = soup.new_tag('idno')
        id_no['type'] = 'OpenDigi'
        id_no.string = book_id
        pub_stmt.append(id_no)
        
        file_desc.append(pub_stmt)
        
        # Source Description
        source_desc = soup.new_tag('sourceDesc')
        source_p = soup.new_tag('p')
        source_p.string = f"Digitized manuscript from Gundert Collection (ID: {book_id})"
        source_desc.append(source_p)
        
        # Add bibliographic citation if available
        bibl = soup.new_tag('bibl')
        if metadata.get('title'):
            bibl_title = soup.new_tag('title')
            bibl_title.string = metadata['title']
            bibl.append(bibl_title)
        source_desc.append(bibl)
        
        file_desc.append(source_desc)
        header.append(file_desc)
        
        # Encoding Description
        encoding_desc = soup.new_tag('encodingDesc')
        proj_desc = soup.new_tag('projectDesc')
        proj_p = soup.new_tag('p')
        proj_p.string = "Digital edition created from manuscript digitization by OpenDigi platform"
        proj_desc.append(proj_p)
        encoding_desc.append(proj_desc)
        header.append(encoding_desc)
        
        # Profile Description
        profile_desc = soup.new_tag('profileDesc')
        lang_usage = soup.new_tag('langUsage')
        language = soup.new_tag('language')
        language['ident'] = metadata.get('language', 'ml')  # Malayalam default
        language.string = metadata.get('language_name', 'Malayalam')
        lang_usage.append(language)
        profile_desc.append(lang_usage)
        header.append(profile_desc)
        
        # Revision Description
        revision_desc = soup.new_tag('revisionDesc')
        change = soup.new_tag('change')
        change['when'] = datetime.now().strftime('%Y-%m-%d')
        change.string = "TEI file generated from OpenDigi digitization"
        revision_desc.append(change)
        header.append(revision_desc)
        
        return header
    
    def _build_tei_document(self, header: Tag, source_doc: Tag) -> str:
        """Build complete TEI document with proper namespace and declarations.
        
        Args:
            header: Enhanced teiHeader element
            source_doc: sourceDoc element with manuscript content
            
        Returns:
            Complete TEI document as string
        """
        # Build XML declaration and root element with namespace
        xml_decl = '<?xml version="1.0" encoding="UTF-8"?>\n'
        
        # TEI root with namespace
        tei_start = f'<TEI xmlns="{self.TEI_NAMESPACE}">\n'
        
        # Convert elements to strings and clean up
        header_str = str(header).replace('<teiheader>', '<teiHeader>').replace('</teiheader>', '</teiHeader>')
        source_str = str(source_doc).replace('<sourcedoc', '<sourceDoc').replace('</sourcedoc>', '</sourceDoc>')
        
        tei_end = '\n</TEI>'
        
        return xml_decl + tei_start + header_str + '\n' + source_str + tei_end
    
    def _format_tei_xml(self, tei_doc: str) -> str:
        """Format TEI XML with proper indentation.
        
        Args:
            tei_doc: TEI document string
            
        Returns:
            Formatted XML string
        """
        # Parse and prettify
        soup = BeautifulSoup(tei_doc, 'xml')
        
        # BeautifulSoup's prettify adds too much whitespace, so we'll do basic formatting
        formatted = soup.prettify()
        
        # Clean up excessive blank lines
        formatted = re.sub(r'\n\s*\n\s*\n', '\n\n', formatted)
        
        return formatted
    
    def _validate_tei(self, tei_doc: str) -> dict:
        """Validate basic TEI structure.
        
        Args:
            tei_doc: TEI document string
            
        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'checks': []
        }
        
        # Parse with XML parser
        try:
            soup = BeautifulSoup(tei_doc, 'xml')
        except Exception as e:
            results['valid'] = False
            results['checks'].append({'check': 'XML parsing', 'status': 'FAILED', 'message': str(e)})
            return results
        
        results['checks'].append({'check': 'XML parsing', 'status': 'PASSED', 'message': 'Valid XML'})
        
        # Check for required elements
        required_elements = [
            ('TEI', 'Root TEI element'),
            ('teiHeader', 'TEI Header'),
            ('fileDesc', 'File Description'),
            ('titleStmt', 'Title Statement'),
            ('publicationStmt', 'Publication Statement'),
            ('sourceDesc', 'Source Description'),
            ('sourceDoc', 'Source Document')
        ]
        
        for elem_name, description in required_elements:
            elem = soup.find(elem_name)
            if elem:
                results['checks'].append({
                    'check': description,
                    'status': 'PASSED',
                    'message': f'{elem_name} element found'
                })
            else:
                results['valid'] = False
                results['checks'].append({
                    'check': description,
                    'status': 'FAILED',
                    'message': f'{elem_name} element missing'
                })
                self.errors.append(f"Missing required element: {elem_name}")
        
        # Check namespace
        tei_elem = soup.find('TEI')
        if tei_elem and tei_elem.get('xmlns') == self.TEI_NAMESPACE:
            results['checks'].append({
                'check': 'TEI namespace',
                'status': 'PASSED',
                'message': f'Correct namespace: {self.TEI_NAMESPACE}'
            })
        else:
            self.warnings.append("TEI namespace not set or incorrect")
            results['checks'].append({
                'check': 'TEI namespace',
                'status': 'WARNING',
                'message': 'Namespace missing or incorrect'
            })
        
        return results
    
    def _calculate_statistics(self, source_doc: Tag) -> dict:
        """Calculate statistics about the TEI document.
        
        Args:
            source_doc: sourceDoc element
            
        Returns:
            Dictionary with statistics
        """
        surfaces = source_doc.find_all('surface')
        
        total_pages = len(surfaces)
        total_paragraphs = len(source_doc.find_all('p'))
        total_line_breaks = len(source_doc.find_all('lb'))
        
        # Count text content
        text_content = source_doc.get_text()
        total_chars = len(text_content)
        total_words = len(text_content.split())
        
        return {
            'total_pages': total_pages,
            'total_paragraphs': total_paragraphs,
            'total_line_breaks': total_line_breaks,
            'total_characters': total_chars,
            'total_words': total_words,
            'page_numbers': [int(s.get('n', 0)) for s in surfaces]
        }
    
    def is_compatible(self, cached_content: dict) -> bool:
        """Check if cached content is compatible with TEI transformation.
        
        Args:
            cached_content: Cached content dictionary
            
        Returns:
            True if content can be transformed to TEI
        """
        try:
            html_content = cached_content.get('content', '')
            if not html_content:
                return False
            
            soup = BeautifulSoup(html_content, 'html.parser')
            transcript_div = soup.find('div', id='transcript-content')
            if not transcript_div:
                return False
            
            tei_root = transcript_div.find('tei')
            return tei_root is not None
        except Exception:
            return False
    
    def validate_input(self, cached_content: dict) -> tuple[bool, list[str]]:
        """Validate input cached content.
        
        Args:
            cached_content: Cached content dictionary
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        if not isinstance(cached_content, dict):
            errors.append("Input must be a dictionary")
            return False, errors
        
        if 'content' not in cached_content:
            errors.append("Missing 'content' field")
        
        if 'book_id' not in cached_content:
            errors.append("Missing 'book_id' field")
        
        if errors:
            return False, errors
        
        # Check TEI structure
        if not self.is_compatible(cached_content):
            errors.append("Content does not contain valid TEI structure")
            return False, errors
        
        return True, []
