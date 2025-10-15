#!/usr/bin/env python3
"""
Basic Usage Examples for Gundert Portal Scraper

This file demonstrates fundamental usage patterns for extracting content
from Malayalam manuscript portals and converting to various formats.

Level: Beginner
Use Case: Getting started with the scraper, basic extraction workflows
"""

import logging
from pathlib import Path
from gundert_portal_scraper import (
    BookIdentifier,
    GundertPortalConnector,
    ContentScraper,
    create_transformation_engine,
    create_validation_engine
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_basic_extraction():
    """Extract a small sample from a Malayalam manuscript."""
    print("\n=== Example 1: Basic Extraction ===")
    
    # Test URL - Gundert's Bible commentary
    test_url = "https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1"
    
    try:
        # 1. Initialize book identifier
        book = BookIdentifier(test_url)
        logger.info(f"Identified book: {book.book_id}")
        
        # 2. Connect to portal and extract content
        with GundertPortalConnector(book, use_selenium=True, headless=True) as connector:
            # Validate book is accessible
            if not connector.validate_book_access():
                logger.error("Book is not accessible")
                return None
            
            # Get basic info
            page_count = connector.get_page_count()
            logger.info(f"Book has {page_count} pages")
            
            # Extract small sample (first 3 pages)
            scraper = ContentScraper(connector, preserve_formatting=True)
            
            def progress_callback(current, total):
                logger.info(f"Progress: {current}/{total} pages")
            
            book_data = scraper.scrape_full_book(
                start_page=1,
                end_page=3,
                batch_size=2,
                progress_callback=progress_callback
            )
            
            # Display results
            stats = book_data.statistics
            logger.info(f"Extraction complete:")
            logger.info(f"  - Pages processed: {stats['pages_processed']}")
            logger.info(f"  - Success rate: {stats['success_rate']:.1f}%")
            logger.info(f"  - Total lines: {stats['total_lines_extracted']}")
            
            return book_data
            
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return None


def example_2_format_conversion(book_data):
    """Convert extracted content to different formats."""
    if not book_data:
        logger.warning("No data to convert - skipping format conversion")
        return
    
    print("\n=== Example 2: Format Conversion ===")
    
    # Create output directory
    output_dir = Path("examples/output_samples")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize transformation engine
    engine = create_transformation_engine()
    available_formats = engine.get_available_formats()
    logger.info(f"Available formats: {available_formats}")
    
    # Convert to multiple formats
    formats_to_try = ['usfm', 'tei_xml', 'parabible_json']
    
    for format_name in formats_to_try:
        if format_name in available_formats:
            try:
                output_file = output_dir / f"sample.{format_name.replace('_', '.')}"
                
                result = engine.transform(
                    book_storage=book_data,
                    target_format=format_name,
                    output_file=output_file,
                    options={
                        'include_images': False,
                        'preserve_line_numbers': True
                    }
                )
                
                if result.success:
                    logger.info(f"✓ Generated {format_name}: {result.output_file}")
                    logger.info(f"  Lines mapped: {len(result.line_mappings)}")
                    
                    # Show file size
                    size_kb = result.output_file.stat().st_size / 1024
                    logger.info(f"  File size: {size_kb:.1f} KB")
                    
                else:
                    logger.error(f"✗ Failed to generate {format_name}: {result.errors}")
                    
            except Exception as e:
                logger.error(f"✗ Error converting to {format_name}: {e}")


def example_3_single_page_extraction():
    """Extract content from a single page for quick testing."""
    print("\n=== Example 3: Single Page Extraction ===")
    
    test_url = "https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1"
    
    try:
        book = BookIdentifier(test_url)
        
        with GundertPortalConnector(book, headless=True) as connector:
            scraper = ContentScraper(connector)
            
            # Extract just page 5
            page_data = scraper.scrape_single_page(5)
            
            if page_data['extraction_success']:
                transcript = page_data['transcript_info']
                logger.info(f"Page 5 extraction successful:")
                logger.info(f"  - Lines found: {len(transcript.get('lines', []))}")
                logger.info(f"  - Processing time: {page_data.get('processing_time_seconds', 0):.2f}s")
                
                # Show first few lines
                lines = transcript.get('lines', [])[:3]
                for line in lines:
                    text = line.get('text', '')[:50]
                    logger.info(f"  Line {line.get('line_number')}: {text}...")
                    
            else:
                logger.warning("Page 5 extraction failed")
                
    except Exception as e:
        logger.error(f"Single page extraction failed: {e}")


def example_4_validation():
    """Validate generated content for quality assurance."""
    print("\n=== Example 4: Content Validation ===")
    
    output_dir = Path("examples/output_samples")
    usfm_file = output_dir / "sample.usfm"
    
    if not usfm_file.exists():
        logger.warning("No USFM file found for validation")
        return
    
    try:
        # Create validation engine
        validator = create_validation_engine()
        
        # Validate the USFM file
        results = validator.validate_file(
            file_path=usfm_file,
            format_type='usfm',
            options={'strict_mode': False}
        )
        
        logger.info(f"Validation results for {usfm_file.name}:")
        
        for result in results:
            validator_name = result.metadata.get('validator', 'Unknown')
            logger.info(f"\n{validator_name}:")
            logger.info(f"  - Valid: {result.is_valid}")
            logger.info(f"  - Issues: {result.issue_count}")
            
            if result.issues:
                # Show first few issues
                for issue in result.issues[:3]:
                    level = issue.severity.value.upper()
                    logger.info(f"    [{level}] {issue.message}")
                    if issue.line_number:
                        logger.info(f"        Line: {issue.line_number}")
                
                if len(result.issues) > 3:
                    logger.info(f"    ... and {len(result.issues) - 3} more issues")
                    
    except Exception as e:
        logger.error(f"Validation failed: {e}")


def example_5_error_handling():
    """Demonstrate proper error handling patterns."""
    print("\n=== Example 5: Error Handling ===")
    
    # Test with invalid URL
    invalid_url = "https://invalid-portal.com/book/123"
    
    try:
        book = BookIdentifier(invalid_url)
        logger.info("URL parsing succeeded unexpectedly")
    except Exception as e:
        logger.info(f"✓ Caught expected error: {type(e).__name__}: {e}")
    
    # Test with valid URL but invalid book ID
    test_url = "https://opendigi.ub.uni-tuebingen.de/opendigi/NonExistentBook"
    
    try:
        book = BookIdentifier(test_url)
        
        with GundertPortalConnector(book, headless=True) as connector:
            if not connector.validate_book_access():
                logger.info("✓ Book access validation correctly failed")
            else:
                logger.warning("Book access validation passed unexpectedly")
                
    except Exception as e:
        logger.info(f"✓ Connection error handled: {type(e).__name__}: {e}")


def example_6_configuration_options():
    """Show different configuration options and their effects."""
    print("\n=== Example 6: Configuration Options ===")
    
    test_url = "https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1"
    
    try:
        book = BookIdentifier(test_url)
        
        # Test different connector configurations
        configs = [
            {"use_selenium": False, "headless": True, "description": "Requests only"},
            {"use_selenium": True, "headless": True, "description": "Headless Chrome"},
            {"use_selenium": True, "headless": False, "description": "Visible Chrome (if display available)"}
        ]
        
        for config in configs:
            description = config.pop('description')
            logger.info(f"\nTesting configuration: {description}")
            
            try:
                with GundertPortalConnector(book, **config) as connector:
                    accessible = connector.validate_book_access()
                    logger.info(f"  Book accessible: {accessible}")
                    
                    if accessible:
                        # Quick check - just get page count
                        page_count = connector.get_page_count()
                        logger.info(f"  Page count: {page_count}")
                        
            except Exception as e:
                logger.warning(f"  Configuration failed: {e}")
                
    except Exception as e:
        logger.error(f"Configuration testing failed: {e}")


def main():
    """Run all basic usage examples."""
    print("🚀 Starting Basic Usage Examples")
    print("=" * 50)
    
    # Example 1: Basic extraction
    book_data = example_1_basic_extraction()
    
    # Example 2: Format conversion (depends on example 1)
    example_2_format_conversion(book_data)
    
    # Example 3: Single page extraction
    example_3_single_page_extraction()
    
    # Example 4: Content validation
    example_4_validation()
    
    # Example 5: Error handling
    example_5_error_handling()
    
    # Example 6: Configuration options
    example_6_configuration_options()
    
    print("\n" + "=" * 50)
    print("✅ Basic usage examples completed!")
    print("\nNext steps:")
    print("1. Check output_samples/ directory for generated files")
    print("2. Try batch_processing.py for multiple book extraction")
    print("3. Explore custom_transformation.py for advanced features")


if __name__ == "__main__":
    main()