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
from ..storage.schemas import BookStorage
from ..core.two_phase_scraper import create_two_phase_scraper
from ..core.cache import RawContentCache
from ..core.exceptions import GundertPortalError
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
@click.option('--batch-size', '-b', type=int, default=10, help='Batch size for processing (legacy mode only)')
@click.option('--formats', '-f', callback=validate_formats,
              help='Comma-separated list of output formats (usfm,tei_xml,parabible_json,bibleml,docx,markdown,plain_text)')
@click.option('--validate/--no-validate', default=True, help='Enable/disable content validation')
@click.option('--preserve-images', is_flag=True, help='Download and preserve page images')
@click.option('--book-id', help='Override book ID (auto-detected if not provided)')
@click.option('--cache-dir', type=click.Path(), help='Cache directory (default: ./cache)')
@click.option('--force-redownload', is_flag=True, help='Force redownload even if cached')
@click.option('--skip-download', is_flag=True, help='Skip download, process existing cache only')
@click.option('--no-cache', is_flag=True, help='Use legacy single-phase mode (no caching)')
@click.option('--max-workers', type=int, default=4, help='Maximum processing workers')
@click.pass_context
def extract(ctx, url, output, start_page, end_page, batch_size, formats, validate, preserve_images, book_id,
           cache_dir, force_redownload, skip_download, no_cache, max_workers):
    """
    Extract content from a Gundert Portal or OpenDigi book URL with two-phase approach.
    
    URL: Book URL from gundert.org or opendigi.org
    
    The extraction process has two phases:
    1. Download: Raw HTML content is cached locally
    2. Process: Cached content is processed into structured format
    
    Examples:
        # Two-phase extraction (default)
        gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a --formats usfm --output ./output
        
        # Force redownload
        gundert-scraper extract https://... --force-redownload
        
        # Process existing cache only
        gundert-scraper extract --skip-download --cache-dir ./cache --formats usfm
        
        # Legacy single-phase mode
        gundert-scraper extract https://... --no-cache --formats usfm
    """
    try:
        # Step 1: Identify book
        book_info = BookIdentifier(url) if url else None
        
        # Override book ID if provided
        if book_id and book_info:
            book_info = BookIdentifier(book_id)
        
        if not ctx.obj.get('quiet'):
            if book_info:
                console.print(f"\n[bold green]📚 Book Identified:[/bold green]")
                console.print(f"   Portal: [cyan]{book_info.portal_type}[/cyan]")
                console.print(f"   Book ID: [cyan]{book_info.book_id}[/cyan]")
                console.print(f"   URL: [cyan]{book_info.base_url}[/cyan]")
        
        # Handle different extraction modes
        if no_cache:
            # Legacy single-phase mode
            print_info("Using legacy single-phase extraction (no caching)")
            _legacy_extract(ctx, url, output, start_page, end_page, batch_size, formats, 
                          validate, preserve_images, book_info)
        else:
            # Two-phase extraction (default)
            _two_phase_extract(ctx, book_info, output, start_page, end_page, formats,
                             validate, preserve_images, cache_dir, force_redownload, 
                             skip_download, max_workers)
                
    except GundertPortalError as e:
        print_error(f"Portal error: {e}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if ctx.obj.get('verbose'):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


def _two_phase_extract(ctx, book_info, output, start_page, end_page, formats,
                      validate, preserve_images, cache_dir, force_redownload, 
                      skip_download, max_workers):
    """Two-phase extraction implementation."""
    
    # Initialize two-phase scraper
    scraper = create_two_phase_scraper(
        cache_dir=Path(cache_dir) if cache_dir else None,
        max_processing_workers=max_workers,
        preserve_formatting=True
    )
    
    # Check cache status if not skipping download
    if not skip_download and book_info:
        cache_status = scraper.check_cache_status(book_info.book_id)
        
        if cache_status['is_cached'] and cache_status['cache_valid'] and not force_redownload:
            print_info(f"✓ Book {book_info.book_id} is already cached and valid")
            if not ctx.obj.get('quiet'):
                cache_info = cache_status['cache_info']
                console.print(f"   Cache date: [cyan]{cache_info.get('download_date', 'Unknown')}[/cyan]")
                console.print(f"   Cached pages: [cyan]{len(cache_info.get('pages_cached', []))}[/cyan]")
                console.print(f"   Cache size: [cyan]{cache_info.get('cache_size_mb', 0)} MB[/cyan]")
        
        elif force_redownload and cache_status['is_cached']:
            print_warning(f"⚠ Cache exists for {book_info.book_id} but will be redownloaded")
    
    # Initialize dual progress tracking
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        # Phase 1: Download progress
        download_task = progress.add_task("📥 Downloading content...", total=100)
        download_progress_tracker = {'current': 0, 'total': 0}
        
        def download_callback(download_progress):
            info = download_progress.get_progress_info()
            download_progress_tracker['current'] = info['completed_pages']
            download_progress_tracker['total'] = info['total_pages']
            progress.update(download_task, 
                          completed=info['percentage'],
                          description=f"📥 Downloading content... ({info['current_page']}/{info['total_pages']})")
        
        # Phase 2: Processing progress  
        process_task = progress.add_task("🔄 Processing content...", total=100)
        
        def processing_callback(processing_progress):
            info = processing_progress.get_progress_info()
            progress.update(process_task,
                          completed=info['percentage'], 
                          description=f"🔄 Processing content... ({info['current_page']}/{info['total_pages']})")
        
        # Set progress callbacks
        scraper.set_progress_callbacks(
            download_callback=download_callback,
            processing_callback=processing_callback
        )
        
        # Execute two-phase extraction
        book_data = scraper.extract_book(
            book_identifier=book_info,
            start_page=start_page,
            end_page=end_page,
            force_redownload=force_redownload,
            skip_download=skip_download
        )
        
        # Complete progress bars
        progress.update(download_task, completed=100)
        progress.update(process_task, completed=100)
        
        # Display results
        if not ctx.obj.get('quiet'):
            console.print(f"\n[bold green]📖 Extraction Complete:[/bold green]")
            stats = book_data.get('statistics', {})
            console.print(f"   Pages processed: [cyan]{stats.get('pages_processed', 0)}[/cyan]")
            console.print(f"   Success rate: [cyan]{stats.get('success_rate', 0):.1f}%[/cyan]")
            console.print(f"   Total lines: [cyan]{stats.get('total_lines_extracted', 0)}[/cyan]")
            console.print(f"   Processing time: [cyan]{stats.get('processing_duration_seconds', 0):.1f}s[/cyan]")
            
            if stats.get('used_cache'):
                console.print(f"   [dim]Used existing cache[/dim]")
        
        # Save results
        if output:
            save_task = progress.add_task("💾 Saving results...", total=100)
            
            output_dir = Path(output)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            book_id_str = book_info.book_id if book_info else "unknown"
            json_file = output_dir / f"{book_id_str}.json"
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(book_data, f, indent=2, ensure_ascii=False, default=str)
            
            progress.update(save_task, completed=100)
            print_success(f"Content saved to: {json_file}")
            
            # Format transformations (disabled for now)
            if formats:
                print_warning("⚠ Format transformations are currently disabled due to format compatibility issues.")
                print_info("📄 Raw JSON data has been saved and can be transformed later using the 'transform' command.")
        else:
            _display_extraction_summary(book_data)


def _legacy_extract(ctx, url, output, start_page, end_page, batch_size, formats,
                   validate, preserve_images, book_info):
    """Legacy single-phase extraction for backward compatibility."""
    
    # This would implement the original single-phase approach
    print_error("Legacy single-phase extraction not yet implemented in two-phase architecture.")
    print_info("Please use the default two-phase approach (remove --no-cache flag).")
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


def _display_extraction_summary(book_data):
    """Display extraction summary in a table."""
    table = Table(title="📊 Extraction Summary")
    
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    
    metadata = book_data.get('book_metadata', {})
    stats = book_data.get('statistics', {})
    
    table.add_row("Book ID", metadata.get('book_id', 'Unknown'))
    table.add_row("Pages Processed", str(stats.get('pages_processed', 0)))
    table.add_row("Success Rate", f"{stats.get('success_rate', 0):.1f}%")
    table.add_row("Total Lines", str(stats.get('total_lines_extracted', 0)))
    table.add_row("Processing Time", f"{stats.get('extraction_duration_seconds', 0):.1f}s")
    
    console.print(table)


# Import additional commands
try:
    from . import commands  # This registers additional commands with the cli group
except ImportError as e:
    logger.warning(f"Could not import additional commands: {e}")


if __name__ == '__main__':
    cli()