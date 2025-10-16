"""
Pydantic schemas for book storage and content representation.

These models preserve pagination information and maintain the connection
between extracted text and source manuscript images.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class PageContent(BaseModel):
    """Represents content from a single manuscript page with line-level preservation."""
    
    page_number: int = Field(..., description="Page number in the manuscript")
    page_label: Optional[str] = Field(None, description="Page label (e.g., 'i', 'ii', '1a', '1b')")
    image_url: Optional[str] = Field(None, description="URL to the manuscript page image")
    
    # Content with line-level preservation
    lines: list[str] = Field(default_factory=list, description="Individual lines from the page")
    full_text: str = Field("", description="Combined text from all lines")
    
    # Structural metadata
    has_heading: bool = Field(False, description="Page contains a heading")
    has_verse_numbers: bool = Field(False, description="Page contains verse markers")
    
    # Quality metadata
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Extraction confidence")
    notes: list[str] = Field(default_factory=list, description="Extraction notes or warnings")
    
    @field_validator('full_text', mode='before')
    @classmethod
    def combine_lines(cls, v, info):
        """Auto-generate full_text from lines if not provided."""
        if not v and 'lines' in info.data:
            return '\n'.join(info.data['lines'])
        return v


class BookMetadata(BaseModel):
    """Metadata about the manuscript book."""
    
    book_id: str = Field(..., description="Unique book identifier (e.g., 'GaXXXIV5a')")
    url: str = Field(..., description="Source URL on OpenDigi portal")
    title: Optional[str] = Field(None, description="Book title")
    
    # Content classification
    content_type: str = Field("unknown", description="Type: bible, dictionary, literary, etc.")
    language: str = Field("malayalam", description="Primary language")
    script: str = Field("malayalam", description="Primary script")
    
    # Bibliographic information
    author: Optional[str] = Field(None, description="Author or transcriber")
    year: Optional[str] = Field(None, description="Publication or manuscript year")
    publisher: Optional[str] = Field(None, description="Publisher or archive")
    
    # Technical metadata
    total_pages: int = Field(0, description="Total number of pages")
    extraction_date: datetime = Field(default_factory=datetime.now, description="When extracted")
    extractor_version: str = Field("0.1.0", description="Scraper version used")
    
    # Additional metadata
    notes: str = Field("", description="Additional notes about the manuscript")
    extra_metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class BookStorage(BaseModel):
    """
    Complete book storage with metadata and all page contents.
    
    This is the main data structure that preserves pagination information
    and can be transformed into various output formats.
    """
    
    metadata: BookMetadata = Field(..., description="Book metadata")
    pages: list[PageContent] = Field(default_factory=list, description="All page contents")
    
    # Statistics
    statistics: dict[str, Any] = Field(
        default_factory=lambda: {
            "total_lines_extracted": 0,
            "total_characters": 0,
            "pages_with_content": 0,
            "extraction_errors": 0,
            "success_rate": 100.0
        },
        description="Extraction statistics"
    )
    
    def to_json(self, filepath: Optional[str] = None, indent: int = 2) -> str:
        """Export to JSON format with pagination preserved."""
        json_str = self.model_dump_json(indent=indent, exclude_none=True)
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)
        
        return json_str
    
    @classmethod
    def from_json(cls, filepath: str) -> "BookStorage":
        """Load from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            return cls.model_validate_json(f.read())
    
    def get_full_text(self, join_char: str = "\n\n") -> str:
        """Get complete text from all pages."""
        return join_char.join(page.full_text for page in self.pages if page.full_text)
    
    def update_statistics(self) -> None:
        """Recalculate statistics from pages."""
        total_lines = sum(len(page.lines) for page in self.pages)
        total_chars = sum(len(page.full_text) for page in self.pages)
        pages_with_content = sum(1 for page in self.pages if page.full_text.strip())
        
        self.statistics.update({
            "total_lines_extracted": total_lines,
            "total_characters": total_chars,
            "pages_with_content": pages_with_content,
            "success_rate": (pages_with_content / len(self.pages) * 100) if self.pages else 0.0
        })
