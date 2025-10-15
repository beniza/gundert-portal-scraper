"""Universal content scraper for Gundert Portal books."""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from bs4 import BeautifulSoup, Tag
import re

from ..core.connection import GundertPortalConnector
from ..core.exceptions import ExtractionError, PageNotFoundError, TranscriptNotAvailableError
from ..extraction.metadata import MetadataExtractor

logger = logging.getLogger(__name__)


class ContentScraper:
    """Universal content extraction engine with line-level preservation."""
    
    def __init__(self, connector: GundertPortalConnector, preserve_formatting: bool = True):
        """Initialize the content scraper.
        
        Args:
            connector: Active GundertPortalConnector instance
            preserve_formatting: Whether to preserve original line breaks and formatting
        """
        self.connector = connector
        self.preserve_formatting = preserve_formatting
        self.metadata_extractor = MetadataExtractor(connector)
        
        # Processing statistics
        self.stats = {
            'pages_processed': 0,
            'pages_with_transcripts': 0,
            'pages_with_images': 0,
            'total_lines_extracted': 0,
            'extraction_start_time': None,
            'extraction_end_time': None,
            'errors': []
        }
    
    def scrape_full_book(self, start_page: int = 1, end_page: Optional[int] = None, 
                        batch_size: int = 10) -> Dict[str, Any]:
        """Scrape the complete book with all content and metadata.
        
        Args:
            start_page: Starting page number (1-based)
            end_page: Ending page number (inclusive). If None, scrapes to end of book
            batch_size: Number of pages to process in each batch
            
        Returns:
            Complete book data with metadata, pages, and extraction statistics
            
        Raises:
            ExtractionError: If extraction fails
        """
        try:
            logger.info(f"Starting full book extraction: {self.connector.book_identifier.book_id}")
            self.stats['extraction_start_time'] = datetime.now()
            
            # Get book metadata
            logger.info("Extracting book metadata...")
            book_metadata = self.metadata_extractor.extract_full_metadata()
            
            # Determine page range
            total_pages = self.connector.get_page_count()
            if end_page is None:
                end_page = total_pages
            
            end_page = min(end_page, total_pages)
            logger.info(f"Extracting pages {start_page} to {end_page} (total: {total_pages})")
            
            # Check transcript availability
            transcript_available = self.connector.check_transcript_availability()
            logger.info(f"Transcript availability: {transcript_available}")
            
            # Process pages in batches
            all_pages = []
            for batch_start in range(start_page, end_page + 1, batch_size):
                batch_end = min(batch_start + batch_size - 1, end_page)
                logger.info(f"Processing batch: pages {batch_start}-{batch_end}")
                
                batch_pages = self.scrape_page_range(batch_start, batch_end)
                all_pages.extend(batch_pages)
                
                # Brief pause between batches to be respectful to server
                if batch_end < end_page:
                    time.sleep(1)
            
            # Compile final results
            self.stats['extraction_end_time'] = datetime.now()
            extraction_duration = (self.stats['extraction_end_time'] - self.stats['extraction_start_time']).total_seconds()
            
            book_data = {
                'format_version': '2.0',
                'extraction_timestamp': self.stats['extraction_end_time'].isoformat(),
                'book_metadata': book_metadata,
                'extraction_parameters': {
                    'start_page': start_page,
                    'end_page': end_page,
                    'batch_size': batch_size,
                    'preserve_formatting': self.preserve_formatting,
                    'transcript_extraction': transcript_available
                },
                'pages': all_pages,
                'statistics': {
                    **self.stats,
                    'extraction_duration_seconds': extraction_duration,
                    'pages_per_minute': round(self.stats['pages_processed'] / (extraction_duration / 60), 2) if extraction_duration > 0 else 0,
                    'success_rate': round(
                        (self.stats['pages_processed'] - len(self.stats['errors'])) / max(self.stats['pages_processed'], 1) * 100, 2
                    )
                }
            }
            
            logger.info(f"Full book extraction completed: {self.stats['pages_processed']} pages in {extraction_duration:.1f}s")
            return book_data
            
        except Exception as e:
            logger.error(f"Full book extraction failed: {e}")
            raise ExtractionError("full book extraction", str(e))
    
    def scrape_page_range(self, start_page: int, end_page: int) -> List[Dict[str, Any]]:
        """Scrape a range of pages.
        
        Args:
            start_page: Starting page number (1-based)
            end_page: Ending page number (inclusive)
            
        Returns:
            List of page data dictionaries
        """
        pages = []
        
        for page_num in range(start_page, end_page + 1):
            try:
                page_data = self.scrape_single_page(page_num)
                pages.append(page_data)
                
            except (PageNotFoundError, ExtractionError) as e:
                error_info = {
                    'page_number': page_num,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                self.stats['errors'].append(error_info)
                logger.warning(f"Failed to extract page {page_num}: {e}")
                
                # Add placeholder for failed page
                pages.append({
                    'page_number': page_num,
                    'extraction_success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        return pages
    
    def scrape_single_page(self, page_number: int) -> Dict[str, Any]:
        """Scrape a single page with all available content.
        
        Args:
            page_number: Page number to scrape (1-based)
            
        Returns:
            Complete page data dictionary
            
        Raises:
            PageNotFoundError: If page doesn't exist
            ExtractionError: If extraction fails
        """
        try:
            logger.debug(f"Scraping page {page_number}")
            page_start_time = datetime.now()
            
            # Initialize page data
            page_data = {
                'page_number': page_number,
                'extraction_timestamp': page_start_time.isoformat(),
                'extraction_success': True,
                'image_info': {},
                'transcript_info': {},
                'content_analysis': {}
            }
            
            # For OpenDigi, extract transcript content first (it has the most content)
            transcript_soup = None
            if self.connector.book_identifier.portal_type == 'opendigi':
                try:
                    # Load transcript tab content first
                    self.connector.navigate_to_page(page_number, "transcript")
                    self.connector.wait_for_content_load()
                    page_source = self.connector.get_current_page_source()
                    transcript_soup = BeautifulSoup(page_source, 'html.parser')
                except Exception as e:
                    logger.warning(f"Failed to load transcript content for page {page_number}: {e}")
            
            # Extract transcript information
            try:
                transcript_info = self.extract_transcript_with_lines(page_number, transcript_soup)
                page_data['transcript_info'] = transcript_info
                if transcript_info.get('available'):
                    self.stats['pages_with_transcripts'] += 1
                    self.stats['total_lines_extracted'] += transcript_info.get('line_count', 0)
            except Exception as e:
                logger.warning(f"Transcript extraction failed for page {page_number}: {e}")
                page_data['transcript_info'] = {'available': False, 'error': str(e)}
            
            # Extract image information (use transcript soup if available, otherwise load view tab)
            try:
                image_info = self.extract_image_links(page_number, transcript_soup)
                page_data['image_info'] = image_info
                if image_info.get('image_url'):
                    self.stats['pages_with_images'] += 1
            except Exception as e:
                logger.warning(f"Image extraction failed for page {page_number}: {e}")
                page_data['image_info'] = {'error': str(e)}
            
            # Perform content analysis
            try:
                content_analysis = self.analyze_page_content(page_data)
                page_data['content_analysis'] = content_analysis
            except Exception as e:
                logger.warning(f"Content analysis failed for page {page_number}: {e}")
                page_data['content_analysis'] = {'error': str(e)}
            
            # Calculate processing time
            processing_time = (datetime.now() - page_start_time).total_seconds()
            page_data['processing_time_seconds'] = processing_time
            
            self.stats['pages_processed'] += 1
            logger.debug(f"Page {page_number} extracted successfully in {processing_time:.2f}s")
            
            return page_data
            
        except Exception as e:
            logger.error(f"Single page extraction failed for page {page_number}: {e}")
            raise ExtractionError(f"page {page_number} extraction", str(e))
    
    def extract_image_links(self, page_number: int, soup: Optional[BeautifulSoup] = None) -> Dict[str, Any]:
        """Extract image information and links for a page.
        
        Args:
            page_number: Page number to extract images from
            soup: Optional pre-parsed BeautifulSoup object to avoid re-navigation
            
        Returns:
            Dictionary with image URLs and metadata
        """
        try:
            if soup is None:
                # Navigate to view tab only if we don't have pre-loaded content
                self.connector.navigate_to_page(page_number, "view")
                self.connector.wait_for_content_load()
                
                # Get page source
                page_source = self.connector.get_current_page_source()
                soup = BeautifulSoup(page_source, 'html.parser')
            
            image_info = self._extract_image_data(soup, page_number)
            
            return image_info
            
        except Exception as e:
            raise ExtractionError("image extraction", f"Page {page_number}: {str(e)}")
    
    def extract_transcript_with_lines(self, page_number: int, soup: Optional[BeautifulSoup] = None) -> Dict[str, Any]:
        """Extract transcript with line-level preservation.
        
        Args:
            page_number: Page number to extract transcript from
            soup: Optional pre-parsed BeautifulSoup object to avoid re-navigation
            
        Returns:
            Dictionary with transcript content and line structure
        """
        try:
            if soup is None:
                # Navigate to transcript tab only if we don't have pre-loaded content
                self.connector.navigate_to_page(page_number, "transcript")
                self.connector.wait_for_content_load()
                
                # Get page source
                page_source = self.connector.get_current_page_source()
                soup = BeautifulSoup(page_source, 'html.parser')
            
            transcript_info = self._extract_transcript_data(soup, page_number)
            
            return transcript_info
            
        except Exception as e:
            raise ExtractionError("transcript extraction", f"Page {page_number}: {str(e)}")
    
    def _extract_image_data(self, soup: BeautifulSoup, page_number: int) -> Dict[str, Any]:
        """Extract comprehensive image data from page HTML."""
        image_data = {
            'page_number': page_number,
            'images_found': [],
            'primary_image': None
        }
        
        # Enhanced image selectors for different portal types
        image_selectors = [
            # Main page images
            '.page-image img', '.book-page img', '.manuscript-image img',
            '#page-viewer img', '.viewer img', '.image-viewer img',
            '.page-content img', '.content img',
            
            # Generic image patterns
            'img[src*="image"]', 'img[src*="jp2"]', 'img[src*="jpeg"]',
            'img[src*="jpg"]', 'img[src*="png"]', 'img[src*="tif"]',
            'img[src*="page"]', 'img[src*="scan"]',
            
            # Portal-specific patterns
            'img[src*="opendigi"]', 'img[src*="gundert"]',
            
            # OpenDigi specific - look for all images and filter by content
            'img'
        ]
        
        found_images = []
        
        for selector in image_selectors:
            images = soup.select(selector)
            for img in images:
                if img.get('src'):
                    image_info = self._process_image_element(img, page_number)
                    if image_info and image_info not in found_images:
                        found_images.append(image_info)
        
        image_data['images_found'] = found_images
        
        # Identify primary image (largest or most relevant)
        if found_images:
            image_data['primary_image'] = self._identify_primary_image(found_images)
            
            # Add convenience fields from primary image
            primary = image_data['primary_image']
            image_data['image_url'] = primary['url']
            image_data['format'] = primary.get('format', 'unknown')
            image_data['estimated_dimensions'] = primary.get('dimensions', 'unknown')
        
        return image_data
    
    def _process_image_element(self, img_element: Tag, page_number: int) -> Optional[Dict[str, Any]]:
        """Process an individual image element."""
        src = img_element.get('src')
        if not src:
            return None
        
        # Filter out obvious UI/logo images early
        url_lower = src.lower()
        ui_indicators = ['logo', 'icon', 'button', 'ui', 'static/img', 'favicon', 'arrow', 'close', 'menu']
        if any(indicator in url_lower for indicator in ui_indicators):
            return None
        
        # Make URL absolute
        if src.startswith('/') and self.connector.book_identifier.base_url:
            src = self.connector.book_identifier.base_url + src
        elif src.startswith('//'):
            src = 'https:' + src
        
        image_info = {
            'url': src,
            'alt_text': img_element.get('alt', ''),
            'css_classes': img_element.get('class', [])
        }
        
        # Extract dimensions if available
        width = img_element.get('width')
        height = img_element.get('height')
        if width and height:
            image_info['dimensions'] = f"{width}x{height}"
        
        # Detect format from URL
        if '.jp2' in url_lower:
            image_info['format'] = 'JPEG2000'
        elif any(ext in url_lower for ext in ['.jpg', '.jpeg']):
            image_info['format'] = 'JPEG'
        elif '.png' in url_lower:
            image_info['format'] = 'PNG'
        elif any(ext in url_lower for ext in ['.tif', '.tiff']):
            image_info['format'] = 'TIFF'
        else:
            image_info['format'] = 'unknown'
        
        # Look for download/full-size links
        parent = img_element.parent
        if parent and parent.name == 'a' and parent.get('href'):
            image_info['download_url'] = parent['href']
        
        # Enhanced relevance scoring for content images
        score = 0
        
        # High scores for obvious content indicators
        if any(indicator in url_lower for indicator in ['page', 'scan', 'manuscript', 'jp2', 'tiff']):
            score += 15
        if any(cls in ['page-image', 'manuscript-image', 'main-image', 'content-image'] for cls in image_info['css_classes']):
            score += 12
        if str(page_number) in src:
            score += 8
        
        # Medium scores for likely content
        if any(indicator in url_lower for indicator in ['image', 'img', 'jpeg', 'jpg']):
            score += 5
        if len(src) > 50:  # Longer URLs often indicate content
            score += 3
        
        # Penalty for small images (likely UI elements)
        if width and height:
            try:
                w, h = int(width), int(height)
                if w < 100 or h < 100:  # Very small images
                    score -= 5
                elif w > 800 and h > 600:  # Large images (likely content)
                    score += 8
            except ValueError:
                pass
        
        image_info['relevance_score'] = score
        
        return image_info
    
    def _identify_primary_image(self, images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify the primary/main image from a list of images."""
        if not images:
            return {}
        
        # Sort by relevance score (descending)
        sorted_images = sorted(images, key=lambda x: x.get('relevance_score', 0), reverse=True)
        return sorted_images[0]
    
    def _extract_transcript_data(self, soup: BeautifulSoup, page_number: int) -> Dict[str, Any]:
        """Extract comprehensive transcript data with line preservation."""
        transcript_data = {
            'page_number': page_number,
            'available': False,
            'extraction_method': 'html_parsing'
        }
        
        # Enhanced transcript selectors (including more generic ones for OpenDigi)
        transcript_selectors = [
            '.transcript', '.transcription', '#transcript-content',
            '.text-content', '.page-text', '.manuscript-text',
            '.transcript-viewer', '.text-viewer', '.text-area',
            '.content-text', '.ocr-text', '.page-transcript'
        ]
        
        transcript_element = None
        for selector in transcript_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                transcript_element = element
                break
        
        # If specific selectors don't work, try to find the element with the most Malayalam content
        if not transcript_element:
            transcript_element = self._find_malayalam_content_element(soup)
        
        if not transcript_element:
            # Check for "no transcript" indicators
            self._check_transcript_unavailable_indicators(soup, transcript_data)
            return transcript_data
        
        # Extract transcript content with line preservation
        transcript_data['available'] = True
        
        if self.preserve_formatting:
            lines_data = self._extract_lines_with_formatting(transcript_element)
        else:
            lines_data = self._extract_lines_simple(transcript_element)
        
        transcript_data.update(lines_data)
        
        # Add content analysis
        content_analysis = self._analyze_transcript_content(transcript_data)
        transcript_data['content_analysis'] = content_analysis
        
        return transcript_data
    
    def _extract_lines_with_formatting(self, element: Tag) -> Dict[str, Any]:
        """Extract lines while preserving original formatting."""
        lines = []
        line_number = 1
        
        # Handle different HTML structures
        if element.find_all(['p', 'div', 'br']):
            # Structured content with paragraphs/divs
            for child in element.children:
                if hasattr(child, 'name'):
                    if child.name in ['p', 'div']:
                        text = child.get_text(strip=True)
                        if text:
                            lines.append({
                                'line_number': line_number,
                                'text': text,
                                'html_tag': child.name,
                                'css_classes': child.get('class', []),
                                'formatting_preserved': True
                            })
                            line_number += 1
                    elif child.name == 'br':
                        # Explicit line break
                        lines.append({
                            'line_number': line_number,
                            'text': '',
                            'html_tag': 'br',
                            'is_line_break': True
                        })
                        line_number += 1
                elif isinstance(child, str) and child.strip():
                    # Direct text content
                    text = child.strip()
                    if text:
                        lines.append({
                            'line_number': line_number,
                            'text': text,
                            'html_tag': 'text',
                            'formatting_preserved': True
                        })
                        line_number += 1
        else:
            # Plain text content - split by line breaks
            text_content = element.get_text()
            for line_text in text_content.split('\n'):
                line_text = line_text.strip()
                if line_text:
                    lines.append({
                        'line_number': line_number,
                        'text': line_text,
                        'html_tag': 'text',
                        'formatting_preserved': False
                    })
                    line_number += 1
        
        # Compile results
        raw_text = element.get_text()
        processed_text = '\n'.join(line['text'] for line in lines if line.get('text'))
        
        return {
            'lines': lines,
            'line_count': len([l for l in lines if l.get('text')]),
            'raw_html': str(element),
            'raw_text': raw_text,
            'processed_text': processed_text,
            'character_count': len(processed_text),
            'formatting_preserved': True
        }
    
    def _extract_lines_simple(self, element: Tag) -> Dict[str, Any]:
        """Extract lines with simple text processing."""
        raw_text = element.get_text()
        lines = []
        
        for i, line_text in enumerate(raw_text.split('\n'), 1):
            line_text = line_text.strip()
            if line_text:
                lines.append({
                    'line_number': i,
                    'text': line_text,
                    'formatting_preserved': False
                })
        
        processed_text = '\n'.join(line['text'] for line in lines)
        
        return {
            'lines': lines,
            'line_count': len(lines),
            'raw_text': raw_text,
            'processed_text': processed_text,
            'character_count': len(processed_text),
            'formatting_preserved': False
        }
    
    def _find_malayalam_content_element(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Find the element with the most Malayalam content (fallback for OpenDigi)."""
        import re
        malayalam_pattern = r'[\u0d00-\u0d7f]'
        
        # First, try OpenDigi-specific selectors based on our findings
        opendigi_selectors = [
            '#first-screen',  # Found in our testing
            'div[id*="screen"]',
            'div[class*="content"]',
            'div[class*="transcript"]'
        ]
        
        for selector in opendigi_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text()
                malayalam_chars = len(re.findall(malayalam_pattern, text))
                if malayalam_chars > 1000:  # Substantial content
                    logger.debug(f"Found Malayalam content using selector '{selector}': {malayalam_chars} chars")
                    return element
        
        # Fallback: find element with most Malayalam content
        max_malayalam = 0
        best_element = None
        
        # Check various container elements
        for element in soup.find_all(['div', 'section', 'article', 'main', 'body']):
            text = element.get_text()
            malayalam_chars = len(re.findall(malayalam_pattern, text))
            
            # Must have substantial Malayalam content (at least 500 characters)
            if malayalam_chars > 500 and malayalam_chars > max_malayalam:
                # Avoid the entire body unless it's the only option
                if element.name != 'body' or max_malayalam == 0:
                    max_malayalam = malayalam_chars
                    best_element = element
        
        # If we found an element with substantial content, look for its most content-rich child
        if best_element and best_element.name == 'body':
            # Try to find a more specific child element
            for child in best_element.find_all(recursive=False):
                child_text = child.get_text()
                child_malayalam = len(re.findall(malayalam_pattern, child_text))
                if child_malayalam > max_malayalam * 0.8:  # At least 80% of the total
                    best_element = child
                    break
        
        if best_element and max_malayalam > 1000:
            logger.debug(f"Found Malayalam content element: {best_element.name} with {max_malayalam} chars")
        
        return best_element
    
    def _check_transcript_unavailable_indicators(self, soup: BeautifulSoup, transcript_data: Dict) -> None:
        """Check for indicators that transcript is not available."""
        unavailable_indicators = [
            'no transcript', 'nicht verfügbar', 'not available',
            'kein transkript', 'transcription not available',
            'no text available', 'text nicht verfügbar'
        ]
        
        page_text = soup.get_text().lower()
        for indicator in unavailable_indicators:
            if indicator in page_text:
                transcript_data['unavailable_reason'] = indicator
                transcript_data['notes'] = [f'Transcript marked as unavailable: {indicator}']
                break
    
    def _analyze_transcript_content(self, transcript_data: Dict) -> Dict[str, Any]:
        """Analyze transcript content characteristics."""
        if not transcript_data.get('available'):
            return {'error': 'No transcript available for analysis'}
        
        text = transcript_data.get('processed_text', '')
        lines = transcript_data.get('lines', [])
        
        analysis = {
            'text_statistics': {
                'total_characters': len(text),
                'total_lines': len(lines),
                'non_empty_lines': len([l for l in lines if l.get('text', '').strip()]),
                'avg_line_length': round(len(text) / max(len(lines), 1), 2)
            },
            'language_characteristics': self._analyze_language_characteristics(text),
            'content_structure': self._analyze_content_structure(lines),
            'quality_indicators': self._assess_transcript_quality(text, lines)
        }
        
        return analysis
    
    def _analyze_language_characteristics(self, text: str) -> Dict[str, Any]:
        """Analyze language characteristics of the text."""
        characteristics = {}
        
        # Character set analysis
        malayalam_chars = len([c for c in text if '\u0d00' <= c <= '\u0d7f'])
        total_chars = len(text.replace(' ', ''))  # Exclude spaces
        
        if total_chars > 0:
            characteristics['malayalam_percentage'] = round(malayalam_chars / total_chars * 100, 2)
        else:
            characteristics['malayalam_percentage'] = 0
        
        # Common patterns
        characteristics['has_verse_numbers'] = bool(re.search(r'\d+\.\s', text))
        characteristics['has_chapter_markers'] = bool(re.search(r'(chapter|അധ്യായം|\d+\s*അധ്യായം)', text, re.IGNORECASE))
        characteristics['has_malayalam_content'] = malayalam_chars > 0
        
        return characteristics
    
    def _analyze_content_structure(self, lines: List[Dict]) -> Dict[str, Any]:
        """Analyze the structural characteristics of the content."""
        structure = {
            'line_types': {},
            'formatting_elements': {},
            'structural_patterns': []
        }
        
        # Analyze line types
        for line in lines:
            html_tag = line.get('html_tag', 'unknown')
            structure['line_types'][html_tag] = structure['line_types'].get(html_tag, 0) + 1
        
        # Look for structural patterns
        text_lines = [line.get('text', '') for line in lines if line.get('text')]
        
        # Check for verse patterns
        verse_pattern_count = len([line for line in text_lines if re.match(r'^\d+\.?\s', line)])
        if verse_pattern_count > len(text_lines) * 0.3:
            structure['structural_patterns'].append('verse_numbering')
        
        # Check for heading patterns
        heading_pattern_count = len([line for line in text_lines if len(line) < 50 and line.isupper()])
        if heading_pattern_count > 0:
            structure['structural_patterns'].append('headings')
        
        return structure
    
    def _assess_transcript_quality(self, text: str, lines: List[Dict]) -> Dict[str, Any]:
        """Assess the quality of the transcript."""
        quality = {
            'completeness_score': 0,
            'quality_indicators': [],
            'potential_issues': []
        }
        
        # Completeness assessment
        if len(text) > 100:
            quality['completeness_score'] += 40
        if len(lines) > 5:
            quality['completeness_score'] += 30
        if any('[' in line.get('text', '') or ']' in line.get('text', '') for line in lines):
            quality['completeness_score'] += 20  # Editorial marks suggest careful transcription
            quality['quality_indicators'].append('editorial_marks_present')
        
        # Check for potential issues
        if len(text) < 50:
            quality['potential_issues'].append('very_short_content')
        
        empty_lines_ratio = len([l for l in lines if not l.get('text', '').strip()]) / max(len(lines), 1)
        if empty_lines_ratio > 0.5:
            quality['potential_issues'].append('high_empty_line_ratio')
        
        # OCR quality indicators
        if '?' in text or '�' in text:
            quality['potential_issues'].append('possible_ocr_errors')
        
        quality['completeness_score'] = min(quality['completeness_score'], 100)
        
        return quality
    
    def analyze_page_content(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall page content characteristics."""
        analysis = {
            'content_availability': {
                'has_image': bool(page_data.get('image_info', {}).get('image_url')),
                'has_transcript': bool(page_data.get('transcript_info', {}).get('available')),
                'extraction_success': page_data.get('extraction_success', False)
            },
            'content_quality': {},
            'recommendations': []
        }
        
        # Quality assessment
        if analysis['content_availability']['has_image'] and analysis['content_availability']['has_transcript']:
            analysis['content_quality']['completeness'] = 'high'
            analysis['recommendations'].append('Full content available - suitable for comprehensive analysis')
        elif analysis['content_availability']['has_image']:
            analysis['content_quality']['completeness'] = 'medium'
            analysis['recommendations'].append('Image available but no transcript - consider OCR processing')
        elif analysis['content_availability']['has_transcript']:
            analysis['content_quality']['completeness'] = 'medium'
            analysis['recommendations'].append('Transcript available but no image - text-only analysis possible')
        else:
            analysis['content_quality']['completeness'] = 'low'
            analysis['recommendations'].append('Limited content available - page may need manual review')
        
        # Add transcript-specific analysis if available
        transcript_info = page_data.get('transcript_info', {})
        if transcript_info.get('available') and transcript_info.get('content_analysis'):
            analysis['transcript_analysis'] = transcript_info['content_analysis']
        
        return analysis
    
    def get_extraction_statistics(self) -> Dict[str, Any]:
        """Get current extraction statistics.
        
        Returns:
            Dictionary with extraction statistics and performance metrics
        """
        current_time = datetime.now()
        
        stats = dict(self.stats)
        
        if stats['extraction_start_time']:
            if stats['extraction_end_time']:
                duration = (stats['extraction_end_time'] - stats['extraction_start_time']).total_seconds()
            else:
                duration = (current_time - stats['extraction_start_time']).total_seconds()
            
            stats['extraction_duration_seconds'] = duration
            stats['pages_per_minute'] = round(stats['pages_processed'] / (duration / 60), 2) if duration > 0 else 0
        
        stats['success_rate'] = round(
            (stats['pages_processed'] - len(stats['errors'])) / max(stats['pages_processed'], 1) * 100, 2
        ) if stats['pages_processed'] > 0 else 0
        
        return stats