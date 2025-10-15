# API Reference 📚

Complete programmatic interface documentation for the Gundert Portal Scraper.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Classes](#core-classes)
3. [Data Models](#data-models)
4. [Extraction API](#extraction-api)
5. [Transformation API](#transformation-api)
6. [Validation API](#validation-api)
7. [Storage API](#storage-api)
8. [Exception Handling](#exception-handling)
9. [Configuration](#configuration)
10. [Examples](#examples)

## Quick Start

### Basic Usage

```python
from gundert_portal_scraper import (
    BookIdentifier, 
    GundertPortalConnector, 
    ContentScraper,
    create_transformation_engine,
    create_validation_engine
)
from pathlib import Path

# 1. Initialize book identifier
book = BookIdentifier("https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1")

# 2. Extract content
with GundertPortalConnector(book) as connector:
    scraper = ContentScraper(connector)
    book_data = scraper.scrape_full_book(start_page=1, end_page=10)

# 3. Transform to USFM
engine = create_transformation_engine()
result = engine.transform(
    book_storage=book_data,
    target_format='usfm',
    output_file=Path('psalms.usfm')
)

# 4. Validate output
validator = create_validation_engine()
validation_results = validator.validate_file(
    file_path=Path('psalms.usfm'),
    format_type='usfm'
)
```

### Installation

```bash
# Install from PyPI (when available)
pip install gundert-portal-scraper

# Or install from source
git clone https://github.com/beniza/gundert-portal-scraper.git
cd gundert-portal-scraper
uv sync --dev
```

## Core Classes

### BookIdentifier

Parses and manages book identifiers from various digital manuscript portals.

#### Class Definition

```python
class BookIdentifier:
    """Identifies and parses book URLs from supported digital portals."""
    
    def __init__(self, book_url_or_id: str):
        """Initialize with URL or book ID."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `book_id` | `str` | Extracted book identifier |
| `portal_type` | `str` | Portal type ('opendigi', etc.) |
| `base_url` | `str` | Portal base URL |
| `original_url` | `str` | Original input URL |

#### Methods

##### `generate_book_url() -> str`

Generate the main book URL for the portal.

```python
book = BookIdentifier("GaXXXIV5_1")
url = book.generate_book_url()
# Returns: "https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1"
```

##### `generate_page_url(page_number: int, tab: str = "transcript") -> str`

Generate URL for a specific page and tab.

**Parameters:**
- `page_number` (int): Page number (1-based)
- `tab` (str): Tab type ("transcript", "scan", "metadata")

**Returns:** Complete page URL

```python
page_url = book.generate_page_url(page_number=5, tab="transcript")
# Returns: "https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1#page_5_transcript"
```

##### `is_valid_book_id(book_id: str) -> bool` (static)

Validate if a string is a valid book identifier.

```python
is_valid = BookIdentifier.is_valid_book_id("GaXXXIV5_1")  # True
is_valid = BookIdentifier.is_valid_book_id("invalid")      # False
```

#### Exceptions

- `InvalidBookURLError`: Invalid or unsupported URL format
- `UnsupportedPortalError`: Portal not yet supported

---

### GundertPortalConnector

Manages connections to digital manuscript portals with optional Selenium support.

#### Class Definition

```python
class GundertPortalConnector:
    """Manages portal connections and navigation."""
    
    def __init__(self, 
                 book_identifier: BookIdentifier,
                 use_selenium: bool = True,
                 headless: bool = True,
                 timeout: int = 30):
        """Initialize portal connector."""
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `book_identifier` | `BookIdentifier` | Required | Book to connect to |
| `use_selenium` | `bool` | `True` | Use Selenium for dynamic content |
| `headless` | `bool` | `True` | Run browser in headless mode |
| `timeout` | `int` | `30` | Request timeout in seconds |

#### Methods

##### `validate_book_access() -> bool`

Check if the book is accessible on the portal.

```python
with GundertPortalConnector(book) as connector:
    is_accessible = connector.validate_book_access()
    if not is_accessible:
        print("Book not found or not accessible")
```

##### `get_page_count() -> int`

Get the total number of pages in the book.

```python
with GundertPortalConnector(book) as connector:
    total_pages = connector.get_page_count()
    print(f"Book has {total_pages} pages")
```

##### `navigate_to_page(page_number: int, tab: str = "transcript") -> bool`

Navigate to a specific page and tab.

**Parameters:**
- `page_number` (int): Target page number
- `tab` (str): Tab to navigate to

**Returns:** Success status

```python
with GundertPortalConnector(book) as connector:
    success = connector.navigate_to_page(10, "transcript")
    if success:
        # Page loaded successfully
        pass
```

##### `check_transcript_availability(page_number: Optional[int] = None) -> bool`

Check if transcripts are available for the current or specified page.

```python
with GundertPortalConnector(book) as connector:
    has_transcripts = connector.check_transcript_availability()
    page_5_transcripts = connector.check_transcript_availability(5)
```

##### `get_current_page_html() -> str`

Get the HTML content of the currently loaded page.

```python
with GundertPortalConnector(book) as connector:
    connector.navigate_to_page(1, "transcript")
    html = connector.get_current_page_html()
```

##### `close() -> None`

Clean up resources (called automatically with context manager).

#### Context Manager Usage

```python
# Recommended usage with context manager
with GundertPortalConnector(book) as connector:
    # Connector automatically closed when exiting block
    connector.validate_book_access()
    # ... operations
# Resources cleaned up automatically

# Manual resource management (not recommended)
connector = GundertPortalConnector(book)
try:
    connector.validate_book_access()
finally:
    connector.close()  # Must call manually
```

---

### ContentScraper

Extracts manuscript content with line-level preservation and formatting.

#### Class Definition

```python
class ContentScraper:
    """Extracts content from manuscript pages."""
    
    def __init__(self, 
                 connector: GundertPortalConnector,
                 preserve_formatting: bool = True,
                 extract_images: bool = False):
        """Initialize content scraper."""
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `connector` | `GundertPortalConnector` | Required | Portal connector |
| `preserve_formatting` | `bool` | `True` | Maintain line breaks and formatting |
| `extract_images` | `bool` | `False` | Include image references |

#### Methods

##### `scrape_single_page(page_number: int) -> Dict[str, Any]`

Extract content from a single page.

**Parameters:**
- `page_number` (int): Page to extract

**Returns:** Page data dictionary

```python
scraper = ContentScraper(connector)
page_data = scraper.scrape_single_page(5)

# Page data structure:
{
    'page_number': 5,
    'extraction_success': True,
    'transcript_info': {
        'available': True,
        'lines': [
            {'line_number': 1, 'text': 'സങ്കീർത്തനങ്ങൾ'},
            {'line_number': 2, 'text': '൧. ആശീർവാദമുള്ളവൻ...'}
        ]
    },
    'image_info': {
        'image_url': 'https://example.com/page5.jpg',
        'width': 800,
        'height': 1200
    },
    'extraction_time': '2025-01-14T10:30:00',
    'processing_time_seconds': 2.5
}
```

##### `scrape_full_book(start_page: int = 1, end_page: Optional[int] = None, batch_size: int = 5, progress_callback: Optional[Callable] = None) -> BookStorage`

Extract content from multiple pages or entire book.

**Parameters:**
- `start_page` (int): First page to extract (default: 1)
- `end_page` (Optional[int]): Last page to extract (default: all pages)
- `batch_size` (int): Pages to process per batch (default: 5)
- `progress_callback` (Optional[Callable]): Progress update function

**Returns:** Complete book storage object

```python
def progress_callback(current: int, total: int) -> None:
    print(f"Progress: {current}/{total} ({current/total*100:.1f}%)")

book_data = scraper.scrape_full_book(
    start_page=1,
    end_page=50,
    batch_size=10,
    progress_callback=progress_callback
)

# Access extracted data
print(f"Extracted {book_data.statistics['pages_processed']} pages")
print(f"Success rate: {book_data.statistics['success_rate']:.1f}%")
```

##### `scrape_page_range(start_page: int, end_page: int, batch_size: int = 5) -> List[Dict[str, Any]]`

Extract content from a specific range of pages.

```python
pages_1_to_10 = scraper.scrape_page_range(1, 10, batch_size=3)
for page in pages_1_to_10:
    print(f"Page {page['page_number']}: {page['extraction_success']}")
```

## Data Models

### BookStorage

Main data container for extracted book content.

```python
from gundert_portal_scraper.storage import BookStorage

class BookStorage(BaseModel):
    """Complete book data storage."""
    
    book_metadata: BookMetadata
    pages: List[PageContent]
    statistics: ExtractionStatistics
    extraction_config: Optional[Dict[str, Any]] = None
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `book_metadata` | `BookMetadata` | Book information and metadata |
| `pages` | `List[PageContent]` | List of extracted page content |
| `statistics` | `ExtractionStatistics` | Extraction performance metrics |
| `extraction_config` | `Dict` | Configuration used for extraction |

#### Methods

##### `get_total_pages() -> int`

Get the total number of pages in the book.

```python
total = book_storage.get_total_pages()
```

##### `get_successful_pages() -> List[PageContent]`

Get only pages that were successfully extracted.

```python
successful_pages = book_storage.get_successful_pages()
print(f"Successfully extracted {len(successful_pages)} pages")
```

##### `get_page_by_number(page_number: int) -> Optional[PageContent]`

Get a specific page by its number.

```python
page_5 = book_storage.get_page_by_number(5)
if page_5:
    print(f"Page 5 has {len(page_5.transcript_info['lines'])} lines")
```

##### `to_dict() -> Dict[str, Any]`

Convert to dictionary for serialization.

```python
data_dict = book_storage.to_dict()
# Can be serialized to JSON, saved to file, etc.
```

##### `from_dict(data: Dict[str, Any]) -> BookStorage` (classmethod)

Create BookStorage from dictionary.

```python
book_storage = BookStorage.from_dict(loaded_data)
```

---

### BookMetadata

Book information and bibliographic metadata.

```python
class BookMetadata(BaseModel):
    """Book metadata and information."""
    
    book_id: str
    title: Optional[str] = None
    portal_type: str
    content_type: Optional[str] = None
    language: str = "malayalam"
    source_url: Optional[str] = None
    extraction_date: datetime = Field(default_factory=datetime.now)
```

#### Example

```python
from gundert_portal_scraper.storage import BookMetadata

metadata = BookMetadata(
    book_id="PSA_example",
    title="സങ്കീർത്തനങ്ങൾ",
    portal_type="opendigi",
    content_type="biblical",
    language="malayalam",
    source_url="https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1"
)
```

---

### PageContent

Individual page content and metadata.

```python
class PageContent(BaseModel):
    """Single page content and metadata."""
    
    page_number: int
    extraction_success: bool
    transcript_info: Dict[str, Any]
    image_info: Optional[Dict[str, Any]] = None
    extraction_time: datetime = Field(default_factory=datetime.now)
    processing_time_seconds: Optional[float] = None
```

#### Transcript Info Structure

```python
transcript_info = {
    'available': True,
    'lines': [
        {
            'line_number': 1,
            'text': 'സങ്കീർത്തനങ്ങൾ',
            'formatting': {'bold': True, 'centered': True}
        },
        {
            'line_number': 2, 
            'text': '൧. ആശീർവാദമുള്ളവൻ ദുഷ്ടന്മാരുടെ ആലോചനയിൽ നടക്കാതെ',
            'formatting': {'indent': 2}
        }
    ],
    'total_lines': 25,
    'extraction_method': 'selenium'
}
```

#### Image Info Structure

```python
image_info = {
    'image_url': 'https://opendigi.ub.uni-tuebingen.de/image/page5.jpg',
    'width': 800,
    'height': 1200,
    'format': 'JPEG',
    'file_size': 245760  # bytes
}
```

## Extraction API

### MetadataExtractor

Extracts bibliographic and descriptive metadata from portal pages.

#### Class Definition

```python
from gundert_portal_scraper.extraction import MetadataExtractor

class MetadataExtractor:
    """Extracts book metadata from portal pages."""
    
    def __init__(self, connector: GundertPortalConnector):
        """Initialize with portal connector."""
```

#### Methods

##### `extract_book_metadata() -> BookMetadata`

Extract complete book metadata.

```python
extractor = MetadataExtractor(connector)
metadata = extractor.extract_book_metadata()

print(f"Title: {metadata.title}")
print(f"Language: {metadata.language}")
print(f"Content Type: {metadata.content_type}")
```

##### `extract_basic_info() -> Dict[str, str]`

Extract basic book information.

```python
basic_info = extractor.extract_basic_info()
# Returns: {'title': 'Book Title', 'author': 'Author Name', ...}
```

##### `extract_technical_metadata() -> Dict[str, Any]`

Extract technical metadata (page count, format info, etc.).

```python
tech_metadata = extractor.extract_technical_metadata()
# Returns: {'page_count': 150, 'format': 'manuscript', ...}
```

## Transformation API

### TransformationEngine

Converts extracted content to various output formats.

#### Class Definition

```python
from gundert_portal_scraper.transformations import TransformationEngine, create_transformation_engine

# Factory function (recommended)
engine = create_transformation_engine()

# Direct instantiation
engine = TransformationEngine()
```

#### Methods

##### `get_available_formats() -> List[str]`

Get list of supported transformation formats.

```python
formats = engine.get_available_formats()
print(formats)  # ['usfm', 'tei_xml', 'docx', 'parabible_json', 'bibleml_xml']
```

##### `transform(book_storage: BookStorage, target_format: str, output_file: Path, options: Optional[Dict] = None) -> TransformationResult`

Transform content to specified format.

**Parameters:**
- `book_storage` (BookStorage): Extracted content
- `target_format` (str): Target format ('usfm', 'tei_xml', etc.)
- `output_file` (Path): Output file path
- `options` (Optional[Dict]): Format-specific options

**Returns:** TransformationResult object

```python
from pathlib import Path

result = engine.transform(
    book_storage=book_data,
    target_format='usfm',
    output_file=Path('psalms.usfm'),
    options={
        'include_images': True,
        'preserve_line_numbers': True,
        'chapter_detection': 'auto'
    }
)

if result.success:
    print(f"Generated: {result.output_file}")
    print(f"Format: {result.format_name}")
    print(f"Line mappings: {len(result.line_mappings)}")
else:
    print(f"Transformation failed: {result.errors}")
```

##### `get_format_options(format_name: str) -> Dict[str, Any]`

Get available options for a specific format.

```python
usfm_options = engine.get_format_options('usfm')
print(usfm_options)
# Returns: {'include_images': bool, 'preserve_line_numbers': bool, ...}
```

#### Format-Specific Options

##### USFM Options

```python
usfm_options = {
    'include_images': True,          # Include image references
    'preserve_line_numbers': True,   # Keep original line numbers
    'chapter_detection': 'auto',     # 'auto', 'manual', 'none'
    'verse_detection': 'auto',       # 'auto', 'manual', 'none'
    'book_code': 'PSA'              # Override book code
}
```

##### TEI XML Options

```python
tei_options = {
    'include_facsimile': True,       # Include facsimile references
    'scholarly_apparatus': True,     # Include critical apparatus
    'metadata_level': 'full',        # 'basic', 'standard', 'full'
    'encoding_level': 4             # TEI encoding level (1-5)
}
```

##### DOCX Options

```python
docx_options = {
    'include_images': True,          # Embed images
    'page_breaks': True,             # Insert page breaks
    'line_numbering': False,         # Word line numbering
    'styles': {                      # Custom styles
        'heading': 'Heading 1',
        'verse': 'Normal',
        'line_number': 'Line Number'
    }
}
```

### TransformationResult

Result object from transformation operations.

```python
class TransformationResult:
    """Result of a transformation operation."""
    
    success: bool
    output_file: Optional[Path]
    format_name: str
    line_mappings: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `success` | `bool` | Whether transformation succeeded |
| `output_file` | `Path` | Path to generated output file |
| `format_name` | `str` | Target format name |
| `line_mappings` | `List[Dict]` | Source-to-output line mappings |
| `metadata` | `Dict` | Transformation metadata |
| `errors` | `List[str]` | Error messages |
| `warnings` | `List[str]` | Warning messages |

#### Methods

##### `get_line_mapping(output_line: int) -> Optional[Dict[str, Any]]`

Get source mapping for an output line.

```python
mapping = result.get_line_mapping(15)
if mapping:
    print(f"Output line 15 maps to page {mapping['source_page']}, line {mapping['source_line']}")
```

##### `get_statistics() -> Dict[str, Any]`

Get transformation statistics.

```python
stats = result.get_statistics()
print(f"Lines processed: {stats['lines_processed']}")
print(f"Processing time: {stats['processing_time']:.2f}s")
```

## Validation API

### ValidationEngine

Validates generated content for format compliance and quality.

#### Class Definition

```python
from gundert_portal_scraper.validation import ValidationEngine, create_validation_engine

# Factory function (recommended)
engine = create_validation_engine()

# Direct instantiation
engine = ValidationEngine()
```

#### Methods

##### `validate_file(file_path: Path, format_type: str, options: Optional[Dict] = None) -> List[ValidationResult]`

Validate a file against format specifications.

**Parameters:**
- `file_path` (Path): File to validate
- `format_type` (str): Expected format ('usfm', 'tei_xml', etc.)
- `options` (Optional[Dict]): Validation options

**Returns:** List of ValidationResult objects

```python
from pathlib import Path

results = engine.validate_file(
    file_path=Path('psalms.usfm'),
    format_type='usfm',
    options={'strict_mode': True, 'check_encoding': True}
)

for result in results:
    print(f"Validator: {result.metadata.get('validator')}")
    print(f"Valid: {result.is_valid}")
    print(f"Issues: {result.issue_count}")
    
    for issue in result.issues:
        print(f"  {issue.severity.value}: {issue.message}")
```

##### `validate_content(content: str, format_type: str, options: Optional[Dict] = None) -> List[ValidationResult]`

Validate content string directly.

```python
usfm_content = """\\id PSA
\\c 1
\\v 1 സന്തോഷമുള്ളവൻ ദുഷ്ടന്മാരുടെ ആലോചനയിൽ നടക്കാതെ"""

results = engine.validate_content(
    content=usfm_content,
    format_type='usfm'
)
```

##### `get_available_validators(format_type: str) -> List[str]`

Get available validators for a format.

```python
validators = engine.get_available_validators('usfm')
print(validators)  # ['USFMSyntaxValidator', 'USFMStructureValidator', ...]
```

### ValidationResult

Result object from validation operations.

```python
class ValidationResult:
    """Result of a validation operation."""
    
    is_valid: bool
    format_type: str
    issues: List[ValidationIssue]
    metadata: Dict[str, Any]
```

#### Properties

##### `issue_count -> int`

Total number of validation issues.

```python
total_issues = result.issue_count
```

##### `error_count -> int`

Number of error-level issues.

```python
errors = result.error_count
```

##### `warning_count -> int`

Number of warning-level issues.

```python
warnings = result.warning_count
```

### ValidationIssue

Individual validation issue.

```python
class ValidationIssue:
    """Individual validation issue."""
    
    severity: ValidationSeverity
    code: str
    message: str
    line_number: Optional[int]
    column_number: Optional[int]
    context: Optional[Dict[str, Any]]
    suggestion: Optional[str]
```

#### Severity Levels

```python
from gundert_portal_scraper.validation import ValidationSeverity

# Available severity levels
ValidationSeverity.CRITICAL   # Fatal errors, output unusable
ValidationSeverity.ERROR      # Significant problems
ValidationSeverity.WARNING    # Potential issues
ValidationSeverity.INFO       # Informational notes
```

#### Example Usage

```python
for issue in validation_result.issues:
    print(f"[{issue.severity.value.upper()}] {issue.message}")
    
    if issue.line_number:
        print(f"  Line {issue.line_number}")
    
    if issue.suggestion:
        print(f"  Suggestion: {issue.suggestion}")
    
    if issue.context:
        print(f"  Context: {issue.context}")
```

## Storage API

### StorageManager

Manages persistent storage of extracted content and metadata.

#### Class Definition

```python
from gundert_portal_scraper.storage import StorageManager

manager = StorageManager(base_path=Path('storage'))
```

#### Methods

##### `save_book_data(book_storage: BookStorage, format: str = 'json') -> Path`

Save book data to persistent storage.

```python
storage_path = manager.save_book_data(
    book_storage=extracted_data,
    format='json'  # 'json', 'pickle', 'hdf5'
)
print(f"Saved to: {storage_path}")
```

##### `load_book_data(file_path: Path) -> BookStorage`

Load previously saved book data.

```python
loaded_data = manager.load_book_data(storage_path)
print(f"Loaded book: {loaded_data.book_metadata.title}")
```

##### `list_stored_books() -> List[Path]`

Get list of all stored books.

```python
stored_books = manager.list_stored_books()
for book_path in stored_books:
    print(f"Found: {book_path}")
```

## Exception Handling

### Exception Hierarchy

```python
from gundert_portal_scraper.core.exceptions import (
    GundertPortalError,        # Base exception
    BookNotFoundError,         # Book doesn't exist
    ConnectionError,           # Network/portal issues  
    ExtractionError,          # Content extraction problems
    TransformationError,      # Format conversion issues
    ValidationError,          # Content validation failures
    InvalidBookURLError,      # Invalid URL format
    UnsupportedPortalError    # Portal not supported
)
```

### Exception Details

#### GundertPortalError

Base exception for all library errors.

```python
class GundertPortalError(Exception):
    """Base exception for Gundert Portal Scraper."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.details = details or {}
```

#### BookNotFoundError

Raised when a book cannot be found on the portal.

```python
try:
    connector.validate_book_access()
except BookNotFoundError as e:
    print(f"Book not found: {e}")
    print(f"Details: {e.details}")
```

#### ExtractionError

Raised when content extraction fails.

```python
try:
    page_data = scraper.scrape_single_page(5)
except ExtractionError as e:
    print(f"Extraction failed: {e}")
    if e.details.get('page_number'):
        print(f"Failed on page: {e.details['page_number']}")
```

### Error Handling Patterns

#### Graceful Degradation

```python
def extract_with_fallback(scraper, page_number):
    """Extract page with fallback strategies."""
    try:
        return scraper.scrape_single_page(page_number)
    except ExtractionError as e:
        if e.details.get('transcript_unavailable'):
            # Try image-only extraction
            return scraper.scrape_single_page(page_number, images_only=True)
        raise
    except ConnectionError:
        # Retry with different connection settings
        time.sleep(5)
        return scraper.scrape_single_page(page_number)
```

#### Comprehensive Error Reporting

```python
def process_book_with_reporting(book_url):
    """Process book with comprehensive error reporting."""
    errors = []
    warnings = []
    
    try:
        book = BookIdentifier(book_url)
    except InvalidBookURLError as e:
        errors.append(f"Invalid URL: {e}")
        return None, errors, warnings
    
    try:
        with GundertPortalConnector(book) as connector:
            scraper = ContentScraper(connector)
            book_data = scraper.scrape_full_book()
            
    except BookNotFoundError as e:
        errors.append(f"Book not found: {e}")
        return None, errors, warnings
        
    except ConnectionError as e:
        errors.append(f"Connection failed: {e}")
        return None, errors, warnings
        
    except ExtractionError as e:
        warnings.append(f"Partial extraction: {e}")
        # Continue with partial data
    
    return book_data, errors, warnings
```

## Configuration

### Environment Variables

```bash
# Portal connection settings
GUNDERT_PORTAL_TIMEOUT=30
GUNDERT_PORTAL_RETRY_ATTEMPTS=3
GUNDERT_PORTAL_USE_SELENIUM=true

# Selenium settings
SELENIUM_HEADLESS=true
SELENIUM_WINDOW_SIZE="1920,1080"
SELENIUM_IMPLICIT_WAIT=10

# Output settings
GUNDERT_OUTPUT_DIR="/path/to/output"
GUNDERT_TEMP_DIR="/tmp/gundert_scraper"

# Logging
GUNDERT_LOG_LEVEL=INFO
GUNDERT_LOG_FILE="/path/to/logfile.log"
```

### Configuration Object

```python
from gundert_portal_scraper.config import ScrapingConfig

config = ScrapingConfig(
    portal_timeout=30,
    use_selenium=True,
    headless=True,
    batch_size=5,
    output_format='usfm',
    preserve_formatting=True,
    include_images=False
)

# Use with connector
with GundertPortalConnector(book, config=config) as connector:
    # ... operations
```

## Examples

### Complete Extraction Workflow

```python
"""Complete example: Extract, transform, and validate Malayalam psalms."""

from gundert_portal_scraper import (
    BookIdentifier,
    GundertPortalConnector, 
    ContentScraper,
    create_transformation_engine,
    create_validation_engine
)
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_and_process_psalms():
    """Extract and process Malayalam psalms to USFM format."""
    
    # 1. Initialize book identifier
    psalms_url = "https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1"
    book = BookIdentifier(psalms_url)
    logger.info(f"Processing book: {book.book_id}")
    
    # 2. Extract content
    try:
        with GundertPortalConnector(book, use_selenium=True) as connector:
            # Validate access
            if not connector.validate_book_access():
                raise Exception("Book not accessible")
            
            # Get page count
            total_pages = connector.get_page_count()
            logger.info(f"Book has {total_pages} pages")
            
            # Extract content with progress tracking
            scraper = ContentScraper(connector, preserve_formatting=True)
            
            def progress_callback(current, total):
                logger.info(f"Extracted {current}/{total} pages ({current/total*100:.1f}%)")
            
            book_data = scraper.scrape_full_book(
                start_page=1,
                end_page=min(50, total_pages),  # Limit for example
                batch_size=5,
                progress_callback=progress_callback
            )
            
            logger.info(f"Extraction complete. Success rate: {book_data.statistics['success_rate']:.1f}%")
    
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return None
    
    # 3. Transform to USFM
    try:
        engine = create_transformation_engine()
        output_file = Path('malayalam_psalms.usfm')
        
        result = engine.transform(
            book_storage=book_data,
            target_format='usfm',
            output_file=output_file,
            options={
                'include_images': False,
                'preserve_line_numbers': True,
                'book_code': 'PSA'
            }
        )
        
        if result.success:
            logger.info(f"USFM file generated: {result.output_file}")
            logger.info(f"Line mappings: {len(result.line_mappings)}")
        else:
            logger.error(f"Transformation failed: {result.errors}")
            return None
            
    except Exception as e:
        logger.error(f"Transformation error: {e}")
        return None
    
    # 4. Validate output
    try:
        validator = create_validation_engine()
        validation_results = validator.validate_file(
            file_path=output_file,
            format_type='usfm',
            options={'strict_mode': True}
        )
        
        for result in validation_results:
            logger.info(f"Validation by {result.metadata.get('validator')}: {'PASS' if result.is_valid else 'FAIL'}")
            
            if result.issues:
                for issue in result.issues:
                    level = issue.severity.value.upper()
                    logger.warning(f"  [{level}] {issue.message}")
                    
    except Exception as e:
        logger.error(f"Validation error: {e}")
    
    return output_file

if __name__ == "__main__":
    result_file = extract_and_process_psalms()
    if result_file:
        print(f"Successfully processed psalms: {result_file}")
    else:
        print("Processing failed")
```

### Batch Processing Multiple Books

```python
"""Batch processing example: Process multiple books with error handling."""

from gundert_portal_scraper import BookIdentifier, GundertPortalConnector, ContentScraper
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor
import logging

def process_single_book(book_url: str, output_dir: Path) -> Dict[str, Any]:
    """Process a single book and return results."""
    result = {
        'url': book_url,
        'success': False,
        'output_file': None,
        'errors': [],
        'statistics': {}
    }
    
    try:
        # Initialize and extract
        book = BookIdentifier(book_url)
        output_file = output_dir / f"{book.book_id}.json"
        
        with GundertPortalConnector(book) as connector:
            scraper = ContentScraper(connector)
            book_data = scraper.scrape_full_book(
                start_page=1,
                end_page=20  # Limit for batch processing
            )
        
        # Save extracted data
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(book_data.to_dict(), f, ensure_ascii=False, indent=2)
        
        result.update({
            'success': True,
            'output_file': str(output_file),
            'statistics': book_data.statistics
        })
        
    except Exception as e:
        result['errors'].append(str(e))
    
    return result

def batch_process_books(book_urls: List[str], output_dir: Path, max_workers: int = 3):
    """Process multiple books concurrently."""
    output_dir.mkdir(exist_ok=True)
    
    # Process books concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_book, url, output_dir): url
            for url in book_urls
        }
        
        results = []
        for future in futures:
            try:
                result = future.result(timeout=300)  # 5 minute timeout
                results.append(result)
                
                if result['success']:
                    logging.info(f"✓ Processed: {result['url']}")
                else:
                    logging.error(f"✗ Failed: {result['url']} - {result['errors']}")
                    
            except Exception as e:
                url = futures[future]
                logging.error(f"✗ Exception for {url}: {e}")
                results.append({
                    'url': url,
                    'success': False,
                    'errors': [str(e)]
                })
    
    # Generate report
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    report = {
        'summary': {
            'total_books': total,
            'successful': successful,
            'failed': total - successful,
            'success_rate': successful / total * 100 if total > 0 else 0
        },
        'results': results
    }
    
    # Save report
    report_file = output_dir / 'batch_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    logging.info(f"Batch processing complete: {successful}/{total} books processed successfully")
    return report

# Usage
if __name__ == "__main__":
    book_urls = [
        "https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1",
        "https://opendigi.ub.uni-tuebingen.de/opendigi/GaXV2",
        # Add more URLs
    ]
    
    output_directory = Path('batch_output')
    report = batch_process_books(book_urls, output_directory)
    print(f"Processing complete. Report saved to {output_directory}/batch_report.json")
```

### Custom Format Development

```python
"""Example: Develop a custom output format for special requirements."""

from gundert_portal_scraper.transformations import BaseTransformer, TransformationResult
from pathlib import Path
from typing import Dict, Any, Optional
import json
from datetime import datetime

class ScholarlyEditionTransformer(BaseTransformer):
    """Transform to scholarly edition format with critical apparatus."""
    
    def __init__(self):
        super().__init__()
        self.format_name = "scholarly_edition"
        self.file_extension = "json"
        self.description = "Scholarly edition with critical apparatus and annotations"
    
    def transform(self, book_storage, output_file: Path, options: Optional[Dict[str, Any]] = None) -> TransformationResult:
        """Transform to scholarly edition format."""
        try:
            options = options or {}
            
            # Build scholarly edition structure
            edition = {
                'metadata': {
                    'title': book_storage.book_metadata.title,
                    'source': book_storage.book_metadata.source_url,
                    'editor': options.get('editor_name', 'Digital Edition'),
                    'edition_date': datetime.now().isoformat(),
                    'encoding_standards': ['TEI P5', 'Dublin Core'],
                    'language': book_storage.book_metadata.language
                },
                'text_structure': {
                    'divisions': [],
                    'apparatus': [],
                    'annotations': []
                },
                'facsimile': {
                    'pages': []
                }
            }
            
            line_mappings = []
            current_division = None
            
            # Process pages and build structure
            for page in book_storage.get_successful_pages():
                page_data = {
                    'page_number': page.page_number,
                    'image_reference': page.image_info.get('image_url') if page.image_info else None,
                    'lines': []
                }
                
                if page.transcript_info.get('available'):
                    for line_data in page.transcript_info.get('lines', []):
                        text = line_data.get('text', '')
                        
                        # Detect structural elements
                        line_type = self._classify_line(text, options)
                        
                        if line_type == 'division_start':
                            current_division = {
                                'type': 'chapter',
                                'number': self._extract_number(text),
                                'title': text,
                                'content': []
                            }
                            edition['text_structure']['divisions'].append(current_division)
                        
                        # Create line entry
                        line_entry = {
                            'id': f"p{page.page_number}l{line_data.get('line_number')}",
                            'text': text,
                            'type': line_type,
                            'page_reference': page.page_number,
                            'source_line': line_data.get('line_number'),
                            'annotations': self._generate_annotations(text, options)
                        }
                        
                        # Add to current division or standalone
                        if current_division:
                            current_division['content'].append(line_entry)
                        else:
                            edition['text_structure']['divisions'].append({
                                'type': 'fragment',
                                'content': [line_entry]
                            })
                        
                        page_data['lines'].append(line_entry)
                        
                        # Track line mapping
                        line_mappings.append({
                            'output_id': line_entry['id'],
                            'source_page': page.page_number,
                            'source_line': line_data.get('line_number'),
                            'text_preview': text[:50] + '...' if len(text) > 50 else text
                        })
                
                edition['facsimile']['pages'].append(page_data)
            
            # Generate critical apparatus
            edition['text_structure']['apparatus'] = self._generate_critical_apparatus(
                edition['text_structure']['divisions'], options
            )
            
            # Add encoding metadata
            edition['encoding'] = {
                'method': 'automated_extraction',
                'source_format': 'digital_manuscript',
                'transformation_date': datetime.now().isoformat(),
                'line_count': len(line_mappings),
                'page_count': len(edition['facsimile']['pages'])
            }
            
            # Write output
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(edition, f, ensure_ascii=False, indent=2)
            
            return TransformationResult(
                success=True,
                output_file=output_file,
                format_name=self.format_name,
                line_mappings=line_mappings,
                metadata={
                    'divisions_count': len(edition['text_structure']['divisions']),
                    'annotations_count': sum(len(line.get('annotations', [])) 
                                           for div in edition['text_structure']['divisions'] 
                                           for line in div.get('content', [])),
                    'encoding_level': 'scholarly'
                }
            )
            
        except Exception as e:
            return TransformationResult(
                success=False,
                format_name=self.format_name,
                errors=[str(e)]
            )
    
    def _classify_line(self, text: str, options: Dict) -> str:
        """Classify line type for structural analysis."""
        text = text.strip()
        
        if not text:
            return 'empty'
        
        # Malayalam chapter/section markers
        if any(marker in text for marker in ['അദ്ധ്യായം', 'ഭാഗം', 'സങ്കീർത്തനം']):
            return 'division_start'
        
        # Verse numbers
        if text.startswith(('൧', '൨', '൩', '൪', '൫', '൬', '൭', '൮', '൯', '൦')):
            return 'verse'
        
        # Titles and headers  
        if len(text) < 50 and not text.endswith('.'):
            return 'title'
        
        return 'text'
    
    def _extract_number(self, text: str) -> Optional[int]:
        """Extract chapter/verse numbers from Malayalam text."""
        malayalam_digits = {
            '൦': 0, '൧': 1, '൨': 2, '൩': 3, '൪': 4,
            '൫': 5, '൬': 6, '൭': 7, '൮': 8, '൯': 9
        }
        
        number_str = ''
        for char in text:
            if char in malayalam_digits:
                number_str += str(malayalam_digits[char])
        
        return int(number_str) if number_str else None
    
    def _generate_annotations(self, text: str, options: Dict) -> List[Dict]:
        """Generate annotations for scholarly apparatus."""
        annotations = []
        
        # Linguistic annotations
        if options.get('linguistic_analysis', False):
            if any(word in text for word in ['ആശീർവാദം', 'ദുഷ്ടൻ', 'നീതിമാൻ']):
                annotations.append({
                    'type': 'linguistic',
                    'category': 'theological_term',
                    'note': 'Key theological terminology'
                })
        
        # Textual variants (simulated)
        if options.get('textual_criticism', False):
            if len(text) > 100:  # Long lines might have variants
                annotations.append({
                    'type': 'textual',
                    'category': 'variant_reading',
                    'note': 'Compare with manuscript tradition'
                })
        
        return annotations
    
    def _generate_critical_apparatus(self, divisions: List[Dict], options: Dict) -> List[Dict]:
        """Generate critical apparatus entries."""
        apparatus = []
        
        for i, division in enumerate(divisions):
            if division.get('type') == 'chapter':
                apparatus.append({
                    'reference': f"Chapter {division.get('number', i+1)}",
                    'type': 'structural',
                    'note': f"Chapter division based on manuscript layout"
                })
        
        return apparatus

# Usage example
if __name__ == "__main__":
    from gundert_portal_scraper.transformations import TransformationEngine
    
    # Register custom transformer
    engine = TransformationEngine()
    scholarly_transformer = ScholarlyEditionTransformer()
    engine.register_transformer(scholarly_transformer)
    
    # Use in transformation
    result = engine.transform(
        book_storage=extracted_data,
        target_format='scholarly_edition',
        output_file=Path('scholarly_edition.json'),
        options={
            'editor_name': 'Dr. Scholar',
            'linguistic_analysis': True,
            'textual_criticism': True
        }
    )
    
    if result.success:
        print(f"Scholarly edition created: {result.output_file}")
        print(f"Annotations: {result.metadata['annotations_count']}")
```

---

**Next**: See [examples/](../examples/) for more practical use cases and [INSTALLATION.md](INSTALLATION.md) for setup instructions.