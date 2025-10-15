"""Command-line interface for Gundert Portal Scraper."""

import click
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import sys
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.logging import RichHandler

from ..core.book_identifier import BookIdentifier
from ..core.connection import GundertPortalConnector
from ..extraction.metadata import MetadataExtractor
from ..extraction.content import ContentScraper
from ..storage.manager import BookStorageManager
from ..transformations import create_transformation_engine
from ..validation import create_validation_engine
from ..core.exceptions import GundertPortalError

# Initialize console for rich output
console = Console()

# Configure logging with Rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console)]
)

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, quiet: bool = False):
    """Setup logging based on verbosity flags."""
    if quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)


def print_banner():
    """Print application banner."""
    banner = """
[bold blue]╔══════════════════════════════════════════════════════════════╗[/bold blue]
[bold blue]║              GUNDERT PORTAL SCRAPER                          ║[/bold blue]
[bold blue]║         Universal Malayalam Content Extractor                ║[/bold blue]
[bold blue]║                    Version 1.0.0                             ║[/bold blue]
[bold blue]╚══════════════════════════════════════════════════════════════╝[/bold blue]
"""
    console.print(banner)


def print_error(message: str, exception: Optional[Exception] = None):
    """Print error message with rich formatting."""
    console.print(f"[bold red]❌ Error:[/bold red] {message}")
    if exception and logging.getLogger().level == logging.DEBUG:
        console.print(f"[dim red]Details: {exception}[/dim red]")


def print_success(message: str):
    """Print success message with rich formatting."""
    console.print(f"[bold green]✅ {message}[/bold green]")


def print_warning(message: str):
    """Print warning message with rich formatting."""
    console.print(f"[bold yellow]⚠️  {message}[/bold yellow]")


def print_info(message: str):
    """Print info message with rich formatting."""
    console.print(f"[bold blue]ℹ️  {message}[/bold blue]")


def validate_url(ctx, param, value):
    """Validate URL parameter."""
    if value and not (value.startswith('http://') or value.startswith('https://')):
        raise click.BadParameter('URL must start with http:// or https://')
    return value


def validate_output_dir(ctx, param, value):
    """Validate and create output directory."""
    if value:
        output_path = Path(value)
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            return output_path
        except Exception as e:
            raise click.BadParameter(f'Cannot create output directory: {e}')
    return None


def validate_formats(ctx, param, value):
    """Validate transformation formats."""
    if value:
        valid_formats = ['usfm', 'tei_xml', 'parabible_json', 'bibleml', 'docx', 'markdown', 'plain_text']
        formats = [f.strip().lower() for f in value.split(',')]
        
        invalid_formats = [f for f in formats if f not in valid_formats]
        if invalid_formats:
            raise click.BadParameter(f'Invalid formats: {", ".join(invalid_formats)}. Valid formats: {", ".join(valid_formats)}')
        
        return formats
    return None


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Suppress all output except errors')
@click.option('--no-banner', is_flag=True, help='Suppress banner display')
@click.pass_context
def cli(ctx, verbose, quiet, no_banner):
    """
    Gundert Portal Scraper - Universal Malayalam Content Extractor
    
    Extract, transform, and validate Malayalam biblical content from Gundert Portal and OpenDigi.
    """
    # Store options in context
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    
    # Setup logging
    setup_logging(verbose, quiet)
    
    # Print banner unless suppressed or quiet
    if not no_banner and not quiet:
        print_banner()


@cli.command()
@click.argument('url')
@click.option('--output', '-o', type=click.Path(), callback=validate_output_dir,
              help='Output directory for extracted content')
@click.option('--start-page', '-s', type=int, default=1, help='Starting page number')
@click.option('--end-page', '-e', type=int, help='Ending page number (default: extract all)')
@click.option('--batch-size', '-b', type=int, default=10, help='Batch size for processing')
@click.option('--formats', '-f', callback=validate_formats,
              help='Comma-separated list of output formats (usfm,tei_xml,parabible_json,bibleml,docx,markdown,plain_text)')
@click.option('--validate/--no-validate', default=True, help='Enable/disable content validation')
@click.option('--preserve-images', is_flag=True, help='Download and preserve page images')
@click.option('--book-id', help='Override book ID (auto-detected if not provided)')
@click.pass_context
def extract(ctx, url, output, start_page, end_page, batch_size, formats, validate, preserve_images, book_id):
    """
    Extract content from a Gundert Portal or OpenDigi book URL.
    
    URL: Book URL from gundert.org or opendigi.org
    
    Example:
        gundert-scraper extract https://gundert.org/p/73 --formats usfm,docx --output ./output
    """
    try:
        # Initialize progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            # Step 1: Identify book
            task1 = progress.add_task("🔍 Identifying book...", total=100)
            
            book_info = BookIdentifier(url)
            
            progress.update(task1, completed=100)
            
            if not ctx.obj.get('quiet'):
                console.print(f"\n[bold green]📚 Book Identified:[/bold green]")
                console.print(f"   Portal: [cyan]{book_info.portal_type}[/cyan]")
                console.print(f"   Book ID: [cyan]{book_info.book_id}[/cyan]")
                console.print(f"   URL: [cyan]{book_info.base_url}[/cyan]")
            
            # Override book ID if provided
            if book_id:
                # Create a new identifier with the overridden book ID
                book_info = BookIdentifier(book_id)
                print_info(f"Book ID overridden to: {book_id}")
            
            # Step 2: Extract metadata
            task2 = progress.add_task("📋 Extracting metadata...", total=100)
            
            connector = GundertPortalConnector()
            metadata_extractor = MetadataExtractor(connector)
            
            metadata = metadata_extractor.extract_metadata(book_info)
            
            progress.update(task2, completed=100)
            
            if not ctx.obj.get('quiet'):
                console.print(f"\n[bold green]📋 Metadata Extracted:[/bold green]")
                if hasattr(metadata, 'title') and metadata.title:
                    console.print(f"   Title: [cyan]{metadata.title}[/cyan]")
                console.print(f"   Content Type: [cyan]{metadata.content_type}[/cyan]")
                if hasattr(metadata, 'total_pages'):
                    console.print(f"   Total Pages: [cyan]{metadata.total_pages}[/cyan]")
            
            # Step 3: Extract content
            content_task = progress.add_task("📖 Extracting content...", total=100)
            
            scraper = ContentScraper(connector)
            
            # Determine page range
            if not end_page and hasattr(metadata, 'total_pages') and metadata.total_pages:
                end_page = metadata.total_pages
            
            extraction_params = {
                'start_page': start_page,
                'end_page': end_page,
                'batch_size': batch_size,
                'preserve_formatting': True,
                'transcript_extraction': True,
                'portal_type': book_info.portal_type
            }
            
            if preserve_images:
                extraction_params['image_extraction'] = True
            
            # Progress callback for content extraction
            def update_progress(current_page, total_pages):
                if total_pages > 0:
                    percentage = (current_page / total_pages) * 100
                    progress.update(content_task, completed=percentage)
            
            book_storage = scraper.extract_book_content(
                book_info, 
                metadata,
                extraction_params,
                progress_callback=update_progress
            )
            
            progress.update(content_task, completed=100)
            
            # Display extraction results
            if not ctx.obj.get('quiet'):
                console.print(f"\n[bold green]📖 Content Extracted:[/bold green]")
                console.print(f"   Pages processed: [cyan]{book_storage.statistics.pages_processed}[/cyan]")
                console.print(f"   Success rate: [cyan]{book_storage.statistics.success_rate:.1f}%[/cyan]")
                console.print(f"   Total lines: [cyan]{book_storage.statistics.total_lines_extracted}[/cyan]")
            
            # Step 4: Save content
            if output:
                save_task = progress.add_task("💾 Saving content...", total=100)
                
                storage_manager = BookStorageManager(output)
                storage_path = storage_manager.save_book(book_storage)
                
                progress.update(save_task, completed=50)
                
                print_success(f"Content saved to: {storage_path}")
                
                # Step 5: Transform to requested formats
                if formats:
                    transform_task = progress.add_task("🔄 Transforming content...", total=len(formats))
                    
                    transformation_engine = create_transformation_engine()
                    
                    for i, format_name in enumerate(formats):
                        try:
                            output_file = output / f"{book_storage.book_metadata.book_id}.{_get_format_extension(format_name)}"
                            
                            result = transformation_engine.transform(book_storage, format_name, output_file)
                            
                            if result.success:
                                print_success(f"{format_name.upper()} generated: {output_file}")
                                
                                # Validate if requested
                                if validate:
                                    validation_engine = create_validation_engine()
                                    validation_results = validation_engine.validate_file(output_file, format_name)
                                    
                                    for validation_result in validation_results:
                                        if validation_result.is_valid:
                                            print_success(f"{format_name.upper()} validation: PASSED")
                                        else:
                                            print_warning(f"{format_name.upper()} validation: {validation_result.error_count} errors, {validation_result.warning_count} warnings")
                            else:
                                print_error(f"Failed to generate {format_name.upper()}: {result.errors}")
                        
                        except Exception as e:
                            print_error(f"Error generating {format_name.upper()}", e)
                        
                        progress.update(transform_task, advance=1)
                
                progress.update(save_task, completed=100)
            
            else:
                # Just show extraction summary
                _display_extraction_summary(book_storage)
                
    except GundertPortalError as e:
        print_error(f"Scraping failed: {e}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if ctx.obj.get('verbose'):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


def _get_format_extension(format_name: str) -> str:
    """Get file extension for format."""
    extensions = {
        'usfm': 'usfm',
        'tei_xml': 'xml',
        'parabible_json': 'json',
        'bibleml': 'xml',
        'docx': 'docx',
        'markdown': 'md',
        'plain_text': 'txt'
    }
    return extensions.get(format_name, format_name)


def _display_extraction_summary(book_storage):
    """Display extraction summary in a table."""
    table = Table(title="📊 Extraction Summary")
    
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    
    table.add_row("Book ID", book_storage.book_metadata.book_id)
    table.add_row("Pages Processed", str(book_storage.statistics.pages_processed))
    table.add_row("Success Rate", f"{book_storage.statistics.success_rate:.1f}%")
    table.add_row("Total Lines", str(book_storage.statistics.total_lines_extracted))
    table.add_row("Processing Time", f"{book_storage.statistics.extraction_duration_seconds:.1f}s")
    
    console.print(table)


# Import additional commands
try:
    from . import commands  # This registers additional commands with the cli group
except ImportError as e:
    logger.warning(f"Could not import additional commands: {e}")


if __name__ == '__main__':
    cli()