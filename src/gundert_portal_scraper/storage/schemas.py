"""Storage schemas for Gundert Portal extracted content."""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import json


class ContentFormat(Enum):
    """Supported storage formats."""
    JSON = "json"
    TEI_XML = "tei_xml"
    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"


class StorageVersion(Enum):
    """Storage schema versions."""
    V1_0 = "1.0"
    V2_0 = "2.0"  # Current version with enhanced metadata


@dataclass
class PageContent:
    """Schema for individual page content."""
    page_number: int
    extraction_timestamp: str
    extraction_success: bool
    processing_time_seconds: float
    
    # Image information
    image_info: Dict[str, Any]
    
    # Transcript information
    transcript_info: Dict[str, Any]
    
    # Content analysis
    content_analysis: Dict[str, Any]
    
    # Optional error information
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PageContent':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ExtractionParameters:
    """Parameters used during extraction."""
    start_page: int
    end_page: int
    batch_size: int
    preserve_formatting: bool
    transcript_extraction: bool
    portal_type: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractionStatistics:
    """Statistics from the extraction process."""
    pages_processed: int
    pages_with_transcripts: int
    pages_with_images: int
    total_lines_extracted: int
    extraction_start_time: Optional[str]
    extraction_end_time: Optional[str]
    extraction_duration_seconds: float
    pages_per_minute: float
    success_rate: float
    errors: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BookMetadata:
    """Complete book metadata schema."""
    book_id: str
    portal_type: str
    base_url: Optional[str]
    
    # Basic bibliographic information
    title: Optional[str] = None
    author: Optional[str] = None
    editor: Optional[str] = None  
    publisher: Optional[str] = None
    publication_year: Optional[str] = None
    publication_place: Optional[str] = None
    
    # Physical description
    pages: Optional[int] = None
    dimensions: Optional[str] = None
    condition: Optional[str] = None
    
    # Content classification
    content_type: Optional[str] = None  # bible, dictionary, grammar, literature
    primary_language: Optional[str] = None
    secondary_languages: Optional[List[str]] = None
    subject_keywords: Optional[List[str]] = None
    
    # Digital information
    digitization_date: Optional[str] = None
    source_library: Optional[str] = None
    manuscript_collection: Optional[str] = None
    shelf_mark: Optional[str] = None
    
    # Technical metadata
    transcript_available: bool = False
    image_format: Optional[str] = None
    page_count: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookMetadata':
        return cls(**data)


@dataclass
class BookStorage:
    """Complete book storage schema."""
    format_version: str
    extraction_timestamp: str
    book_metadata: BookMetadata
    extraction_parameters: ExtractionParameters
    pages: List[PageContent]
    statistics: ExtractionStatistics
    
    # Storage metadata
    storage_path: Optional[str] = None
    last_updated: Optional[str] = None
    checksum: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            'format_version': self.format_version,
            'extraction_timestamp': self.extraction_timestamp,
            'book_metadata': self.book_metadata.to_dict(),
            'extraction_parameters': self.extraction_parameters.to_dict(),
            'pages': [page.to_dict() for page in self.pages],
            'statistics': self.statistics.to_dict(),
            'storage_metadata': {
                'storage_path': self.storage_path,
                'last_updated': self.last_updated,
                'checksum': self.checksum
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookStorage':
        """Create from dictionary."""
        storage_meta = data.get('storage_metadata', {})
        
        return cls(
            format_version=data['format_version'],
            extraction_timestamp=data['extraction_timestamp'],
            book_metadata=BookMetadata.from_dict(data['book_metadata']),
            extraction_parameters=ExtractionParameters(**data['extraction_parameters']),
            pages=[PageContent.from_dict(page) for page in data['pages']],
            statistics=ExtractionStatistics(**data['statistics']),
            storage_path=storage_meta.get('storage_path'),
            last_updated=storage_meta.get('last_updated'),
            checksum=storage_meta.get('checksum')
        )
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BookStorage':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class TEISchema:
    """TEI XML schema definitions for scholarly digital editions."""
    
    @staticmethod
    def generate_tei_header(book_metadata: BookMetadata, extraction_timestamp: str) -> str:
        """Generate TEI header with complete metadata."""
        
        # Extract year from extraction timestamp
        extraction_date = datetime.fromisoformat(extraction_timestamp.replace('Z', '+00:00')).strftime('%Y-%m-%d')
        
        header = f'''<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>{book_metadata.title or 'Untitled Work'}</title>
        {f'<author>{book_metadata.author}</author>' if book_metadata.author else ''}
        {f'<editor>{book_metadata.editor}</editor>' if book_metadata.editor else ''}
        <respStmt>
          <resp>Digital extraction and encoding</resp>
          <name>Gundert Portal Scraper</name>
        </respStmt>
      </titleStmt>
      
      <publicationStmt>
        <publisher>Digital Humanities Project</publisher>
        <date when="{extraction_date}">{extraction_date}</date>
        <availability>
          <p>This digital edition is made available for research purposes.</p>
        </availability>
      </publicationStmt>
      
      <sourceDesc>
        <msDesc>
          <msIdentifier>
            <repository>{book_metadata.source_library or 'Unknown Library'}</repository>
            <collection>{book_metadata.manuscript_collection or 'Gundert Collection'}</collection>
            <idno>{book_metadata.book_id}</idno>
            {f'<altIdentifier><idno>{book_metadata.shelf_mark}</idno></altIdentifier>' if book_metadata.shelf_mark else ''}
          </msIdentifier>
          
          <msContents>
            <summary>
              <p>Content type: {book_metadata.content_type or 'Unknown'}</p>
              <p>Primary language: {book_metadata.primary_language or 'Unknown'}</p>
              {f'<p>Secondary languages: {", ".join(book_metadata.secondary_languages)}</p>' if book_metadata.secondary_languages else ''}
            </summary>
          </msContents>
          
          <physDesc>
            <objectDesc>
              <extent>{book_metadata.pages or 'Unknown'} pages</extent>
              {f'<dimensions>{book_metadata.dimensions}</dimensions>' if book_metadata.dimensions else ''}
            </objectDesc>
            {f'<condition>{book_metadata.condition}</condition>' if book_metadata.condition else ''}
          </physDesc>
          
          <history>
            {f'<origin><origDate>{book_metadata.publication_year}</origDate><origPlace>{book_metadata.publication_place}</origPlace></origin>' if book_metadata.publication_year or book_metadata.publication_place else ''}
          </history>
        </msDesc>
      </sourceDesc>
    </fileDesc>
    
    <encodingDesc>
      <projectDesc>
        <p>Digital edition created from manuscript digitization available at Gundert Portal.</p>
      </projectDesc>
      <editorialDecl>
        <p>Line breaks and formatting preserved from original transcription.</p>
        <p>Malayalam text encoded in Unicode.</p>
      </editorialDecl>
    </encodingDesc>
    
    <profileDesc>
      <langUsage>
        <language ident="{book_metadata.primary_language or 'ml'}">Primary language</language>
        {chr(10).join(f'        <language ident="{lang}">{lang}</language>' for lang in (book_metadata.secondary_languages or []))}
      </langUsage>
      {f'<textClass><keywords>{chr(10).join(f"          <term>{kw}</term>" for kw in book_metadata.subject_keywords)}{chr(10)}        </keywords></textClass>' if book_metadata.subject_keywords else ''}
    </profileDesc>
    
    <revisionDesc>
      <change when="{extraction_date}">Initial digital extraction and encoding</change>
    </revisionDesc>
  </teiHeader>'''
        
        return header
    
    @staticmethod
    def generate_page_xml(page: PageContent, include_facsimile: bool = True) -> str:
        """Generate TEI XML for a single page."""
        page_xml = f'    <pb n="{page.page_number}"/>\n'
        
        if include_facsimile and page.image_info.get('image_url'):
            page_xml += f'    <graphic url="{page.image_info["image_url"]}"/>\n'
        
        if page.transcript_info.get('available') and page.transcript_info.get('lines'):
            page_xml += '    <div type="page">\n'
            
            for line in page.transcript_info['lines']:
                line_text = line.get('text', '').strip()
                if line_text:
                    # Escape XML special characters
                    line_text = line_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    page_xml += f'      <l n="{line.get("line_number", "")}">{line_text}</l>\n'
                elif line.get('is_line_break'):
                    page_xml += '      <lb/>\n'
            
            page_xml += '    </div>\n'
        
        return page_xml


def create_storage_schema_documentation() -> str:
    """Generate documentation for storage schemas."""
    
    doc = '''# Gundert Portal Storage Schemas

## Overview

The Gundert Portal Scraper uses structured schemas to store extracted content in multiple formats:

### Supported Formats

1. **JSON** - Primary storage format with complete metadata
2. **TEI XML** - Scholarly digital edition format  
3. **Plain Text** - Simple text extraction
4. **Markdown** - Formatted text with metadata

## JSON Schema Structure

### BookStorage (Root)
- `format_version`: Schema version (currently "2.0")
- `extraction_timestamp`: ISO timestamp of extraction
- `book_metadata`: Complete bibliographic metadata
- `extraction_parameters`: Parameters used during extraction
- `pages`: Array of page content objects
- `statistics`: Extraction statistics and performance metrics
- `storage_metadata`: File system and integrity information

### BookMetadata
- **Identification**: book_id, portal_type, base_url
- **Bibliographic**: title, author, editor, publisher, publication_year, publication_place
- **Physical**: pages, dimensions, condition
- **Content**: content_type, primary_language, secondary_languages, subject_keywords
- **Digital**: digitization_date, source_library, manuscript_collection, shelf_mark
- **Technical**: transcript_available, image_format, page_count

### PageContent
- **Core**: page_number, extraction_timestamp, extraction_success, processing_time_seconds
- **Content**: image_info, transcript_info, content_analysis
- **Error Handling**: Optional error field for failed extractions

## TEI XML Schema

The TEI XML format follows TEI P5 guidelines for digital manuscripts:

### TEI Header
- Complete bibliographic description in `<fileDesc>`
- Manuscript description in `<msDesc>`
- Encoding practices in `<encodingDesc>`
- Language and classification in `<profileDesc>`

### Text Body
- Page breaks marked with `<pb>`
- Images referenced with `<graphic>`
- Text organized in `<div type="page">`
- Line-level markup with `<l>` elements
- Line breaks with `<lb/>`

## Storage Organization

Books are stored in a hierarchical folder structure:
```
extracted_books/
├── {book_id}/
│   ├── metadata.json
│   ├── content.json
│   ├── content.xml (TEI)
│   ├── content.txt
│   ├── content.md
│   ├── images/
│   │   ├── page_001.jpg
│   │   └── ...
│   └── logs/
│       └── extraction.log
```

## Usage Examples

### Loading from JSON
```python
from gundert_portal_scraper.storage.schemas import BookStorage

with open('book.json', 'r', encoding='utf-8') as f:
    book = BookStorage.from_json(f.read())
```

### Converting to TEI
```python
from gundert_portal_scraper.storage.formats import TEIConverter

converter = TEIConverter()
tei_xml = converter.convert_to_tei(book_storage)
```

## Schema Versioning

- **Version 1.0**: Initial schema with basic content extraction
- **Version 2.0**: Enhanced metadata, content analysis, and TEI support

The system maintains backward compatibility with version 1.0 files.
'''
    
    return doc