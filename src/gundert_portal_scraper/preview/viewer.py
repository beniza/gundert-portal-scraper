"""Preview functionality for Gundert Portal books."""

import logging
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from datetime import datetime

from ..core.connection import GundertPortalConnector
from ..core.exceptions import ExtractionError, PageNotFoundError
from ..extraction.metadata import MetadataExtractor

logger = logging.getLogger(__name__)


class SinglePageViewer:
    """Preview individual pages and metadata before full extraction."""
    
    def __init__(self, connector: GundertPortalConnector):
        """Initialize the page viewer.
        
        Args:
            connector: Active GundertPortalConnector instance
        """
        self.connector = connector
        self.metadata_extractor = MetadataExtractor(connector)
        self._page_cache = {}
    
    def preview_metadata(self) -> Dict[str, Any]:
        """Preview book metadata without full extraction.
        
        Returns:
            Dictionary with essential metadata and preview info
            
        Raises:
            ExtractionError: If metadata preview fails
        """
        try:
            logger.info(f"Previewing metadata for book: {self.connector.book_identifier.book_id}")
            
            # Get basic book info
            book_info = self.connector.get_book_info()
            
            # Get essential metadata
            basic_info = self.metadata_extractor.get_basic_info()
            
            # Detect content characteristics
            content_type = self.metadata_extractor.detect_content_type()
            languages = self.metadata_extractor.get_languages()
            
            # Estimate extraction parameters
            page_count = self.connector.get_page_count()
            transcript_available = self.connector.check_transcript_availability()
            
            preview_data = {
                'preview_timestamp': datetime.now().isoformat(),
                'book_info': book_info,
                'metadata_summary': basic_info,
                'content_type': content_type,
                'languages': languages,
                'extraction_estimates': {
                    'total_pages': page_count,
                    'transcript_available': transcript_available,
                    'estimated_duration_minutes': self._estimate_extraction_time(page_count, transcript_available)
                },
                'sample_availability': {
                    'can_preview_images': True,
                    'can_preview_transcripts': transcript_available,
                    'recommended_sample_pages': self._get_recommended_sample_pages(page_count)
                }
            }
            
            logger.info(f"Metadata preview completed for {self.connector.book_identifier.book_id}")
            return preview_data
            
        except Exception as e:
            logger.error(f"Metadata preview failed: {e}")
            raise ExtractionError("metadata preview", str(e))
    
    def preview_page_image(self, page_number: int) -> Dict[str, str]:
        """Preview the image for a specific page.
        
        Args:
            page_number: Page number to preview (1-based)
            
        Returns:
            Dictionary with image information
            
        Raises:
            PageNotFoundError: If page doesn't exist
            ExtractionError: If image preview fails
        """
        try:
            logger.info(f"Previewing image for page {page_number}")
            
            # Navigate to the page
            page_url = self.connector.navigate_to_page(page_number, "view")
            self.connector.wait_for_content_load()
            
            # Get page source and extract image information
            page_source = self.connector.get_current_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')
            
            image_info = self._extract_image_info(soup, page_number)
            
            if not image_info.get('image_url'):
                raise ExtractionError("image preview", f"No image found for page {page_number}")
            
            image_preview = {
                'page_number': page_number,
                'page_url': page_url,
                'image_url': image_info['image_url'],
                'image_format': image_info.get('format', 'unknown'),
                'image_dimensions': image_info.get('dimensions', 'unknown'),
                'thumbnail_url': image_info.get('thumbnail_url'),
                'download_url': image_info.get('download_url'),
                'metadata': {
                    'extracted_at': datetime.now().isoformat(),
                    'source_portal': self.connector.book_identifier.portal_type
                }
            }
            
            logger.info(f"Image preview completed for page {page_number}")
            return image_preview
            
        except Exception as e:
            if isinstance(e, (PageNotFoundError, ExtractionError)):
                raise
            logger.error(f"Image preview failed for page {page_number}: {e}")
            raise ExtractionError("image preview", f"Page {page_number}: {str(e)}")
    
    def preview_page_transcript(self, page_number: int) -> Dict[str, Any]:
        """Preview the transcript for a specific page.
        
        Args:
            page_number: Page number to preview (1-based)
            
        Returns:
            Dictionary with transcript information
            
        Raises:
            PageNotFoundError: If page doesn't exist
            ExtractionError: If transcript preview fails
        """
        try:
            logger.info(f"Previewing transcript for page {page_number}")
            
            # Check if already cached
            cache_key = f"transcript_{page_number}"
            if cache_key in self._page_cache:
                return self._page_cache[cache_key]
            
            # Navigate to transcript tab
            page_url = self.connector.navigate_to_page(page_number, "transcript")
            self.connector.wait_for_content_load()
            
            # Get page source and extract transcript
            page_source = self.connector.get_current_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')
            
            transcript_data = self._extract_transcript_data(soup, page_number)
            
            transcript_preview = {
                'page_number': page_number,
                'page_url': page_url,
                'transcript_available': transcript_data['available'],
                'transcript_content': transcript_data.get('content', {}),
                'line_count': transcript_data.get('line_count', 0),
                'character_count': transcript_data.get('character_count', 0),
                'language_detected': transcript_data.get('language', 'unknown'),
                'content_sample': transcript_data.get('sample', ''),
                'metadata': {
                    'extracted_at': datetime.now().isoformat(),
                    'processing_notes': transcript_data.get('notes', [])
                }
            }
            
            # Cache the result
            self._page_cache[cache_key] = transcript_preview
            
            logger.info(f"Transcript preview completed for page {page_number}")
            return transcript_preview
            
        except Exception as e:
            if isinstance(e, (PageNotFoundError, ExtractionError)):
                raise
            logger.error(f"Transcript preview failed for page {page_number}: {e}")
            raise ExtractionError("transcript preview", f"Page {page_number}: {str(e)}")
    
    def sample_content(self, sample_pages: Optional[List[int]] = None) -> Dict[str, Any]:
        """Sample content from multiple pages for assessment.
        
        Args:
            sample_pages: List of page numbers to sample. If None, uses recommended pages.
            
        Returns:
            Dictionary with sampled content from multiple pages
            
        Raises:
            ExtractionError: If content sampling fails
        """
        try:
            logger.info("Sampling content from multiple pages")
            
            # Determine sample pages
            if sample_pages is None:
                total_pages = self.connector.get_page_count()
                sample_pages = self._get_recommended_sample_pages(total_pages)
            
            # Get metadata preview first
            metadata_preview = self.preview_metadata()
            
            # Sample pages
            sampled_pages = []
            transcript_available = metadata_preview['extraction_estimates']['transcript_available']
            
            for page_num in sample_pages:
                try:
                    page_sample = {
                        'page_number': page_num,
                        'image_preview': self.preview_page_image(page_num)
                    }
                    
                    if transcript_available:
                        page_sample['transcript_preview'] = self.preview_page_transcript(page_num)
                    
                    sampled_pages.append(page_sample)
                    
                except (PageNotFoundError, ExtractionError) as e:
                    logger.warning(f"Could not sample page {page_num}: {e}")
                    sampled_pages.append({
                        'page_number': page_num,
                        'error': str(e)
                    })
            
            content_sample = {
                'sample_timestamp': datetime.now().isoformat(),
                'book_metadata': metadata_preview,
                'sampled_pages': sampled_pages,
                'sample_statistics': {
                    'requested_pages': len(sample_pages),
                    'successful_pages': len([p for p in sampled_pages if 'error' not in p]),
                    'failed_pages': len([p for p in sampled_pages if 'error' in p]),
                    'transcript_coverage': len([p for p in sampled_pages if 'transcript_preview' in p])
                },
                'recommendations': self._generate_extraction_recommendations(sampled_pages, metadata_preview)
            }
            
            logger.info(f"Content sampling completed for {len(sample_pages)} pages")
            return content_sample
            
        except Exception as e:
            logger.error(f"Content sampling failed: {e}")
            raise ExtractionError("content sampling", str(e))
    
    def estimate_extraction_time(self) -> Dict[str, int]:
        """Estimate time required for full extraction.
        
        Returns:
            Dictionary with time estimates in different scenarios
        """
        try:
            page_count = self.connector.get_page_count()
            transcript_available = self.connector.check_transcript_availability()
            
            estimates = {
                'total_pages': page_count,
                'images_only_minutes': self._estimate_extraction_time(page_count, False),
                'with_transcripts_minutes': self._estimate_extraction_time(page_count, transcript_available),
                'recommended_approach': 'with_transcripts' if transcript_available else 'images_only',
                'batch_size_recommendation': min(10, max(1, page_count // 20))  # Adaptive batch size
            }
            
            return estimates
            
        except Exception as e:
            logger.error(f"Extraction time estimation failed: {e}")
            return {
                'total_pages': 0,
                'images_only_minutes': 0,
                'with_transcripts_minutes': 0,
                'recommended_approach': 'unknown',
                'error': str(e)
            }
    
    def _extract_image_info(self, soup: BeautifulSoup, page_number: int) -> Dict[str, str]:
        """Extract image information from page HTML."""
        image_info = {}
        
        # Common image selectors for different portal types
        image_selectors = [
            '.page-image img', '.book-page img', '.manuscript-image img',
            '#page-viewer img', '.viewer img', '.image-viewer img',
            'img[src*="image"]', 'img[src*="jp2"]', 'img[src*="jpeg"]',
            'img[src*="page"]'
        ]
        
        for selector in image_selectors:
            img_element = soup.select_one(selector)
            if img_element and img_element.get('src'):
                image_info['image_url'] = img_element['src']
                
                # Make URL absolute if needed
                if image_info['image_url'].startswith('/'):
                    base_url = self.connector.book_identifier.base_url
                    if base_url:
                        image_info['image_url'] = base_url + image_info['image_url']
                
                # Extract additional attributes
                if img_element.get('width') and img_element.get('height'):
                    image_info['dimensions'] = f"{img_element['width']}x{img_element['height']}"
                
                # Look for thumbnail or download links
                parent = img_element.parent
                if parent:
                    download_link = parent.find('a', href=True)
                    if download_link:
                        image_info['download_url'] = download_link['href']
                
                break
        
        # Detect image format from URL
        if 'image_url' in image_info:
            url = image_info['image_url'].lower()
            if '.jp2' in url:
                image_info['format'] = 'JPEG2000'
            elif '.jpg' in url or '.jpeg' in url:
                image_info['format'] = 'JPEG'
            elif '.png' in url:
                image_info['format'] = 'PNG'
            elif '.tif' in url or '.tiff' in url:
                image_info['format'] = 'TIFF'
        
        return image_info
    
    def _extract_transcript_data(self, soup: BeautifulSoup, page_number: int) -> Dict[str, Any]:
        """Extract transcript data from page HTML."""
        transcript_data = {'available': False}
        
        # Common transcript selectors
        transcript_selectors = [
            '.transcript', '.transcription', '#transcript-content',
            '.text-content', '.page-text', '.manuscript-text',
            '.transcript-viewer', '.text-viewer'
        ]
        
        transcript_element = None
        for selector in transcript_selectors:
            element = soup.select_one(selector)
            if element:
                transcript_element = element
                break
        
        if not transcript_element:
            # Check for "no transcript" indicators
            no_transcript_indicators = [
                'no transcript', 'nicht verfügbar', 'not available',
                'kein transkript', 'transcription not available'
            ]
            
            page_text = soup.get_text().lower()
            if any(indicator in page_text for indicator in no_transcript_indicators):
                transcript_data['notes'] = ['Transcript explicitly marked as unavailable']
            
            return transcript_data
        
        # Extract transcript content
        transcript_data['available'] = True
        raw_content = transcript_element.get_text()
        
        if raw_content.strip():
            # Preserve line structure
            lines = []
            for i, line in enumerate(transcript_element.stripped_strings, 1):
                if line.strip():
                    lines.append({
                        'line_number': i,
                        'text': line.strip(),
                        'raw_html': str(transcript_element)
                    })
            
            transcript_data['content'] = {
                'lines': lines,
                'raw_text': raw_content.strip(),
                'processed_text': '\n'.join(line['text'] for line in lines)
            }
            
            transcript_data['line_count'] = len(lines)
            transcript_data['character_count'] = len(raw_content.strip())
            transcript_data['sample'] = raw_content.strip()[:200] + '...' if len(raw_content) > 200 else raw_content.strip()
            
            # Simple language detection
            transcript_data['language'] = self._detect_text_language(raw_content)
        
        return transcript_data
    
    def _detect_text_language(self, text: str) -> str:
        """Simple language detection for transcript text."""
        text_lower = text.lower()
        
        # Malayalam detection
        malayalam_chars = len([c for c in text if '\u0d00' <= c <= '\u0d7f'])
        if malayalam_chars > len(text) * 0.1:  # More than 10% Malayalam characters
            return 'malayalam'
        
        # German detection
        german_indicators = ['der', 'die', 'das', 'und', 'ist', 'zu', 'von', 'mit', 'für']
        german_score = sum(1 for word in german_indicators if word in text_lower)
        
        # English detection
        english_indicators = ['the', 'and', 'is', 'to', 'of', 'with', 'for', 'in', 'on']
        english_score = sum(1 for word in english_indicators if word in text_lower)
        
        if german_score > english_score and german_score > 2:
            return 'german'
        elif english_score > 2:
            return 'english'
        
        return 'unknown'
    
    def _get_recommended_sample_pages(self, total_pages: int) -> List[int]:
        """Get recommended pages for sampling based on total page count."""
        if total_pages <= 5:
            return list(range(1, total_pages + 1))
        elif total_pages <= 20:
            return [1, total_pages // 2, total_pages]
        else:
            # Sample from beginning, middle, and end
            return [
                1,  # First page
                total_pages // 4,  # Quarter point
                total_pages // 2,  # Middle
                3 * total_pages // 4,  # Three-quarter point
                total_pages  # Last page
            ]
    
    def _estimate_extraction_time(self, page_count: int, include_transcripts: bool) -> int:
        """Estimate extraction time in minutes."""
        # Base time per page (in seconds)
        base_time_per_page = 3  # Page navigation and image extraction
        transcript_time_per_page = 2  # Additional time for transcript processing
        
        total_seconds = page_count * base_time_per_page
        if include_transcripts:
            total_seconds += page_count * transcript_time_per_page
        
        # Add overhead (connection, setup, etc.)
        overhead_seconds = min(300, page_count * 0.5)  # Max 5 minutes overhead
        total_seconds += overhead_seconds
        
        return max(1, int(total_seconds / 60))  # Convert to minutes, minimum 1
    
    def _generate_extraction_recommendations(self, sampled_pages: List[Dict], metadata: Dict) -> List[str]:
        """Generate recommendations based on sampled content."""
        recommendations = []
        
        # Check transcript availability
        pages_with_transcripts = len([p for p in sampled_pages if 'transcript_preview' in p and p['transcript_preview']['transcript_available']])
        total_sampled = len([p for p in sampled_pages if 'error' not in p])
        
        if total_sampled > 0:
            transcript_ratio = pages_with_transcripts / total_sampled
            
            if transcript_ratio > 0.8:
                recommendations.append("High transcript coverage detected - full extraction with transcripts recommended")
            elif transcript_ratio > 0.3:
                recommendations.append("Partial transcript coverage - consider extracting both images and available transcripts")
            else:
                recommendations.append("Low transcript coverage - focus on image extraction")
        
        # Content type recommendations
        content_type = metadata.get('content_type', 'unknown')
        if content_type == 'bible':
            recommendations.append("Biblical content detected - USFM transformation plugin recommended")
        elif content_type == 'dictionary':
            recommendations.append("Dictionary content detected - structured text extraction recommended")
        elif content_type == 'grammar':
            recommendations.append("Grammar content detected - preserve formatting for linguistic analysis")
        
        # Language recommendations
        languages = metadata.get('languages', [])
        if 'malayalam' in languages:
            recommendations.append("Malayalam content detected - ensure Unicode preservation")
        if len(languages) > 1:
            recommendations.append("Multilingual content detected - consider language-specific processing")
        
        return recommendations
    
    def clear_cache(self) -> None:
        """Clear the preview cache."""
        self._page_cache.clear()
        logger.info("Preview cache cleared")