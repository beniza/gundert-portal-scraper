"""Main CLI commands for Gundert Portal Scraper."""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
import json

from ..core.book_identifier import BookIdentifier
from ..core.connector import GundertPortalConnector
from ..extraction.two_phase_scraper import TwoPhaseContentScraper

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    Gundert Portal Scraper - Extract and transform manuscript content.
    
    Extract content from OpenDigi manuscript collections and transform
    into various academic and publishing formats.
    """
    pass


@cli.command()
@click.argument('url')
@click.option('--output', '-o', default='./output', help='Output directory')
@click.option('--formats', '-f', default='json', help='Output formats (comma-separated): json,usfm,tei,docx')
@click.option('--start-page', type=int, default=1, help='Starting page number')
@click.option('--end-page', type=int, default=None, help='Ending page number (default: all)')
@click.option('--headless/--no-headless', default=True, help='Run browser in headless mode')
@click.option('--validate/--no-validate', default=False, help='Validate output after extraction')
def extract(url, output, formats, start_page, end_page, headless, validate):
    """
    Extract content from OpenDigi manuscript URL.
    
    Example:
        gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a --formats json,usfm --output ./output/psalms
    """
    console.print(f"\n[bold blue]🔍 Gundert Portal Scraper[/bold blue]")
    console.print(f"[dim]Extracting from: {url}[/dim]\n")
    
    try:
        book_id = BookIdentifier(url)
        console.print(f"📚 Book ID: [cyan]{book_id.book_id}[/cyan]")
        
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        with console.status("[bold green]Connecting to portal..."):
            connector = GundertPortalConnector(book_id, headless=headless)
            connector.connect()
        
        console.print("✅ Connected successfully\n")
        
        # Use two-phase scraper for efficient extraction
        scraper = TwoPhaseContentScraper(connector)
        
        with console.status("[bold green]Extracting content..."):
            book_data = scraper.scrape_full_book(start_page=start_page, end_page=end_page)
        
        connector.close()
        
        _display_statistics(book_data)
        
        format_list = [f.strip().lower() for f in formats.split(',')]
        
        for fmt in format_list:
            if fmt == 'json':
                json_path = output_path / f"{book_id.book_id}.json"
                book_data.to_json(str(json_path))
                console.print(f"💾 Saved JSON: [cyan]{json_path}[/cyan]")
            elif fmt == 'usfm':
                console.print(f"⚠️  USFM transformation not yet implemented")
            elif fmt == 'tei':
                console.print(f"⚠️  TEI transformation not yet implemented")
            elif fmt == 'docx':
                console.print(f"⚠️  DOCX transformation not yet implemented")
            else:
                console.print(f"❌ Unknown format: {fmt}")
        
        console.print(f"\n[bold green]✅ Extraction complete![/bold green]")
        
        if validate and 'usfm' in format_list:
            console.print("\n[bold yellow]Validation will be implemented next[/bold yellow]")
    
    except ValueError as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[bold red]❌ Unexpected error:[/bold red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()


def _display_statistics(book_data):
    """Display extraction statistics in a table."""
    stats = book_data.statistics
    
    table = Table(title="📊 Extraction Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Pages", str(len(book_data.pages)))
    table.add_row("Pages with Content", str(stats['pages_with_content']))
    table.add_row("Total Lines", str(stats['total_lines_extracted']))
    table.add_row("Total Characters", str(stats['total_characters']))
    table.add_row("Success Rate", f"{stats['success_rate']:.1f}%")
    
    if stats.get('extraction_errors', 0) > 0:
        table.add_row("Extraction Errors", str(stats['extraction_errors']), style="yellow")
    
    console.print(table)
    console.print()


if __name__ == '__main__':
    cli()
