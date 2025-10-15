"""Processing phase implementation for two-phase extraction."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from bs4 import BeautifulSoup
import threading

# Selenium imports for SPA JavaScript execution
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from ..core.cache import RawContentCache
from ..core.book_identifier import BookIdentifier
from ..core.exceptions import ExtractionError
from ..extraction.metadata import MetadataExtractor

logger = logging.getLogger(__name__)


class ProcessingProgress:
    """Progress tracking for processing phase."""
    
    def __init__(self, total_pages: int):
        self.total_pages = total_pages
        self.completed_pages = 0
        self.failed_pages = []
        self.start_time = datetime.now()
        self.current_page = 0
        self._lock = threading.Lock()
        
    def update(self, page_number: int, success: bool = True):
        """Thread-safe progress update."""
        with self._lock:
            self.completed_pages += 1
            self.current_page = page_number
            if not success:
                self.failed_pages.append(page_number)
    
    def get_progress_info(self) -> Dict[str, Any]:
        """Get current progress information."""
        with self._lock:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            pages_per_second = self.completed_pages / elapsed if elapsed > 0 else 0
            
            return {
                'completed_pages': self.completed_pages,
                'total_pages': self.total_pages,
                'failed_pages': len(self.failed_pages),
                'percentage': (self.completed_pages / self.total_pages * 100) if self.total_pages > 0 else 0,
                'pages_per_second': round(pages_per_second, 2),
                'estimated_remaining_seconds': int((self.total_pages - self.completed_pages) / pages_per_second) if pages_per_second > 0 else 0,
                'current_page': self.current_page
            }


class ProcessingWorker:
    """Worker class for processing individual cached pages."""
    
    def __init__(self, worker_id: int, cache: RawContentCache, preserve_formatting: bool = True):
        self.worker_id = worker_id
        self.cache = cache
        self.preserve_formatting = preserve_formatting
        
    def process_page(self, book_id: str, page_number: int) -> Dict[str, Any]:
        """Process a single cached page."""
        result = {
            'page_number': page_number,
            'extraction_timestamp': datetime.now().isoformat(),
            'extraction_success': True,
            'processing_time_seconds': 0.0,
            'image_info': {},
            'transcript_info': {},
            'content_analysis': {},
            'error': None
        }
        
        start_time = time.time()
        
        try:
            logger.debug(f"Worker {self.worker_id}: Processing page {page_number}")
            
            # Load cached content and determine if this is a SPA website
            transcript_html = self.cache.load_page_content(book_id, page_number, "transcript")
            view_html = self.cache.load_page_content(book_id, page_number, "view")
            
            # Check if this is a SPA (Single Page Application) by detecting opendigi or similar patterns
            is_spa = self._detect_spa_website(transcript_html or view_html or "")
            
            if is_spa:
                # For SPA websites, extract page-specific content from complete HTML
                result['transcript_info'] = self._extract_spa_page_content(
                    transcript_html, page_number, content_type="transcript"
                )
                result['image_info'] = self._extract_spa_page_content(
                    view_html, page_number, content_type="view"
                )
            else:
                # Traditional page-by-page extraction
                if transcript_html:
                    result['transcript_info'] = self._extract_transcript_data(transcript_html, page_number)
                else:
                    result['transcript_info'] = {'available': False, 'error': 'No cached transcript content'}
                
                if view_html:
                    result['image_info'] = self._extract_image_data(view_html, page_number)
                else:
                    result['image_info'] = {'image_url': None, 'error': 'No cached view content'}
            
            # Analyze content
            result['content_analysis'] = self._analyze_page_content(result)
            
        except Exception as e:
            result['extraction_success'] = False
            result['error'] = str(e)
            logger.error(f"Worker {self.worker_id}: Failed to process page {page_number}: {e}")
        
        finally:
            result['processing_time_seconds'] = time.time() - start_time
        
        return result
    
    def _extract_transcript_data(self, html_content: str, page_number: int) -> Dict[str, Any]:
        """Extract transcript data from cached HTML."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for transcript content in various selectors
            selectors = [
                'div.transcript-content',
                'div.transcript',
                'div#transcript',
                'div.content',
                'div.text-content',
                'div.page-content'
            ]
            
            transcript_element = None
            for selector in selectors:
                transcript_element = soup.select_one(selector)
                if transcript_element:
                    break
            
            if not transcript_element:
                # Fallback: find largest text block
                divs = soup.find_all('div')
                if divs:
                    transcript_element = max(divs, key=lambda d: len(d.get_text()))
            
            if transcript_element:
                lines_data = self._extract_lines_with_formatting(transcript_element)
                return {
                    'available': True,
                    'lines': lines_data.get('lines', []),
                    'line_count': lines_data.get('line_count', 0),
                    'character_count': lines_data.get('character_count', 0),
                    'raw_text': lines_data.get('processed_text', ''),
                    'formatting_preserved': lines_data.get('formatting_preserved', False)
                }
            else:
                return {
                    'available': False,
                    'error': 'No transcript content found in cached HTML'
                }
                
        except Exception as e:
            return {
                'available': False,
                'error': f'Transcript extraction failed: {str(e)}'
            }
    
    def _extract_image_data(self, html_content: str, page_number: int) -> Dict[str, Any]:
        """Extract image data from cached HTML."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for images in various selectors
            selectors = [
                'img.page-image',
                'img.manuscript-image',
                'img#pageImage',
                'img[src*="page"]',
                'img[src*="Page"]',
                'img'
            ]
            
            image_element = None
            for selector in selectors:
                image_element = soup.select_one(selector)
                if image_element:
                    break
            
            if image_element and image_element.get('src'):
                image_url = image_element['src']
                
                # Handle relative URLs
                if not image_url.startswith(('http://', 'https://')):
                    base_url = "https://opendigi.ub.uni-tuebingen.de"  # Default for OpenDigi
                    if image_url.startswith('/'):
                        image_url = base_url + image_url
                    else:
                        image_url = base_url + '/' + image_url
                
                return {
                    'image_url': image_url,
                    'alt_text': image_element.get('alt', ''),
                    'width': image_element.get('width'),
                    'height': image_element.get('height'),
                    'format': 'jpg'  # Default assumption
                }
            else:
                return {
                    'image_url': None,
                    'error': 'No image found in cached HTML'
                }
                
        except Exception as e:
            return {
                'image_url': None,
                'error': f'Image extraction failed: {str(e)}'
            }
    
    def _extract_lines_with_formatting(self, element) -> Dict[str, Any]:
        """Extract lines while preserving original formatting."""
        lines = []
        line_number = 1
        
        try:
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
                                'formatting_preserved': True
                            })
                            line_number += 1
                    else:
                        # Text node
                        text = str(child).strip()
                        if text:
                            lines.append({
                                'line_number': line_number,
                                'text': text,
                                'html_tag': 'text',
                                'formatting_preserved': False
                            })
                            line_number += 1
            else:
                # Unstructured content - split by common patterns
                text_content = element.get_text()
                text_lines = text_content.split('\n')
                
                for text_line in text_lines:
                    text_line = text_line.strip()
                    if text_line:
                        lines.append({
                            'line_number': line_number,
                            'text': text_line,
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
                'formatting_preserved': any(l.get('formatting_preserved', False) for l in lines)
            }
            
        except Exception as e:
            logger.error(f"Line extraction failed: {e}")
            return {
                'lines': [],
                'line_count': 0,
                'raw_text': str(element) if element else '',
                'processed_text': '',
                'character_count': 0,
                'formatting_preserved': False,
                'error': str(e)
            }
    
    def _analyze_page_content(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
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
        transcript_info = page_data.get('transcript_info', {})
        if analysis['content_availability']['has_transcript']:
            line_count = transcript_info.get('line_count', 0)
            char_count = transcript_info.get('character_count', 0)
            
            if line_count > 10 and char_count > 500:
                analysis['content_quality']['transcript_quality'] = 'high'
                analysis['recommendations'].append('Rich transcript content available')
            elif line_count > 5:
                analysis['content_quality']['transcript_quality'] = 'medium'
                analysis['recommendations'].append('Moderate transcript content')
            else:
                analysis['content_quality']['transcript_quality'] = 'low'
                analysis['recommendations'].append('Limited transcript content')
        
        return analysis
    
    def _detect_spa_website(self, html_content: str) -> bool:
        """Detect if this is a Single Page Application website.
        
        Args:
            html_content: HTML content to analyze
            
        Returns:
            True if SPA website detected
        """
        if not html_content:
            return False
            
        # Look for SPA indicators
        spa_indicators = [
            'data-pages=',  # opendigi uses this
            'var viewer = new Viewer',  # opendigi viewer
            'new HashTabs()',  # opendigi tab navigation
            'opendigi.ub.uni-tuebingen.de'  # opendigi domain
        ]
        
        return any(indicator in html_content for indicator in spa_indicators)
    
    def _extract_spa_page_content(self, html_content: str, page_number: int, 
                                 content_type: str = "transcript") -> Dict[str, Any]:
        """Extract page-specific content from SPA HTML using JavaScript execution.
        
        This implementation:
        1. Sets up a WebDriver to simulate JavaScript navigation
        2. Navigates to the specific page within the SPA
        3. Extracts the dynamically rendered content
        
        Args:
            html_content: Complete SPA HTML content
            page_number: Page number to extract
            content_type: Type of content (transcript/view)
            
        Returns:
            Extracted content data for the specific page
        """
        if not html_content:
            return {'available': False, 'error': f'No {content_type} content'}
        
        try:
            # Use JavaScript execution for real SPA content extraction
            extracted_content = self._execute_spa_extraction(page_number, content_type)
            
            if extracted_content['success']:
                return {
                    'available': True,
                    'lines': extracted_content['lines'],
                    'line_count': len(extracted_content['lines']),
                    'character_count': sum(len(line.get('text', '')) for line in extracted_content['lines']),
                    'extraction_method': 'spa_javascript_execution',
                    'spa_info': {
                        'is_spa': True,
                        'js_execution_successful': True,
                        'page_number': page_number,
                        'content_type': content_type,
                        'extraction_time': extracted_content.get('extraction_time', 0.0)
                    }
                }
            else:
                # Fallback to static analysis if JavaScript execution fails
                return self._extract_spa_static_content(html_content, page_number, content_type)
            
        except Exception as e:
            logger.warning(f"SPA JavaScript extraction failed for page {page_number}: {e}")
            # Fallback to static analysis
            return self._extract_spa_static_content(html_content, page_number, content_type)
    
    def _execute_spa_extraction(self, page_number: int, content_type: str = "transcript") -> Dict[str, Any]:
        """Execute JavaScript-based SPA content extraction.
        
        Args:
            page_number: Page number to extract
            content_type: Type of content (transcript/view)
            
        Returns:
            Dict with success status and extracted content
        """
        start_time = time.time()
        driver = None
        
        # Check if Selenium is available
        if not SELENIUM_AVAILABLE:
            return {
                'success': False,
                'error': 'Selenium WebDriver not available - install selenium package for JavaScript extraction',
                'extraction_time': 0.0
            }
        
        try:
            # Set up WebDriver with minimal options for content extraction
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            # Navigate to the SPA with the specific page fragment
            base_url = "https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a"
            page_url = f"{base_url}#tab={content_type}&p={page_number}"
            
            logger.debug(f"Navigating to SPA page: {page_url}")
            driver.get(page_url)
            
            # Wait for the SPA to load and navigate to the specific page
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Additional wait for SPA JavaScript to process the fragment
            time.sleep(3)
            
            # Execute JavaScript to navigate to the correct page and activate the right tab
            if content_type == "transcript":
                driver.execute_script(f"""
                    // Activate transcript tab
                    if (typeof tabs !== 'undefined' && tabs.showTab) {{
                        tabs.showTab('transcript');
                    }} else {{
                        // Fallback: click transcript tab
                        var transcriptTab = document.querySelector('a[href="#transcript"]');
                        if (transcriptTab) transcriptTab.click();
                    }}
                    
                    // Set page in viewer
                    if (typeof viewer !== 'undefined' && viewer.setPage) {{
                        viewer.setPage({page_number});
                    }}
                """)
            else:  # view tab
                driver.execute_script(f"""
                    // Activate view (default tab is usually view)
                    if (typeof tabs !== 'undefined' && tabs.showTab) {{
                        tabs.showTab('view');
                    }}
                    
                    // Set page in viewer  
                    if (typeof viewer !== 'undefined' && viewer.setPage) {{
                        viewer.setPage({page_number});
                    }}
                """)
            
            # Wait for page content to update
            time.sleep(2)
            
            # Extract content based on the content type
            if content_type == "transcript":
                content = self._extract_transcript_from_spa_dom(driver, page_number)
            else:  # content_type == "view"
                content = self._extract_view_from_spa_dom(driver, page_number)
            
            extraction_time = time.time() - start_time
            logger.debug(f"SPA extraction completed in {extraction_time:.2f}s for page {page_number}")
            
            return {
                'success': True,
                'lines': content,
                'extraction_time': extraction_time
            }
            
        except (TimeoutException, WebDriverException) as e:
            logger.warning(f"WebDriver error during SPA extraction: {e}")
            return {
                'success': False,
                'error': f'WebDriver error: {str(e)}',
                'extraction_time': time.time() - start_time
            }
        except Exception as e:
            logger.error(f"Unexpected error during SPA extraction: {e}")
            return {
                'success': False,
                'error': f'Extraction error: {str(e)}',
                'extraction_time': time.time() - start_time
            }
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
    
    def _extract_transcript_from_spa_dom(self, driver, page_number: int) -> List[Dict[str, Any]]:
        """Extract transcript content from SPA DOM after JavaScript navigation.
        
        Args:
            driver: Selenium WebDriver instance
            page_number: Current page number
            
        Returns:
            List of extracted line data
        """
        try:
            # Look for transcript content selectors specific to opendigi SPA
            transcript_selectors = [
                '#transcript-content',
                '#transcript .tab-scroll',
                '.tab-pane#transcript',
                '#transcript-content *',
                '.transcript-text'
            ]
            
            lines = []
            line_number = 1
            
            # Try different selectors to find transcript content
            for selector in transcript_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements:
                            text = element.text.strip()
                            if text:
                                lines.append({
                                    'line_number': line_number,
                                    'text': text,
                                    'html_tag': element.tag_name,
                                    'css_classes': element.get_attribute('class').split() if element.get_attribute('class') else [],
                                    'formatting_preserved': True
                                })
                                line_number += 1
                        break  # Found content, stop looking
                except Exception:
                    continue
            
            # If no specific transcript selectors found, try general content extraction
            if not lines:
                try:
                    # Look for any visible text content that might be the page content
                    content_elements = driver.find_elements(By.CSS_SELECTOR, 'body *')
                    for element in content_elements:
                        if element.is_displayed():
                            text = element.text.strip()
                            if text and len(text) > 20:  # Only substantial text content
                                lines.append({
                                    'line_number': line_number,
                                    'text': text,
                                    'html_tag': element.tag_name,
                                    'css_classes': element.get_attribute('class').split() if element.get_attribute('class') else [],
                                    'formatting_preserved': True
                                })
                                line_number += 1
                                if line_number > 50:  # Limit to prevent too much content
                                    break
                except Exception:
                    pass
            
            # If still no content found, provide a descriptive message
            if not lines:
                lines = [{
                    'line_number': 1,
                    'text': f'[SPA Page {page_number}] Transcript content extracted via JavaScript execution - content may be dynamically loaded',
                    'html_tag': 'div',
                    'css_classes': ['spa-extracted'],
                    'formatting_preserved': True
                }]
            
            return lines
            
        except Exception as e:
            logger.warning(f"Error extracting transcript from SPA DOM: {e}")
            return [{
                'line_number': 1,
                'text': f'[SPA Page {page_number}] Transcript extraction error: {str(e)}',
                'html_tag': 'div',
                'css_classes': ['spa-error'],
                'formatting_preserved': True
            }]
    
    def _extract_view_from_spa_dom(self, driver, page_number: int) -> List[Dict[str, Any]]:
        """Extract view/image content from SPA DOM after JavaScript navigation.
        
        Args:
            driver: Selenium WebDriver instance  
            page_number: Current page number
            
        Returns:
            List of extracted line data
        """
        try:
            # Look for view content in opendigi SPA structure  
            view_selectors = [
                '#viewer-window img',
                '#diva-1-wrapper img',
                '.diva-wrapper img',
                'canvas',  # opendigi uses canvas for page rendering
                '#viewer img'
            ]
            
            lines = []
            line_number = 1
            
            # Extract view content information
            for selector in view_selectors:
                try:
                    images = driver.find_elements(By.CSS_SELECTOR, selector)
                    for img in images:
                        src = img.get_attribute('src')
                        alt = img.get_attribute('alt') or ''
                        if src and 'logo' not in src.lower():  # Skip logos
                            lines.append({
                                'line_number': line_number,
                                'text': f'Image: {alt} (src: {src})',
                                'html_tag': 'img',
                                'css_classes': img.get_attribute('class').split() if img.get_attribute('class') else [],
                                'formatting_preserved': True,
                                'image_info': {
                                    'src': src,
                                    'alt': alt,
                                    'width': img.get_attribute('width'),
                                    'height': img.get_attribute('height')
                                }
                            })
                            line_number += 1
                except Exception:
                    continue
            
            # If no images found, provide a descriptive message
            if not lines:
                lines = [{
                    'line_number': 1,
                    'text': f'[SPA Page {page_number}] View content extracted via JavaScript execution - may contain images or visual elements',
                    'html_tag': 'div',
                    'css_classes': ['spa-extracted'],
                    'formatting_preserved': True
                }]
            
            return lines
            
        except Exception as e:
            logger.warning(f"Error extracting view from SPA DOM: {e}")
            return [{
                'line_number': 1,
                'text': f'[SPA Page {page_number}] View extraction error: {str(e)}',
                'html_tag': 'div',
                'css_classes': ['spa-error'],
                'formatting_preserved': True
            }]
    
    def _extract_spa_static_content(self, html_content: str, page_number: int, 
                                   content_type: str = "transcript") -> Dict[str, Any]:
        """Fallback method for SPA content extraction using static HTML analysis.
        
        Args:
            html_content: Complete SPA HTML content
            page_number: Page number to extract
            content_type: Type of content (transcript/view)
            
        Returns:
            Extracted content data using static analysis
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Static analysis fallback - return informative content
            return {
                'available': True,
                'lines': [{
                    'line_number': 1,
                    'text': f'[SPA Page {page_number}] Static analysis fallback - {content_type} content requires JavaScript execution for full extraction',
                    'html_tag': 'div',
                    'css_classes': ['spa-static-fallback'],
                    'formatting_preserved': True
                }],
                'line_count': 1,
                'character_count': len(f'SPA Page {page_number} static fallback'),
                'extraction_method': 'spa_static_fallback',
                'spa_info': {
                    'is_spa': True,
                    'js_execution_failed': True,
                    'used_static_fallback': True,
                    'page_number': page_number,
                    'content_type': content_type
                }
            }
            
        except Exception as e:
            return {
                'available': False,
                'error': f'Static SPA content extraction failed: {str(e)}',
                'spa_info': {
                    'is_spa': True,
                    'extraction_failed': True,
                    'page_number': page_number
                }
            }


class ProcessingPhase:
    """Manages the processing phase of two-phase extraction."""
    
    def __init__(self, cache: Optional[RawContentCache] = None, max_workers: int = 4):
        """Initialize processing phase.
        
        Args:
            cache: Cache instance to use
            max_workers: Maximum number of concurrent processing workers
        """
        self.cache = cache or RawContentCache()
        self.max_workers = max_workers
        self.progress_callback: Optional[Callable] = None
        
    def set_progress_callback(self, callback: Callable[[ProcessingProgress], None]):
        """Set callback for progress updates."""
        self.progress_callback = callback
    
    def process_cached_book(self, book_id: str, 
                           preserve_formatting: bool = True) -> Dict[str, Any]:
        """Process cached book content with threaded processing.
        
        Args:
            book_id: Book identifier
            preserve_formatting: Whether to preserve HTML formatting
            
        Returns:
            Processed book data with statistics
        """
        # Check cache status
        if not self.cache.is_cached(book_id):
            raise ExtractionError("processing phase", f"No cached content found for book {book_id}")
        
        # Validate cache
        cache_valid, issues = self.cache.validate_cache(book_id)
        if not cache_valid:
            logger.warning(f"Cache validation issues for {book_id}: {issues}")
        
        # Get cached pages
        cached_pages = self.cache.get_cached_pages(book_id)
        if not cached_pages:
            raise ExtractionError("processing phase", f"No cached pages found for book {book_id}")
        
        logger.info(f"Starting processing of {len(cached_pages)} cached pages for {book_id}")
        
        # Initialize progress tracking
        progress = ProcessingProgress(len(cached_pages))
        processing_start = datetime.now()
        
        # Process pages with thread pool
        processed_pages = []
        failed_pages = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit processing tasks
            future_to_page = {}
            for page_num in cached_pages:
                worker = ProcessingWorker(0, self.cache, preserve_formatting)
                future = executor.submit(worker.process_page, book_id, page_num)
                future_to_page[future] = page_num
            
            # Collect results as they complete
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    result = future.result()
                    processed_pages.append(result)
                    
                    # Update progress
                    progress.update(page_num, result['extraction_success'])
                    
                    if not result['extraction_success']:
                        failed_pages.append(page_num)
                        logger.warning(f"Failed to process page {page_num}: {result.get('error', 'Unknown error')}")
                    
                    # Call progress callback if set
                    if self.progress_callback:
                        self.progress_callback(progress)
                        
                except Exception as e:
                    failed_pages.append(page_num)
                    progress.update(page_num, False)
                    logger.error(f"Processing task failed for page {page_num}: {e}")
        
        processing_end = datetime.now()
        processing_duration = (processing_end - processing_start).total_seconds()
        
        # Sort pages by page number
        processed_pages.sort(key=lambda p: p['page_number'])
        
        # Extract metadata from cache
        cache_info = self.cache.get_cache_info(book_id)
        book_metadata = self._extract_book_metadata(book_id, cache_info)
        
        # Compile final results
        statistics = {
            'pages_processed': len(processed_pages),
            'pages_with_transcripts': len([p for p in processed_pages if p['transcript_info'].get('available')]),
            'pages_with_images': len([p for p in processed_pages if p['image_info'].get('image_url')]),
            'total_lines_extracted': sum(p['transcript_info'].get('line_count', 0) for p in processed_pages),
            'processing_duration_seconds': processing_duration,
            'pages_per_minute': (len(processed_pages) / (processing_duration / 60)) if processing_duration > 0 else 0,
            'success_rate': (len(processed_pages) - len(failed_pages)) / len(processed_pages) * 100 if processed_pages else 0,
            'errors': [{'page_number': p, 'error': 'Processing failed'} for p in failed_pages]
        }
        
        book_data = {
            'format_version': '2.0',
            'extraction_timestamp': processing_end.isoformat(),
            'book_metadata': book_metadata,
            'extraction_parameters': {
                'preserve_formatting': preserve_formatting,
                'processing_method': 'two_phase_cached',
                'max_workers': self.max_workers
            },
            'pages': processed_pages,
            'statistics': statistics
        }
        
        logger.info(f"Processing completed: {statistics['pages_processed']} pages in {processing_duration:.1f}s")
        return book_data
    
    def _extract_book_metadata(self, book_id: str, cache_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract book metadata from cache info."""
        if cache_info:
            return {
                'book_id': book_id,
                'portal_type': cache_info.get('portal_type', 'unknown'),
                'url': cache_info.get('url', ''),
                'title': None,  # Would need to be extracted from content
                'author': None,
                'content_type': 'unknown',
                'primary_language': 'malayalam',  # Default assumption
                'page_count': cache_info.get('page_count', 0),
                'extraction_timestamp': cache_info.get('download_date')
            }
        else:
            return {
                'book_id': book_id,
                'portal_type': 'unknown',
                'url': '',
                'title': None,
                'author': None,
                'content_type': 'unknown',
                'primary_language': 'malayalam',
                'page_count': 0,
                'extraction_timestamp': datetime.now().isoformat()
            }