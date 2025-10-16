"""Main CLI commands for Gundert Portal Scraper."""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
import json

from ..core.book_identifier import BookIdentifier
from ..core.connector import GundertPortalConnector
from ..extraction.two_phase_scraper import TwoPhaseContentScraper
from ..transformations.usfm_transformer import USFMTransformer
from ..storage.output_manager import OutputManager, OutputType

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
@click.option('--keep-interim/--clean-interim', default=False, help='Keep interim JSON files after transformation')
def extract(url, output, formats, start_page, end_page, headless, validate, keep_interim):
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
        
        # Initialize output manager
        output_manager = OutputManager(base_output_dir=output, keep_interim=keep_interim)
        
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
        
        # Save JSON (always as interim, unless it's the only format)
        json_is_final = len(format_list) == 1 and 'json' in format_list
        
        if 'json' in format_list or len(format_list) > 1:
            json_path = output_manager.get_interim_path('json', f"{book_id.book_id}.json") if not json_is_final else output_manager.get_final_path('json', f"{book_id.book_id}.json")
            book_data.to_json(str(json_path))
            
            output_type = OutputType.FINAL if json_is_final else OutputType.INTERIM
            output_manager.register_file(
                str(json_path),
                output_type=output_type,
                format_name='json',
                metadata={
                    'book_id': book_id.book_id,
                    'pages': len(book_data.pages),
                    'extraction_date': book_data.metadata.extraction_date
                }
            )
            
            console.print(f"💾 Saved JSON ({output_type}): [cyan]{json_path.relative_to(output_path)}[/cyan]")
        
        # Transform to other formats
        for fmt in format_list:
            if fmt == 'json':
                continue  # Already handled
            elif fmt == 'usfm':
                usfm_path = output_manager.get_final_path('usfm', f"{book_id.book_id}.usfm")
                transformer = USFMTransformer()
                
                # Get the interim JSON path
                interim_json = output_manager.get_interim_path('json', f"{book_id.book_id}.json")
                if not interim_json.exists():
                    # Save temporarily if not already saved
                    book_data.to_json(str(interim_json))
                
                usfm_content = transformer.transform(str(interim_json), str(usfm_path))
                
                output_manager.register_file(
                    str(usfm_path),
                    output_type=OutputType.FINAL,
                    format_name='usfm',
                    metadata={
                        'book_id': book_id.book_id,
                        'chapters': usfm_content.count('\\c '),
                        'verses': usfm_content.count('\\v ')
                    }
                )
                
                console.print(f"📝 Saved USFM: [cyan]{usfm_path.relative_to(output_path)}[/cyan]")
            elif fmt == 'tei':
                console.print(f"⚠️  TEI transformation not yet implemented")
            elif fmt == 'docx':
                console.print(f"⚠️  DOCX transformation not yet implemented")
            else:
                console.print(f"❌ Unknown format: {fmt}")
        
        # Cleanup interim files if requested
        if not keep_interim and len(format_list) > 1 and 'json' not in format_list:
            cleanup_result = output_manager.cleanup_interim()
            if cleanup_result["cleaned"]:
                console.print(f"\n🧹 Cleaned {cleanup_result['files_deleted']} interim files ({cleanup_result['space_freed_mb']} MB freed)")
        
        # Show output summary
        console.print(f"\n[bold green]✅ Extraction complete![/bold green]")
        _display_output_summary(output_manager)
        
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


def _display_output_summary(output_manager: OutputManager):
    """Display output file summary."""
    stats = output_manager.get_statistics()
    
    table = Table(title="📁 Output Summary")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Size", style="yellow")
    
    table.add_row("Final Outputs", str(stats['total_final']), f"{stats['final_size_mb']} MB")
    table.add_row("Interim Files", str(stats['total_interim']), f"{stats['interim_size_mb']} MB")
    
    console.print(table)
    console.print()


@cli.command()
@click.argument('json_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file path')
@click.option('--format', '-f', type=click.Choice(['usfm', 'tei', 'docx']), default='usfm', help='Output format')
@click.option('--keep-interim/--clean-interim', default=False, help='Keep interim JSON files')
def transform(json_file, output, format, keep_interim):
    """
    Transform extracted JSON to specified format.
    
    Example:
        gundert-scraper transform output/GaXXXIV5a.json --format usfm --output output/psalms.usfm
    """
    console.print(f"\n[bold blue]🔄 Transforming Content[/bold blue]")
    console.print(f"[dim]Input: {json_file}[/dim]")
    console.print(f"[dim]Format: {format}[/dim]\n")
    
    try:
        json_path = Path(json_file)
        
        # Initialize output manager
        output_manager = OutputManager(keep_interim=keep_interim)
        
        # Determine output path
        if not output:
            output = output_manager.get_final_path(format, json_path.stem + f'.{format}')
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'usfm':
            with console.status("[bold green]Transforming to USFM..."):
                transformer = USFMTransformer()
                usfm_content = transformer.transform(str(json_path), str(output_path))
            
            # Register as final output
            output_manager.register_file(
                str(output_path),
                output_type=OutputType.FINAL,
                format_name='usfm',
                metadata={
                    'source': str(json_path),
                    'chapters': usfm_content.count('\\c '),
                    'verses': usfm_content.count('\\v ')
                }
            )
            
            console.print(f"✅ USFM file generated: [cyan]{output_path}[/cyan]")
            console.print(f"   Total characters: {len(usfm_content):,}")
            
            # Count chapters and verses
            chapters = usfm_content.count('\\c ')
            verses = usfm_content.count('\\v ')
            console.print(f"   Chapters: {chapters}")
            console.print(f"   Verses: {verses}")
        
        elif format == 'tei':
            console.print("⚠️  TEI transformation not yet implemented")
        
        elif format == 'docx':
            console.print("⚠️  DOCX transformation not yet implemented")
        
        console.print(f"\n[bold green]✅ Transformation complete![/bold green]")
    
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()


@cli.command()
@click.option('--output-dir', '-o', default='./output', help='Output directory to manage')
@click.option('--force', is_flag=True, help='Force cleanup even if keep-interim is set')
def cleanup(output_dir, force):
    """
    Clean up interim output files, keeping only final deliverables.
    
    This removes intermediate JSON files and temporary processing files,
    but preserves final outputs (USFM, TEI, DOCX) and cache.
    
    Example:
        gundert-scraper cleanup
        gundert-scraper cleanup --force
    """
    console.print(f"\n[bold blue]🧹 Output Cleanup[/bold blue]")
    console.print(f"[dim]Managing: {output_dir}[/dim]\n")
    
    try:
        output_manager = OutputManager(base_output_dir=output_dir)
        
        # Show current state
        stats_before = output_manager.get_statistics()
        console.print(f"📊 Current state:")
        console.print(f"   Final outputs: {stats_before['total_final']} files ({stats_before['final_size_mb']} MB)")
        console.print(f"   Interim files: {stats_before['total_interim']} files ({stats_before['interim_size_mb']} MB)\n")
        
        if stats_before['total_interim'] == 0:
            console.print("[green]✅ No interim files to clean[/green]")
            return
        
        # Confirm cleanup
        if not force:
            if not click.confirm("Clean up interim files?"):
                console.print("❌ Cleanup cancelled")
                return
        
        # Perform cleanup
        with console.status("[bold yellow]Cleaning interim files..."):
            result = output_manager.cleanup_interim(force=force)
        
        if result["cleaned"]:
            console.print(f"\n[bold green]✅ Cleanup complete![/bold green]")
            console.print(f"   Files deleted: {result['files_deleted']}")
            console.print(f"   Space freed: {result['space_freed_mb']} MB")
            
            # Show deleted files
            if result['deleted_files']:
                console.print(f"\n[dim]Deleted files:[/dim]")
                for file in result['deleted_files'][:10]:  # Show first 10
                    console.print(f"   [dim]{file}[/dim]")
                if len(result['deleted_files']) > 10:
                    console.print(f"   [dim]... and {len(result['deleted_files']) - 10} more[/dim]")
        else:
            console.print(f"\n[yellow]ℹ️  {result['reason']}[/yellow]")
    
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise click.Abort()


if __name__ == '__main__':
    cli()
