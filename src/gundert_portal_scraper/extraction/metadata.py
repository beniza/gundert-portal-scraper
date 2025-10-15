"""Metadata extraction from Gundert Portal Info tabs."""

import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from bs4 import BeautifulSoup

from ..core.connection import GundertPortalConnector
from ..core.exceptions import ExtractionError, ConnectionError

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extract bibliographic metadata from Gundert Portal Info tabs."""
    
    # Content type detection patterns
    CONTENT_TYPE_PATTERNS = {
        'bible': [
            r'bible|bibel|testament|psalms|സങ്കീൎത്തനങ്ങൾ',
            r'genesis|exodus|matthew|mark|luke|john',
            r'ഉല്പത്തി|പുറപ്പാട്|മത്തായി|മാൎക്കൊസ്'
        ],
        'dictionary': [
            r'dictionary|wörterbuch|lexicon|glossary',
            r'മലയാളം.*dictionary|dictionary.*malayalam'
        ],
        'grammar': [
            r'grammar|grammatik|syntax|morphology',
            r'വ്യാകരണം|grammar.*malayalam'
        ],
        'literature': [
            r'literature|story|novel|poetry|കഥ|കവിത',
            r'erzählung|geschichte|literatur'
        ],
        'linguistic': [
            r'linguistic|phonetic|comparative|etymology',
            r'sprachlich|vergleichend|etymologie'
        ],
        'religious': [
            r'prayer|hymn|devotion|liturgy|പ്രാൎത്ഥന',
            r'gebet|hymne|andacht|liturgie'
        ]
    }
    
    # Language detection patterns
    LANGUAGE_PATTERNS = {
        'malayalam': [
            r'malayalam|മലയാളം',
            r'[\u0d00-\u0d7f]+'  # Malayalam Unicode range
        ],
        'german': [
            r'german|deutsch|deutsche',
            r'[äöüß]+'  # German special characters
        ],
        'english': [
            r'english|anglicus',
            r'^[a-zA-Z\s.,;:!?\'"()-]+$'  # Pure ASCII text
        ],
        'sanskrit': [
            r'sanskrit|संस्कृत',
            r'[\u0900-\u097f]+'  # Devanagari range
        ],
        'latin': [
            r'latin|latina|latein'
        ]
    }
    
    def __init__(self, connector: GundertPortalConnector):
        """Initialize metadata extractor.
        
        Args:
            connector: Active GundertPortalConnector instance
        """
        self.connector = connector
        self._cached_metadata = None
        
    def extract_full_metadata(self) -> Dict[str, Any]:
        """Extract complete metadata from the book's Info tab.
        
        Returns:
            Comprehensive metadata dictionary
            
        Raises:
            ExtractionError: If metadata extraction fails
        """
        if self._cached_metadata:
            return self._cached_metadata
        
        try:
            # Navigate to info tab
            self.connector.navigate_to_page(1, "info")
            self.connector.wait_for_content_load()
            
            # Get page source
            page_source = self.connector.get_current_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract different metadata components
            basic_info = self._extract_basic_info(soup)
            bibliographic_data = self._extract_bibliographic_data(soup)
            digital_provenance = self._extract_digital_provenance(soup)
            content_analysis = self._analyze_content_characteristics(soup)
            
            # Combine all metadata
            metadata = {
                'extraction_timestamp': datetime.now().isoformat(),
                'book_id': self.connector.book_identifier.book_id,
                'portal_info': self.connector.book_identifier.get_info(),
                **basic_info,
                **bibliographic_data,
                **digital_provenance,
                **content_analysis
            }
            
            # Cache the result
            self._cached_metadata = metadata
            
            logger.info(f"Successfully extracted metadata for book: {self.connector.book_identifier.book_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            raise ExtractionError("metadata extraction", str(e))
    
    def _extract_basic_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract basic book information."""
        basic_info = {}
        
        # Common info selectors
        info_selectors = {
            'title': ['.title', '.book-title', '#title', 'h1', '.main-title'],
            'subtitle': ['.subtitle', '.book-subtitle', '#subtitle', '.secondary-title'],
            'author': ['.author', '.creator', '#author', '.by-author'],
            'editor': ['.editor', '.herausgeber', '#editor'],
            'translator': ['.translator', '.übersetzer', '#translator'],
            'publisher': ['.publisher', '.verlag', '#publisher'],
            'place': ['.place', '.ort', '#place', '.publication-place'],
            'year': ['.year', '.jahr', '#year', '.publication-year', '.date']
        }
        
        for field, selectors in info_selectors.items():
            value = self._extract_text_by_selectors(soup, selectors)
            if value:
                basic_info[field] = self._clean_text(value)
        
        # Extract from metadata tables/lists
        self._extract_from_metadata_tables(soup, basic_info)
        
        return basic_info
    
    def _extract_bibliographic_data(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract bibliographic and catalog information."""
        bib_data = {}
        
        # Bibliographic selectors
        bib_selectors = {
            'shelfmark': ['.shelfmark', '.signatur', '#shelfmark', '.shelf-mark'],
            'catalog_id': ['.catalog-id', '.katalog-id', '#catalog-id'],
            'isbn': ['.isbn', '#isbn'],
            'issn': ['.issn', '#issn'],
            'urn': ['.urn', '#urn'],
            'doi': ['.doi', '#doi'],
            'url': ['.url', '.permalink', '#url'],
            'pages': ['.pages', '.seiten', '#pages', '.page-count'],
            'volumes': ['.volumes', '.bände', '#volumes'],
            'edition': ['.edition', '.auflage', '#edition'],
            'series': ['.series', '.reihe', '#series'],
            'format': ['.format', '#format'],
            'language': ['.language', '.sprache', '#language']
        }
        
        for field, selectors in bib_selectors.items():
            value = self._extract_text_by_selectors(soup, selectors)
            if value:
                bib_data[field] = self._clean_text(value)
        
        # Extract from structured data (JSON-LD, microdata)
        self._extract_structured_data(soup, bib_data)
        
        return bib_data
    
    def _extract_digital_provenance(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract digital provenance and source information."""
        provenance = {}
        
        # Digital provenance selectors
        digital_selectors = {
            'digital_collection': ['.collection', '.sammlung', '#collection'],
            'digitization_date': ['.digitization-date', '.digitalisierung', '#digitization-date'],
            'digital_format': ['.digital-format', '#digital-format'],
            'repository': ['.repository', '.bibliothek', '#repository'],
            'license': ['.license', '.lizenz', '#license'],
            'rights': ['.rights', '.rechte', '#rights'],
            'access_conditions': ['.access', '.zugang', '#access'],
            'quality': ['.quality', '.qualität', '#quality']
        }
        
        for field, selectors in digital_selectors.items():
            value = self._extract_text_by_selectors(soup, selectors)
            if value:
                provenance[field] = self._clean_text(value)
        
        # Extract from links and URLs
        self._extract_link_metadata(soup, provenance)
        
        return provenance
    
    def _analyze_content_characteristics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze content characteristics and detect content type."""
        analysis = {}
        
        # Get all text content for analysis
        full_text = soup.get_text().lower()
        
        # Detect content type
        content_type = self._detect_content_type(full_text)
        analysis['content_type'] = content_type
        
        # Detect primary language
        primary_language = self._detect_primary_language(full_text, soup)
        analysis['primary_language'] = primary_language
        
        # Detect additional languages
        additional_languages = self._detect_additional_languages(full_text, soup)
        if additional_languages:
            analysis['additional_languages'] = additional_languages
        
        # Analyze text characteristics
        text_characteristics = self._analyze_text_characteristics(soup)
        analysis.update(text_characteristics)
        
        return analysis
    
    def _extract_text_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Extract text using a list of CSS selectors."""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) > 0:
                    return text
        return None
    
    def _extract_from_metadata_tables(self, soup: BeautifulSoup, data_dict: Dict[str, str]) -> None:
        """Extract metadata from tables and definition lists."""
        # Look for metadata tables
        tables = soup.find_all('table', class_=re.compile(r'metadata|info|details'))
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    # Map common German/English terms
                    key_mapping = {
                        'titel': 'title', 'title': 'title',
                        'autor': 'author', 'author': 'author',
                        'herausgeber': 'editor', 'editor': 'editor',
                        'verlag': 'publisher', 'publisher': 'publisher',
                        'jahr': 'year', 'year': 'year', 'date': 'year',
                        'ort': 'place', 'place': 'place',
                        'seiten': 'pages', 'pages': 'pages',
                        'sprache': 'language', 'language': 'language'
                    }
                    
                    mapped_key = key_mapping.get(key.rstrip(':'), key.rstrip(':'))
                    if mapped_key and value:
                        data_dict[mapped_key] = self._clean_text(value)
        
        # Look for definition lists
        dls = soup.find_all('dl', class_=re.compile(r'metadata|info|details'))
        for dl in dls:
            terms = dl.find_all('dt')
            definitions = dl.find_all('dd')
            
            for term, definition in zip(terms, definitions):
                key = term.get_text(strip=True).lower().rstrip(':')
                value = definition.get_text(strip=True)
                
                if key and value:
                    data_dict[key] = self._clean_text(value)
    
    def _extract_structured_data(self, soup: BeautifulSoup, data_dict: Dict[str, str]) -> None:
        """Extract structured data (JSON-LD, microdata, etc.)."""
        # JSON-LD extraction
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                import json
                structured_data = json.loads(script.string)
                self._parse_json_ld(structured_data, data_dict)
            except (json.JSONDecodeError, AttributeError):
                continue
        
        # Microdata extraction
        microdata_elements = soup.find_all(attrs={'itemtype': True})
        for element in microdata_elements:
            self._parse_microdata(element, data_dict)
    
    def _extract_link_metadata(self, soup: BeautifulSoup, data_dict: Dict[str, str]) -> None:
        """Extract metadata from links and URLs."""
        # Look for canonical links
        canonical = soup.find('link', rel='canonical')
        if canonical and canonical.get('href'):
            data_dict['canonical_url'] = canonical['href']
        
        # Look for DOI links
        doi_links = soup.find_all('a', href=re.compile(r'doi\.org|dx\.doi\.org'))
        if doi_links:
            data_dict['doi'] = doi_links[0]['href']
        
        # Look for URN links
        urn_links = soup.find_all('a', href=re.compile(r'urn:'))
        if urn_links:
            data_dict['urn'] = urn_links[0]['href']
    
    def _detect_content_type(self, text: str) -> str:
        """Detect the type of content based on text analysis."""
        scores = {}
        
        for content_type, patterns in self.CONTENT_TYPE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
            scores[content_type] = score
        
        if not scores or max(scores.values()) == 0:
            return 'unknown'
        
        return max(scores, key=scores.get)
    
    def _detect_primary_language(self, text: str, soup: BeautifulSoup) -> str:
        """Detect the primary language of the content."""
        # Check HTML lang attribute first
        html_lang = soup.find('html')
        if html_lang and html_lang.get('lang'):
            return html_lang['lang'].split('-')[0].lower()
        
        # Text-based detection
        scores = {}
        for language, patterns in self.LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
            scores[language] = score
        
        if not scores or max(scores.values()) == 0:
            return 'unknown'
        
        return max(scores, key=scores.get)
    
    def _detect_additional_languages(self, text: str, soup: BeautifulSoup) -> List[str]:
        """Detect additional languages present in the content."""
        primary = self._detect_primary_language(text, soup)
        additional = []
        
        for language, patterns in self.LANGUAGE_PATTERNS.items():
            if language == primary:
                continue
            
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    additional.append(language)
                    break
        
        return additional
    
    def _analyze_text_characteristics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze various text characteristics."""
        characteristics = {}
        
        # Count different types of content
        characteristics['has_images'] = len(soup.find_all('img')) > 0
        characteristics['has_tables'] = len(soup.find_all('table')) > 0
        characteristics['has_lists'] = len(soup.find_all(['ul', 'ol', 'dl'])) > 0
        
        # Text structure analysis
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        characteristics['heading_count'] = len(headings)
        
        paragraphs = soup.find_all('p')
        characteristics['paragraph_count'] = len(paragraphs)
        
        # Extract sample text for further analysis
        sample_text = soup.get_text()[:1000]  # First 1000 characters
        characteristics['text_sample'] = self._clean_text(sample_text)
        characteristics['estimated_length'] = len(soup.get_text())
        
        return characteristics
    
    def _parse_json_ld(self, data: Dict, output: Dict[str, str]) -> None:
        """Parse JSON-LD structured data."""
        # Common JSON-LD fields mapping
        json_ld_mapping = {
            'name': 'title',
            'author': 'author',
            'publisher': 'publisher',
            'datePublished': 'year',
            'inLanguage': 'language',
            'description': 'description',
            'url': 'url',
            'identifier': 'catalog_id'
        }
        
        for json_key, output_key in json_ld_mapping.items():
            if json_key in data:
                value = data[json_key]
                if isinstance(value, dict) and 'name' in value:
                    value = value['name']
                elif isinstance(value, list) and value:
                    value = value[0]
                    if isinstance(value, dict) and 'name' in value:
                        value = value['name']
                
                if isinstance(value, str):
                    output[output_key] = self._clean_text(value)
    
    def _parse_microdata(self, element, output: Dict[str, str]) -> None:
        """Parse microdata from HTML elements."""
        # Common microdata properties
        microdata_props = element.find_all(attrs={'itemprop': True})
        
        for prop_element in microdata_props:
            prop_name = prop_element.get('itemprop')
            prop_value = prop_element.get_text(strip=True)
            
            if prop_name and prop_value:
                # Map common microdata properties
                if prop_name in ['name', 'title']:
                    output['title'] = self._clean_text(prop_value)
                elif prop_name == 'author':
                    output['author'] = self._clean_text(prop_value)
                elif prop_name == 'publisher':
                    output['publisher'] = self._clean_text(prop_value)
                elif prop_name in ['datePublished', 'dateCreated']:
                    output['year'] = self._clean_text(prop_value)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common artifacts
        text = re.sub(r'[\r\n\t]+', ' ', text)
        
        return text
    
    def get_basic_info(self) -> Dict[str, str]:
        """Get basic book information only.
        
        Returns:
            Dictionary with essential book details
        """
        full_metadata = self.extract_full_metadata()
        
        basic_fields = [
            'book_id', 'title', 'subtitle', 'author', 'editor', 'translator',
            'publisher', 'place', 'year', 'content_type', 'primary_language'
        ]
        
        return {field: full_metadata.get(field, '') for field in basic_fields}
    
    def detect_content_type(self) -> str:
        """Detect and return the content type.
        
        Returns:
            Content type string
        """
        metadata = self.extract_full_metadata()
        return metadata.get('content_type', 'unknown')
    
    def get_languages(self) -> List[str]:
        """Get list of languages present in the book.
        
        Returns:
            List of detected languages
        """
        metadata = self.extract_full_metadata()
        languages = [metadata.get('primary_language', '')]
        languages.extend(metadata.get('additional_languages', []))
        return [lang for lang in languages if lang and lang != 'unknown']